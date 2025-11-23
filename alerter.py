import requests
import json
import time
from datetime import datetime
from config import NOTIFYX_WEBHOOK_URLS

def send_alert(symbol: str, signal_data: dict, ai_interpretation: str):
    """
    构建并向所有配置的 notifyx webhook 发送消息
    """
    if not NOTIFYX_WEBHOOK_URLS:
        print("NotifyX webhook URLs are not set.")
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

    content = (
        f"🚨 **{symbol} 市场异动告警** 🚨\n\n"
        f"**指标:** {indicator_name}\n"
        f"**信号详情:** {details_string}\n\n"
        f"{ai_interpretation_formatted}"
    )

    payload = {
        "content": content,
        "title": f"{symbol} 市场异动告警"
    }

    for webhook_token_or_url in NOTIFYX_WEBHOOK_URLS:
        if webhook_token_or_url.startswith('http'):
            webhook_url = webhook_token_or_url
        else:
            webhook_url = f"https://www.notifyx.cn/api/v1/send/{webhook_token_or_url}"
        try:
            response = requests.post(webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            print(f"NotifyX alert sent successfully to {webhook_url}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending NotifyX alert to {webhook_url}: {e}")
        time.sleep(1) # a brief pause to prevent rate-limiting issues
