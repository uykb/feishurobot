import aiohttp
import asyncio
import pandas as pd
from config import TIMEFRAME, DATA_FETCH_LIMIT, TOP_N_SYMBOLS, HTTP_PROXY, HTTPS_PROXY

BASE_URL = "https://fapi.binance.com"

async def get_top_liquid_symbols(session: aiohttp.ClientSession):
    """获取币安期货市场流动性最高的 N 个 USDT 交易对 (Async)"""
    try:
        ticker_url = f"{BASE_URL}/fapi/v1/ticker/24hr"
        proxy = HTTPS_PROXY if ticker_url.startswith('https') else HTTP_PROXY
        
        async with session.get(ticker_url, proxy=proxy) as response:
            if response.status != 200:
                print(f"Error fetching top symbols: HTTP {response.status}")
                return []
            tickers = await response.json()
        
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

async def fetch_json(session: aiohttp.ClientSession, url: str, params: dict):
    try:
        proxy = HTTPS_PROXY if url.startswith('https') else HTTP_PROXY
        async with session.get(url, params=params, proxy=proxy) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Error fetching {url}: HTTP {response.status}")
                return None
    except Exception as e:
        print(f"Exception fetching {url}: {e}")
        return None

async def get_binance_data(symbol: str, session: aiohttp.ClientSession):
    """获取一个币种的所有相关数据：K-line, OI, L/S Ratio (Async)"""
    try:
        # 1. Prepare URLs and params
        klines_url = f"{BASE_URL}/fapi/v1/klines"
        klines_params = {'symbol': symbol, 'interval': TIMEFRAME, 'limit': DATA_FETCH_LIMIT}
        
        oi_url = f"{BASE_URL}/futures/data/openInterestHist"
        oi_params = {'symbol': symbol, 'period': TIMEFRAME, 'limit': DATA_FETCH_LIMIT}
        
        ls_url = f"{BASE_URL}/futures/data/globalLongShortAccountRatio"
        ls_params = {'symbol': symbol, 'period': TIMEFRAME, 'limit': DATA_FETCH_LIMIT}
        
        # 2. Fetch all data concurrently
        klines_task = fetch_json(session, klines_url, klines_params)
        oi_task = fetch_json(session, oi_url, oi_params)
        ls_task = fetch_json(session, ls_url, ls_params)
        
        klines_data, oi_data, ls_data = await asyncio.gather(klines_task, oi_task, ls_task)
        
        if not klines_data or not oi_data or not ls_data:
            print(f"Incomplete data for {symbol}, skipping.")
            return pd.DataFrame()

        # 3. Process K-lines
        df = pd.DataFrame(klines_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base_asset_volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

        # 4. Calculate CVD
        volume_delta = df['taker_buy_base_asset_volume'] - (df['volume'] - df['taker_buy_base_asset_volume'])
        df['cvd'] = volume_delta.cumsum()
        
        # 5. Process OI
        oi_df = pd.DataFrame(oi_data)
        oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp'], unit='ms')
        oi_df.set_index('timestamp', inplace=True)
        # Handle duplicate indices if any
        oi_df = oi_df[~oi_df.index.duplicated(keep='last')]
        df['oi'] = pd.to_numeric(oi_df['sumOpenInterestValue'])
        
        # 6. Process LS Ratio
        ls_df = pd.DataFrame(ls_data)
        ls_df['timestamp'] = pd.to_datetime(ls_df['timestamp'], unit='ms')
        ls_df.set_index('timestamp', inplace=True)
        ls_df = ls_df[~ls_df.index.duplicated(keep='last')]
        df['ls_ratio'] = pd.to_numeric(ls_df['longShortRatio'])
        
        # 7. Fill missing data
        df.bfill(inplace=True)
        df.ffill(inplace=True)
        
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()
