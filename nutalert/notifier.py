import base64
import apprise
import logging
import requests
import urllib.parse


logger = logging.getLogger("nutalert.notifier")
logger.setLevel(logging.DEBUG)


class NutAlertNotifier:
    def __init__(self, config, container_name: str = None):
        self.config = config
        self.container = container_name
        self.logger = logging.getLogger("nutalert.notifier")

    def _assemble_ntfy_options(self) -> dict:
        opts = {
            "url": self.config.notifications.ntfy.url,
            "topic": self.config.notifications.ntfy.topic,
            "tags": self.config.notifications.ntfy.tags,
            "priority": self.config.notifications.ntfy.priority,
        }
        if hasattr(self.config, "containers") and self.container in self.config.containers:
            cconfig = self.config.containers[self.container]
            opts["topic"] = cconfig.get("ntfy_topic", opts["topic"])
            opts["tags"] = cconfig.get("ntfy_tags", opts["tags"])
            opts["priority"] = cconfig.get("ntfy_priority", opts["priority"])
        if self.config.notifications.ntfy.token:
            opts["authorization"] = f"Bearer {self.config.notifications.ntfy.token.get_secret_value()}"
        elif self.config.notifications.ntfy.username and self.config.notifications.ntfy.password:
            creds = f"{self.config.notifications.ntfy.username}:{self.config.notifications.ntfy.password.get_secret_value()}"
            encoded = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
            opts["authorization"] = f"Basic {encoded}"
        return opts

    def notify_ntfy(self, title: str, message: str, file_path: str = None) -> bool:
        options = self._assemble_ntfy_options()
        short_msg = ("this message had to be shortened: \n" if len(message) > 3900 else "") + message[:3900]
        hdrs = {
            "Title": title,
            "Tags": str(options.get("tags")),
            "Icon": "https://raw.githubusercontent.com/clemcer/loggifly/main/images/icon.png",
            "Priority": str(options.get("priority")),
        }
        if options.get("authorization"):
            hdrs["Authorization"] = options["authorization"]
        try:
            if file_path:
                hdrs["Filename"] = file_path.split("/")[-1]
                with open(file_path, "rb") as fp:
                    if len(short_msg) < 199:
                        resp = requests.post(
                            f"{options['url']}/{options['topic']}?message={urllib.parse.quote(short_msg)}",
                            data=fp,
                            headers=hdrs,
                        )
                    else:
                        resp = requests.post(f"{options['url']}/{options['topic']}", data=fp, headers=hdrs)
            else:
                resp = requests.post(f"{options['url']}/{options['topic']}", data=short_msg, headers=hdrs)
            if resp.status_code == 200:
                self.logger.info("ntfy notification sent successfully")
                return True
            else:
                self.logger.error("failed to send ntfy notification: %s", resp.text)
        except Exception as exc:
            self.logger.error("exception in ntfy notification: %s", exc)
        return False

    def notify_apprise(self, title: str, message: str, file_path: str = None) -> bool:
        ap_obj = apprise.Apprise()
        ap_url = (
            self.config.notifications.apprise.url.get_secret_value()
            if hasattr(self.config.notifications.apprise.url, "get_secret_value")
            else self.config.notifications.apprise.url
        )
        ap_obj.add(ap_url)
        short_body = ("this message had to be shortened: \n" if len(message) > 1900 else "") + message[:1900]
        try:
            if file_path:
                ap_obj.notify(title=title, body=short_body, attach=file_path)
            else:
                ap_obj.notify(title=title, body=short_body)
            self.logger.info("apprise notification sent successfully")
            return True
        except Exception as exc:
            self.logger.error("error sending apprise notification: %s", exc)
            return False

    def notify_webhook(self, title: str, message: str, file_path: str = None, keywords: str = None, hostname: str = None) -> bool:
        payload = {
            "container": self.container,
            "keywords": keywords,
            "title": title,
            "message": message,
            "host": hostname,
        }
        hook_url = self.config.notifications.webhook.url
        hook_hdrs = self.config.notifications.webhook.headers
        try:
            resp = requests.post(hook_url, json=payload, headers=hook_hdrs, timeout=10)
            if resp.status_code == 200:
                self.logger.info("webhook notification sent successfully")
                return True
            else:
                self.logger.error("failed to send webhook notification: %s", resp.text)
        except Exception as exc:
            self.logger.error("exception sending webhook: %s", exc)
        return False

    def notify_text(self, title: str, message: str) -> None:
        print(f"{title}: {message}")

    def send_all(self, title: str, message: str, file_path: str = None, keywords: str = None, hostname: str = None) -> None:
        if (
            self.config.notifications.ntfy
            and self.config.notifications.ntfy.url
            and self.config.notifications.ntfy.topic
        ):
            self.notify_ntfy(title, message, file_path)
        if self.config.notifications.apprise and self.config.notifications.apprise.url:
            self.notify_apprise(title, message, file_path)
        if self.config.notifications.webhook and self.config.notifications.webhook.url:
            self.notify_webhook(title, message, file_path, keywords, hostname)
        if self.config.notifications.print and self.config.notifications.print.enabled:
            self.notify_text(title, message)
