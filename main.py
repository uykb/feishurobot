import time
import schedule
import asyncio
import aiohttp
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

async def process_symbol(symbol: str, session: aiohttp.ClientSession, indicator_checkers: list):
    """
    处理单个 symbol 的逻辑
    """
    print(f"--- 正在检查 {symbol} ---")
    df = await get_binance_data(symbol, session)
    
    if df.empty:
        print(f"未能获取 {symbol} 的数据，跳过。")
        return
        
    for checker in indicator_checkers:
        # check is CPU bound, fast enough to run in main thread usually, 
        # but if very heavy, could use run_in_executor
        signal = checker.check(df)
        if signal:
            print(f"为 {symbol} 找到潜在信号: {signal['primary_signal']}")
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

async def run_check_async():
    connector = None
    if PROXY_URL:
        if ProxyConnector:
            try:
                connector = ProxyConnector.from_url(PROXY_URL)
                print(f"Using proxy: {PROXY_URL}")
            except Exception as e:
                print(f"Failed to create proxy connector: {e}")
        elif PROXY_URL.startswith('socks'):
            print("Warning: SOCKS5 proxy configured but aiohttp-socks not installed. Proxy may not work.")

    async with aiohttp.ClientSession(connector=connector) as session:
        # 根据配置决定使用哪个币种列表
        if DYNAMIC_SYMBOLS:
            symbols_to_check = await get_top_liquid_symbols(session)
            # 如果动态获取失败，则使用静态列表作为备用
            if not symbols_to_check:
                print("动态获取币种列表失败，将使用 config.py 中的静态列表作为备用。")
                symbols_to_check = SYMBOLS
        else:
            symbols_to_check = SYMBOLS

        print(f"\n[{datetime.now()}] 开始执行检查，目标币种: {', '.join(symbols_to_check)}...")
        
        # 初始化所有指标检查器 (reused for all symbols as they are stateless or reset per check?)
        # Looking at indicators.py, VolumeSignal, OpenInterestSignal, LSRatioSignal seem stateless or don't store symbol-specific state in `self`.
        # They only use constants from config. So we can reuse instances.
        indicator_checkers = [VolumeSignal(), OpenInterestSignal(), LSRatioSignal()]
        
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        
        async def sem_task(sym):
            async with semaphore:
                await process_symbol(sym, session, indicator_checkers)

        tasks = [sem_task(symbol) for symbol in symbols_to_check]
        await asyncio.gather(*tasks)
        
        print("检查完成。")

def run_check():
    """Wrapper to run async check from sync schedule"""
    asyncio.run(run_check_async())

if __name__ == "__main__":
    print("启动加密货币指标监控器...")
    # 首次启动立即执行一次
    run_check()
    
    # 设置定时任务, 例如每15分钟运行一次
    schedule.every(15).minutes.do(run_check)
    print("定时任务已设置，程序将每 15 分钟运行一次检查。")
    
    while True:
        schedule.run_pending()
        time.sleep(1)
