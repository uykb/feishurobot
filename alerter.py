import requests
import json
import time
from datetime import datetime
from config import NOTIFYX_WEBHOOK_URLS, GOTIFY_URL, GOTIFY_TOKEN

def send_notifyx_alert(payload):
    """Sends a message to all configured NotifyX webhooks."""
    if not NOTIFYX_WEBHOOK_URLS:
        return

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
        time.sleep(1)

def send_gotify_alert(title, message):
    """Sends a message to the configured Gotify server."""
    if not GOTIFY_URL or not GOTIFY_TOKEN:
        return

    try:
        response = requests.post(
            f"{GOTIFY_URL}/message?token={GOTIFY_TOKEN}",
            json={"title": title, "message": message, "priority": 5},
        )
        response.raise_for_status()
        print(f"Gotify alert sent successfully to {GOTIFY_URL}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Gotify alert to {GOTIFY_URL}: {e}")

def send_alert(symbol: str, signal_data: dict, ai_interpretation: str):
    """
    Formats a message and sends it to all configured notification services.
    """
    primary_signal = signal_data.get('primary_signal', {})
    indicator_name = primary_signal.get('indicator', 'N/A')
    
    details_list = []
    for key, value in primary_signal.items():
        if key not in ['indicator', 'signal_type']:
            details_list.append(f"**{key.replace('_', ' ').title()}:** `{value}`")
    details_string = " | ".join(details_list)

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

    title = f"{symbol} 市场异动告警"
    
    notifyx_payload = {
        "content": content,
        "title": title
    }
    
    send_notifyx_alert(notifyx_payload)
    send_gotify_alert(title, content)
