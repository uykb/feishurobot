import json
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL_NAME, DEEPSEEK_API_BASE_URL

if DEEPSEEK_API_KEY:
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_API_BASE_URL,
    )
else:
    client = None
    print("Warning: DEEPSEEK_API_KEY is not set. AI interpretation will be disabled.")

def get_ai_interpretation(symbol: str, timeframe: str, signal_data: dict, previous_signal: dict = None):
    if not client:
        return "AI interpretation disabled (API key missing)."
    """
    使用AI模型解读指标异动信号及其市场背景
    """
    # 为了可读性，将数据包拆分
    primary_signal = signal_data.get('primary_signal', {})
    market_context = signal_data.get('market_context', {})

    system_prompt = """You are a world-class crypto market analyst. Your analysis is concise, data-driven, and directly actionable for experienced traders. You avoid generic advice and focus on interpreting the provided data to form a coherent market thesis. Do not use emojis. Never give financial advice.

Your Task is to analyze the primary signal in conjunction with the broader market context provided. Structure your interpretation in the following format, and your entire analysis must be in Chinese:

【核心信号解读】What does the specific primary signal mean in technical terms? (e.g., "A volume Z-Score of 3.5 indicates an extreme deviation from the recent average, suggesting a major market participant's activity.")
【市场背景分析】How does the market context (recent price action, key indicators, CVD) support or contradict the primary signal? (e.g., "This volume spike is occurring as the price is testing a key resistance level identified by the EMA_26, and the RSI is approaching overbought territory. The recent CVD trend has been flat, suggesting this may be a climactic top rather than a breakout.")
【潜在影响与后续关注】What is the most likely short-term impact, and what specific price levels or indicator behaviors should be monitored for confirmation or invalidation? (e.g., "Potential for a short-term reversal. Watch for a price rejection at the $68,200 level. Confirmation would be a bearish divergence on the RSI on the next price swing.")
"""

    # 将K线数据格式化为更易读的字符串
    klines_str = "\n".join([f"  - O:{k['open']:.2f} H:{k['high']:.2f} L:{k['low']:.2f} C:{k['close']:.2f} V:{k['volume']:,.0f}" for k in market_context.get('recent_klines', [])])

    # 构建历史信号部分
    if previous_signal:
        prev_signal_context = f"""**0. Previous Signal Context:**
This is an update to a previously triggered signal. Your task is to analyze if the new signal represents a continuation, acceleration, or potential reversal of the situation.
Previous Signal:
```json
{json.dumps(previous_signal, indent=2)}
```
"""
    else:
        prev_signal_context = """**0. Context:**
This is a new signal alert.
"""

    user_prompt = f"""{prev_signal_context}
**Asset:** {symbol}
**Timeframe:** {timeframe}

**1. Primary Signal Detected:**
```json
{json.dumps(primary_signal, indent=2)}
```

**2. Market Context Snapshot:**
*   **Key On-Chain & Market Indicators:**
    ```json
    {json.dumps(market_context.get('key_indicators', {}), indent=2)}
    ```
*   **Key Technical Indicators:**
    ```json
    {json.dumps(market_context.get('technical_indicators', {}), indent=2)}
    ```
*   **Recent Price Action (Last 16 periods, newest first):**
{klines_str}
"""

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6, # 稍微提高一点创造性以进行更好的分析
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling custom API: {e}")
        return "AI interpretation failed."
