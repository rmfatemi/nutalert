import apprise

from nutalert.utils import setup_logger


logger = setup_logger(__name__)


class NutAlertNotifier:
    def __init__(self, config, container_name: str | None = None):
        self.config = config
        self.container = container_name

    def notify_apprise(self, title: str, message: str, file_path: str | None = None) -> bool:
        ap_obj = apprise.Apprise()
        notifications_cfg = self.config.get("notifications", {})
        urls_config = []

        if "apprise" in notifications_cfg:
            logger.warning("using legacy 'apprise' key in config. please update to the new format.")
            apprise_cfg = notifications_cfg.get("apprise", {})
            urls_config = apprise_cfg.get("urls", [])
            if "url" in apprise_cfg and isinstance(apprise_cfg["url"], str):
                urls_config.append(apprise_cfg["url"])
        else:
            urls_config = notifications_cfg.get("urls", [])

        if not urls_config:
            logger.error("no apprise urls found in configuration.")
            return False

        if all(isinstance(item, str) for item in urls_config):
            for url in urls_config:
                if url:
                    ap_obj.add(url)
        elif all(isinstance(item, dict) for item in urls_config):
            for item in urls_config:
                if item.get("enabled", True):
                    url = item.get("url")
                    if url:
                        ap_obj.add(url)

        if not ap_obj.servers:
            logger.error("no enabled and valid apprise urls could be added.")
            return False

        short_body = ("this message had to be shortened: \n" if len(message) > 1900 else "") + message[:1900]
        try:
            if file_path:
                ap_obj.notify(title=title, body=short_body, attach=file_path)
            else:
                ap_obj.notify(title=title, body=short_body)
            logger.info("apprise notification sent successfully")
            return True
        except Exception as exc:
            logger.error("error sending apprise notification: %s", exc)
            return False

    def send_all(self, title: str, message: str, file_path: str | None = None) -> None:
        notifications_cfg = self.config.get("notifications", {})

        if notifications_cfg.get("enabled", False) and notifications_cfg.get("urls"):
            self.notify_apprise(title, message, file_path)
            return

        apprise_cfg = notifications_cfg.get("apprise", {})
        if (
            "apprise" in notifications_cfg
            and apprise_cfg.get("enabled", False)
            and (apprise_cfg.get("url") or apprise_cfg.get("urls"))
        ):
            self.notify_apprise(title, message, file_path)
