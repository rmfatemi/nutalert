import apprise
from typing import Tuple

from nutalert.utils import setup_logger


logger = setup_logger(__name__)


class NutAlertNotifier:
    def __init__(self, config, container_name: str | None = None):
        self.config = config
        self.container = container_name

    def notify_apprise(self, title: str, message: str, file_path: str | None = None) -> Tuple[bool, str]:
        ap_obj = apprise.Apprise()
        notifications_cfg = self.config.get("notifications", {})
        urls_config = notifications_cfg.get("urls", "")
        if not urls_config:
            error_msg = "no apprise urls configured"
            logger.error(error_msg)
            return False, error_msg
        if isinstance(urls_config, str):
            for line in urls_config.strip().splitlines():
                url = line.strip()
                if url and not url.startswith("#"):
                    ap_obj.add(url)
        elif isinstance(urls_config, list):
            for item in urls_config:
                if isinstance(item, str):
                    if item:
                        ap_obj.add(item)
                elif isinstance(item, dict):
                    if item.get("enabled", True):
                        url = item.get("url")
                        if url:
                            ap_obj.add(url)
        if not ap_obj.servers:
            error_msg = "no enabled apprise urls found"
            logger.error(error_msg)
            return False, error_msg
        short_body = ("this message had to be shortened: \n" if len(message) > 1900 else "") + message[:1900]
        try:
            logger.info(f"sending notification to {len(ap_obj.servers)} service(s)...")
            if file_path:
                result = ap_obj.notify(title=title, body=short_body, attach=file_path)
            else:
                result = ap_obj.notify(title=title, body=short_body)
            if result:
                logger.info("notification sent successfully")
                return True, ""
            else:
                error_msg = "notification delivery failed - check url format and service availability"
                logger.error(error_msg)
                return False, error_msg
        except Exception as exc:
            error_msg = f"notification error: {exc}"
            logger.error(error_msg)
            return False, error_msg

    def send_all(self, title: str, message: str, file_path: str | None = None) -> bool:
        notifications_cfg = self.config.get("notifications", {})
        if notifications_cfg.get("enabled", False) and notifications_cfg.get("urls"):
            success, _ = self.notify_apprise(title, message, file_path)
            return success
        return False
