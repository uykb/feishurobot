import requests
import json
from datetime import datetime
from config import NOTIFYX_WEBHOOK_URL

def send_alert(symbol: str, signal_data: dict, ai_interpretation: str):
    """
    构建并发送一个 notifyx 消息
    """
    webhook_url = NOTIFYX_WEBHOOK_URL
    if not webhook_url:
        print("NotifyX webhook URL not set.")
        return

    primary_signal = signal_data.get('primary_signal', {})
    indicator_name = primary_signal.get('indicator', 'N/A')
    
    details_list = []
    for key, value in primary_signal.items():
        if key not in ['indicator', 'signal_type']:
            details_list.append(f"**{key.replace('_', ' ').title()}:** `{value}`")
    details_string = " | ".join(details_list)

    # 格式化AI解读以适应notifyx的纯文本格式
    ai_sections = []
    sections = ai_interpretation.split('【')
    for section in sections:
        if '】' in section:
            parts = section.split('】', 1)
            title = parts[0]
            content = parts[1].strip()
            if content:
                ai_sections.append(f"【{title}】\n{content}")
    
    ai_interpretation_formatted = "\n\n".join(ai_sections)

    message = (
        f"🚨 **{symbol} 市场异动告警** 🚨\n\n"
        f"**指标:** {indicator_name}\n"
        f"**信号详情:** {details_string}\n\n"
        f"{ai_interpretation_formatted}"
    )

    payload = {
        "message": message,
        "title": f"{symbol} 市场异动告警",
        "priority": "high"
    }

    try:
        response = requests.post(webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        print("NotifyX alert sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending NotifyX alert: {e}")
