import socket
import requests
import urllib3.util.connection as urllib3_cn
from config import settings

# This network's IPv6 route to api.telegram.org is dead (connect hangs in SYN_SENT well past
# any request timeout), while IPv4 connects instantly. Force IPv4 so delivery never hangs on it.
def _allowed_gai_family():
    return socket.AF_INET


urllib3_cn.allowed_gai_family = _allowed_gai_family


def send_reel(video_path: str, caption: str) -> bool:
    """Sends a rendered reel to Telegram. Returns True on success."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        print("Telegram credentials not configured, skipping delivery.")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, "rb") as video:
            files = {"video": video}
            data = {
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "caption": caption,
                "supports_streaming": True,
            }
            response = requests.post(url, files=files, data=data, timeout=120)
            response.raise_for_status()
        return True
    except Exception as e:
        print(f"Telegram delivery failed: {e}")
        return False


if __name__ == "__main__":
    pass
