import apprise

from nutalert.utils import setup_logger


logger = setup_logger(__name__)


class NutAlertNotifier:
    def __init__(self, config, container_name: str | None = None):
        self.config = config
        self.container = container_name

    def notify_apprise(self, title: str, message: str, file_path: str | None = None) -> bool:
        ap_obj = apprise.Apprise()
        apprise_cfg = self.config["notifications"]["apprise"]
        ap_url = (
            apprise_cfg["url"].get_secret_value()
            if hasattr(apprise_cfg["url"], "get_secret_value")
            else apprise_cfg["url"]
        )
        ap_obj.add(ap_url)
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

    def send_all(
        self,
        title: str,
        message: str,
        file_path: str | None = None,
    ) -> None:
        notifications_cfg = self.config.get("notifications", {})
        if (
            "apprise" in notifications_cfg
            and notifications_cfg["apprise"].get("enabled", False)
            and notifications_cfg["apprise"].get("url")
        ):
            self.notify_apprise(title, message, file_path)
