import base64
import apprise
import requests
import socket
import urllib.parse

from nutalert.utils import setup_logger


logger = setup_logger("notifier")


class NutAlertNotifier:
    def __init__(self, config, container_name: str = None):
        self.config = config
        self.container = container_name

    def _assemble_ntfy_options(self) -> dict:
        ntfy_cfg = self.config["notifications"]["ntfy"]
        opts = {
            "url": ntfy_cfg["url"],
            "topic": ntfy_cfg["topic"],
            "tags": ntfy_cfg["tags"],
            "priority": ntfy_cfg["priority"],
        }
        if "containers" in self.config and self.container in self.config["containers"]:
            cconfig = self.config["containers"][self.container]
            opts["topic"] = cconfig.get("ntfy_topic", opts["topic"])
            opts["tags"] = cconfig.get("ntfy_tags", opts["tags"])
            opts["priority"] = cconfig.get("ntfy_priority", opts["priority"])
        if ntfy_cfg.get("token"):
            token_value = (
                ntfy_cfg["token"].get_secret_value()
                if hasattr(ntfy_cfg["token"], "get_secret_value")
                else ntfy_cfg["token"]
            )
            opts["authorization"] = f"Bearer {token_value}"
        elif ntfy_cfg.get("username") and ntfy_cfg.get("password"):
            username = ntfy_cfg["username"]
            password = (
                ntfy_cfg["password"].get_secret_value()
                if hasattr(ntfy_cfg["password"], "get_secret_value")
                else ntfy_cfg["password"]
            )
            creds = f"{username}:{password}"
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
                        resp = requests.post(
                            f"{options['url']}/{options['topic']}",
                            data=fp,
                            headers=hdrs,
                        )
            else:
                resp = requests.post(
                    f"{options['url']}/{options['topic']}",
                    data=short_msg,
                    headers=hdrs,
                )
            if resp.status_code == 200:
                logger.info("ntfy notification sent successfully")
                return True
            else:
                logger.error("failed to send ntfy notification: %s", resp.text)
        except Exception as exc:
            logger.error("exception in ntfy notification: %s", exc)
        return False

    def notify_apprise(self, title: str, message: str, file_path: str = None) -> bool:
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

    def notify_webhook(
        self, title: str, message: str, file_path: str = None, keywords: str = None, hostname: str = None
    ) -> bool:
        payload = {
            "container": self.container,
            "keywords": keywords,
            "title": title,
            "message": message,
            "host": hostname,
        }
        webhook_cfg = self.config["notifications"]["webhook"]
        hook_url = webhook_cfg["url"]
        hook_hdrs = webhook_cfg["headers"]
        try:
            resp = requests.post(hook_url, json=payload, headers=hook_hdrs, timeout=10)
            if resp.status_code == 200:
                logger.info("webhook notification sent successfully")
                return True
            else:
                logger.error("failed to send webhook notification: %s", resp.text)
        except Exception as exc:
            logger.error("exception sending webhook: %s", exc)
        return False

    def notify_tcp(self, title: str, message: str) -> None:
        tcp_cfg = self.config["notifications"].get("tcp")
        if not tcp_cfg or not tcp_cfg.get("enabled", False):
            logger.error("tcp notification is not configured or disabled.")
            return
        host = tcp_cfg.get("host")
        port = tcp_cfg.get("port")
        if not host or not port:
            logger.error("tcp notification configuration missing host or port.")
            return
        try:
            with socket.create_connection((host, port), timeout=5) as sock:
                content = f"{title}: {message}\n"
                sock.sendall(content.encode("utf-8"))
            logger.info("tcp notification sent successfully")
        except Exception as exc:
            logger.error("error sending tcp notification: %s", exc)

    def send_all(
        self, title: str, message: str, file_path: str = None, keywords: str = None, hostname: str = None
    ) -> None:
        notifications_cfg = self.config.get("notifications", {})
        if (
            "ntfy" in notifications_cfg
            and notifications_cfg["ntfy"].get("url")
            and notifications_cfg["ntfy"].get("topic")
        ):
            self.notify_ntfy(title, message, file_path)
        if "apprise" in notifications_cfg and notifications_cfg["apprise"].get("url"):
            self.notify_apprise(title, message, file_path)
        if "webhook" in notifications_cfg and notifications_cfg["webhook"].get("url"):
            self.notify_webhook(title, message, file_path, keywords, hostname)
        if "tcp" in notifications_cfg and notifications_cfg["tcp"].get("enabled", False):
            self.notify_tcp(title, message)
