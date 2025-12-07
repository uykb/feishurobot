import time
import schedule
import asyncio
import aiohttp
import gc
import logging
from datetime import datetime
from config import SYMBOLS, TIMEFRAME, DYNAMIC_SYMBOLS, PROXY_URL
from data_fetcher import get_binance_data, get_top_liquid_symbols
from indicators import VolumeSignal, OpenInterestSignal, LSRatioSignal

# Try to import ProxyConnector for SOCKS5 support
try:
    from aiohttp_socks import ProxyConnector
except ImportError:
    ProxyConnector = None
from ai_interpreter import get_ai_interpretation
from alerter import send_alert
from state_manager import SignalStateManager

# 初始化状态管理器
state_manager = SignalStateManager()

# Concurrency limit (e.g. 5 concurrent requests)
CONCURRENCY_LIMIT = 5

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def process_symbol(symbol: str, session: aiohttp.ClientSession, indicator_checkers: list):
    """
    处理单个 symbol 的逻辑
    """
    try:
        logger.info(f"Checking {symbol}...")
        df = await get_binance_data(symbol, session)
        
        if df.empty:
            logger.warning(f"Failed to fetch data for {symbol}, skipping.")
            return
            
        for checker in indicator_checkers:
            # check is CPU bound, fast enough to run in main thread usually, 
            # but if very heavy, could use run_in_executor
            try:
                signal = checker.check(df)
                if signal:
                    logger.info(f"Potential signal for {symbol}: {signal['primary_signal']}")
                    # 检查是否应该发送警报
                    should_send, prev_signal = state_manager.should_send_alert(symbol, signal)
                    if should_send:
                        # 获取 AI 解读 (Blocking I/O, run in executor)
                        loop = asyncio.get_running_loop()
                        ai_insight = await loop.run_in_executor(
                            None, 
                            get_ai_interpretation, 
                            symbol, TIMEFRAME, signal, prev_signal
                        )
                        
                        # 发送通知 (Blocking I/O, run in executor)
                        await loop.run_in_executor(
                            None,
                            send_alert,
                            symbol, signal, ai_insight
                        )
            except Exception as e:
                logger.error(f"Error processing signal for {symbol}: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Error in process_symbol for {symbol}: {e}", exc_info=True)

async def run_check_async():
    connector = None
    if PROXY_URL:
        if ProxyConnector:
            try:
                connector = ProxyConnector.from_url(PROXY_URL)
                logger.info(f"Using proxy: {PROXY_URL}")
            except Exception as e:
                logger.error(f"Failed to create proxy connector: {e}")
        elif PROXY_URL.startswith('socks'):
            logger.warning("SOCKS5 proxy configured but aiohttp-socks not installed. Proxy may not work.")

    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            # 根据配置决定使用哪个币种列表
            if DYNAMIC_SYMBOLS:
                symbols_to_check = await get_top_liquid_symbols(session)
                # 如果动态获取失败，则使用静态列表作为备用
                if not symbols_to_check:
                    logger.warning("动态获取币种列表失败，将使用 config.py 中的静态列表作为备用。")
                    symbols_to_check = SYMBOLS
            else:
                symbols_to_check = SYMBOLS

            logger.info(f"开始执行检查，目标币种: {', '.join(symbols_to_check)}...")
            
            # 初始化所有指标检查器
            indicator_checkers = [VolumeSignal(), OpenInterestSignal(), LSRatioSignal()]
            
            # Use semaphore to limit concurrency
            semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
            
            async def sem_task(sym):
                async with semaphore:
                    await process_symbol(sym, session, indicator_checkers)

            tasks = [sem_task(symbol) for symbol in symbols_to_check]
            await asyncio.gather(*tasks)
            
            logger.info("检查完成。")
            
    except Exception as e:
        logger.error(f"Error in run_check_async: {e}", exc_info=True)
    finally:
        # Force garbage collection to free memory
        gc.collect()

def run_check():
    """Wrapper to run async check from sync schedule"""
    try:
        asyncio.run(run_check_async())
    except Exception as e:
        logger.error(f"Critical error in run_check: {e}", exc_info=True)

if __name__ == "__main__":
    logger.info("启动加密货币指标监控器...")
    # 首次启动立即执行一次
    run_check()
    
    # 设置定时任务, 例如每15分钟运行一次
    schedule.every(15).minutes.do(run_check)
    logger.info("定时任务已设置，程序将每 15 分钟运行一次检查。")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in schedule loop: {e}", exc_info=True)
            time.sleep(5) # Wait before retrying
