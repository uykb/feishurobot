import pandas as pd
import pandas_ta as ta
from config import *

def _create_market_snapshot(df: pd.DataFrame, primary_signal: dict):
    """
    创建一个包含主要信号和市场背景快照的丰富数据包。
    """
    # 1. 提取最近16条K线数据
    recent_klines = df.tail(16).copy()
    klines_data = recent_klines[['open', 'high', 'low', 'close', 'volume']].to_dict(orient='records')

    # 2. 提取关键指标的最新值
    latest_indicators = df.tail(1).copy()
    context_indicators = {
        "oi": f"${latest_indicators['oi'].iloc[0]:,.0f}",
        "price": f"{latest_indicators['close'].iloc[0]:.2f}",
        "volume": f"{latest_indicators['volume'].iloc[0]:,.0f}",
        "cvd": f"{latest_indicators['cvd'].iloc[0]:,.0f}",
        "long_short_ratio": f"{latest_indicators['ls_ratio'].iloc[0]:.3f}"
    }
    
    # 3. 计算额外的技术指标 (RSI, EMA)
    df.ta.rsi(length=14, append=True)
    df.ta.ema(length=12, append=True)
    df.ta.ema(length=26, append=True)
    
    latest_tech_indicators = df.tail(1)
    tech_indicators = {
        "rsi_14": f"{latest_tech_indicators['RSI_14'].iloc[0]:.2f}",
        "ema_12": f"{latest_tech_indicators['EMA_12'].iloc[0]:.2f}",
        "ema_26": f"{latest_tech_indicators['EMA_26'].iloc[0]:.2f}",
    }

    return {
        "primary_signal": primary_signal,
        "market_context": {
            "recent_klines": klines_data,
            "key_indicators": context_indicators,
            "technical_indicators": tech_indicators
        }
    }

def calculate_z_score(series: pd.Series, lookback: int):
    """计算 Z-Score"""
    mean = series.rolling(window=lookback).mean()
    std = series.rolling(window=lookback).std()
    return (series - mean) / std

class VolumeSignal:
    def check(self, df: pd.DataFrame):
        df['volume_z_score'] = calculate_z_score(df['volume'], VOLUME_LOOKBACK_PERIOD)
        latest = df.iloc[-1]
        if abs(latest['volume_z_score']) > VOLUME_Z_SCORE_THRESHOLD:
            signal = {
                "indicator": "Volume",
                "signal_type": "Spike Alert",
                "value": f"{latest['volume']:,.0f}",
                "z_score": f"{latest['volume_z_score']:.2f}",
                "price_change": f"{(latest['close']/df.iloc[-2]['close'] - 1):.2%}"
            }
            return _create_market_snapshot(df, signal)
        return None

class OpenInterestSignal:
    def check(self, df: pd.DataFrame):
        latest = df.iloc[-1]
        
        # 1. 24小时变化检测
        oi_24h_ago = df['oi'].iloc[-VOLUME_LOOKBACK_PERIOD]
        oi_24h_change = (latest['oi'] / oi_24h_ago) - 1
        if abs(oi_24h_change) > OI_24H_CHANGE_THRESHOLD:
            signal = {
                "indicator": "Open Interest",
                "signal_type": "24H Change Alert",
                "value": f"${latest['oi']:,.0f}",
                "change_24h": f"{oi_24h_change:+.2%}",
                "price": f"{latest['close']:.2f}"
            }
            return _create_market_snapshot(df, signal)

        # 2. 连续上涨/下跌检测
        oi_pct_change = df['oi'].pct_change()
        if (oi_pct_change.iloc[-OI_CONTINUOUS_RISE_PERIODS:] > 0).all():
            signal = {
                "indicator": "Open Interest",
                "signal_type": f"Continuous Rise ({OI_CONTINUOUS_RISE_PERIODS} periods)",
                "value": f"${latest['oi']:,.0f}",
                "price": f"{latest['close']:.2f}"
            }
            return _create_market_snapshot(df, signal)
        
        if (oi_pct_change.iloc[-OI_CONTINUOUS_RISE_PERIODS:] < 0).all():
            signal = {
                "indicator": "Open Interest",
                "signal_type": f"Continuous Fall ({OI_CONTINUOUS_RISE_PERIODS} periods)",
                "value": f"${latest['oi']:,.0f}",
                "price": f"{latest['close']:.2f}"
            }
            return _create_market_snapshot(df, signal)

        # 3. 突然剧烈变化
        if abs(oi_pct_change.iloc[-1]) > OI_SUDDEN_CHANGE_THRESHOLD:
            signal = {
                "indicator": "Open Interest",
                "signal_type": "Sudden Change Alert",
                "value": f"${latest['oi']:,.0f}",
                "change_1_period": f"{oi_pct_change.iloc[-1]:+.2%}",
                "price": f"{latest['close']:.2f}"
            }
            return _create_market_snapshot(df, signal)
            
        return None

class LSRatioSignal:
    def check(self, df: pd.DataFrame):
        df['ls_z_score'] = calculate_z_score(df['ls_ratio'], LS_RATIO_LOOKBACK_PERIOD)
        latest = df.iloc[-1]
        
        if abs(latest['ls_z_score']) > LS_RATIO_Z_SCORE_THRESHOLD:
            sentiment = "Extremely Bullish (Contrarian Bearish)" if latest['ls_z_score'] > 0 else "Extremely Bearish (Contrarian Bullish)"
            signal = {
                "indicator": "Long/Short Ratio",
                "signal_type": "Sentiment Extreme Alert",
                "value": f"{latest['ls_ratio']:.3f}",
                "z_score": f"{latest['ls_z_score']:.2f}",
                "sentiment": sentiment
            }
            return _create_market_snapshot(df, signal)
        return None
