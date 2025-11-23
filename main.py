import time
import schedule
from datetime import datetime
from config import SYMBOLS, TIMEFRAME, DYNAMIC_SYMBOLS
from data_fetcher import get_binance_data, get_top_liquid_symbols
from indicators import VolumeSignal, OpenInterestSignal, LSRatioSignal
from ai_interpreter import get_gemini_interpretation
from alerter import send_alert
from state_manager import SignalStateManager

# 初始化状态管理器
state_manager = SignalStateManager()

def run_check():
    # 根据配置决定使用哪个币种列表
    if DYNAMIC_SYMBOLS:
        symbols_to_check = get_top_liquid_symbols()
        # 如果动态获取失败，则使用静态列表作为备用
        if not symbols_to_check:
            print("动态获取币种列表失败，将使用 config.py 中的静态列表作为备用。")
            symbols_to_check = SYMBOLS
    else:
        symbols_to_check = SYMBOLS

    print(f"\n[{datetime.now()}] 开始执行检查，目标币种: {', '.join(symbols_to_check)}...")
    
    # 初始化所有指标检查器
    indicator_checkers = [VolumeSignal(), OpenInterestSignal(), LSRatioSignal()]
    
    for symbol in symbols_to_check:
        print(f"--- 正在检查 {symbol} ---")
        df = get_binance_data(symbol)
        
        if df.empty:
            print(f"未能获取 {symbol} 的数据，跳过。")
            continue
            
        for checker in indicator_checkers:
            signal = checker.check(df)
            if signal:
                print(f"为 {symbol} 找到潜在信号: {signal['primary_signal']}")
                # 检查是否应该发送警报
                should_send, prev_signal = state_manager.should_send_alert(symbol, signal)
                if should_send:
                    # 获取 AI 解读
                    ai_insight = get_gemini_interpretation(symbol, TIMEFRAME, signal, previous_signal=prev_signal)
                    # 发送通知
                    send_alert(symbol, signal, ai_insight)
                    # 防止短时间重复发送同一个信号
                    time.sleep(2)
    
    print("检查完成。")

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
