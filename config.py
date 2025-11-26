# config.py
import os
from dotenv import load_dotenv
load_dotenv()
# --- API Keys & Webhooks ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# 处理多个 NotifyX Webhook URLs
webhook_urls_str = os.getenv("NOTIFYX_WEBHOOK_URL", "")
NOTIFYX_WEBHOOK_URLS = [url.strip() for url in webhook_urls_str.split(',') if url.strip()]

# --- Gotify Settings ---
GOTIFY_URL = os.getenv("GOTIFY_URL")
GOTIFY_TOKEN = os.getenv("GOTIFY_TOKEN")

# --- AI Model Settings ---
# DeepSeek Model Settings
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")
DEEPSEEK_API_BASE_URL = os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com/v1")

# --- Gemini Model Settings (Archived) ---
# 默认模型名称
# GEMINI_MODEL_NAME = "gemini-2.5-flash" 
# 代理或自定义API地址 (如果使用官方API，请留空或注释掉)
# GEMINI_API_BASE_URL = "https://api.uykb.eu.org/v1" 
# --- Monitoring Settings ---
# 动态币种监控开关 (True: 自动获取热门币种, False: 使用下面的 SYMBOLS 列表)
DYNAMIC_SYMBOLS = False
TOP_N_SYMBOLS = 20 # 如果开启动态监控，获取流动性前 N 名的币种

# 静态币种列表 (当 DYNAMIC_SYMBOLS = False 时生效，或作为动态获取失败时的备用列表)
SYMBOLS = ['BTCUSDT','ETHUSDT','SOLUSDT','DOGEUSDT'] # 要监控的币种列表
TIMEFRAME = '15m'                # K线周期
DATA_FETCH_LIMIT = 200           # 每次获取数据条数
# --- Indicator Thresholds ---
# Volume Anomaly
VOLUME_Z_SCORE_THRESHOLD = 2.0   # 成交量Z-Score异动阈值
VOLUME_LOOKBACK_PERIOD = 96      # 回看周期 (15m * 96 = 24 hours)
# Open Interest (OI) Anomaly
OI_LOOKBACK_PERIOD = 96          # OI回看周期
OI_CONTINUOUS_RISE_PERIODS = 4   # OI连续上涨N个周期则触发
OI_SUDDEN_CHANGE_THRESHOLD = 0.035 # OI单周期剧烈变化阈值 (5%)
OI_24H_CHANGE_THRESHOLD = 0.10   # OI 24小时变化阈值 (20%)
# Long/Short Ratio Anomaly
LS_RATIO_Z_SCORE_THRESHOLD = 2.0 # 多空比Z-Score异动阈值
LS_RATIO_LOOKBACK_PERIOD = 96    # 多空比回看周期

# --- State Management (Memory) Settings ---
# Z-Score 类信号的显著变化阈值
# 只有当新的 Z-Score 与上次发送的 Z-Score 差值的绝对值大于此阈值时，才被视为新信号
Z_SCORE_CHANGE_THRESHOLD = 0.5

# 百分比类信号的显著变化阈值 (例如 OI 变化)
# 只有当新的百分比与上次发送的百分比差值的绝对值大于此阈值时，才被视为新信号
PERCENTAGE_CHANGE_THRESHOLD = 0.05 # 5%
