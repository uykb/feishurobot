import requests
import pandas as pd
from config import TIMEFRAME, DATA_FETCH_LIMIT, TOP_N_SYMBOLS

BASE_URL = "https://fapi.binance.com"

def get_top_liquid_symbols():
    """获取币安期货市场流动性最高的 N 个 USDT 交易对"""
    try:
        ticker_url = f"{BASE_URL}/fapi/v1/ticker/24hr"
        tickers = requests.get(ticker_url).json()
        
        # 过滤出 USDT 永续合约并转换为 DataFrame
        usdt_futures = [t for t in tickers if t['symbol'].endswith('USDT')]
        df = pd.DataFrame(usdt_futures)
        
        # 将交易量转换为数值类型以便排序
        df['quoteVolume'] = pd.to_numeric(df['quoteVolume'])
        
        # 按 24 小时交易额降序排序
        top_symbols = df.sort_values(by='quoteVolume', ascending=False)
        
        # 提取前 N 个币种的名称
        symbol_list = top_symbols['symbol'].head(TOP_N_SYMBOLS).tolist()
        
        print(f"动态获取到流动性前 {TOP_N_SYMBOLS} 的币种: {', '.join(symbol_list)}")
        return symbol_list
        
    except Exception as e:
        print(f"动态获取热门币种列表失败: {e}")
        return []

def get_binance_data(symbol: str):
    """获取一个币种的所有相关数据：K-line, OI, L/S Ratio"""
    try:
        # 1. 获取K线数据 (价格, 成交量)
        klines_url = f"{BASE_URL}/fapi/v1/klines"
        params = {'symbol': symbol, 'interval': TIMEFRAME, 'limit': DATA_FETCH_LIMIT}
        klines_data = requests.get(klines_url, params=params).json()
        
        df = pd.DataFrame(klines_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base_asset_volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

        # 4. 计算 CVD (Cumulative Volume Delta)
        volume_delta = df['taker_buy_base_asset_volume'] - (df['volume'] - df['taker_buy_base_asset_volume'])
        df['cvd'] = volume_delta.cumsum()
        
        # 2. 获取持仓量 (OI)
        oi_url = f"{BASE_URL}/futures/data/openInterestHist"
        oi_params = {'symbol': symbol, 'period': TIMEFRAME, 'limit': DATA_FETCH_LIMIT}
        oi_data = requests.get(oi_url, params=oi_params).json()
        oi_df = pd.DataFrame(oi_data)
        oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp'], unit='ms')
        oi_df.set_index('timestamp', inplace=True)
        df['oi'] = pd.to_numeric(oi_df['sumOpenInterestValue'])
        # 3. 获取多空比
        ls_url = f"{BASE_URL}/futures/data/globalLongShortAccountRatio"
        ls_params = {'symbol': symbol, 'period': TIMEFRAME, 'limit': DATA_FETCH_LIMIT}
        ls_data = requests.get(ls_url, params=ls_params).json()
        ls_df = pd.DataFrame(ls_data)
        ls_df['timestamp'] = pd.to_datetime(ls_df['timestamp'], unit='ms')
        ls_df.set_index('timestamp', inplace=True)
        df['ls_ratio'] = pd.to_numeric(ls_df['longShortRatio'])
        
        # 最大化保留K线数据：通过bfill和ffill的组合，填补因时间戳未对齐而在头部或中间产生的空缺
        df.bfill(inplace=True)
        df.ffill(inplace=True)
        
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()
