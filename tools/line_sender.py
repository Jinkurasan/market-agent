"""
LINE公式アカウントから全フォロワーへブロードキャスト送信するツール。
"""
import httpx
from config import LINE_CHANNEL_ACCESS_TOKEN


def send_line_broadcast(message: str) -> dict:
    """LINE公式アカウントの全フォロワーにメッセージを配信する"""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        return {"status": "skipped", "message": "LINE_CHANNEL_ACCESS_TOKENが未設定"}

    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [{"type": "text", "text": message}]
    }
    try:
        resp = httpx.post(
            "https://api.line.me/v2/bot/message/broadcast",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            return {"status": "success", "message": "LINE配信完了"}
        else:
            return {"status": "failed", "code": resp.status_code, "error": resp.text}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
