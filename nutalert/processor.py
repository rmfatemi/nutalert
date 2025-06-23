import time
from typing import Tuple, Dict

from nutalert.alert import should_alert
from nutalert.parser import parse_nut_data
from nutalert.fetcher import fetch_nut_data
from nutalert.notifier import NutAlertNotifier
from nutalert.utils import setup_logger, get_recent_logs


logger = setup_logger(__name__)


last_notification_time: float = 0.0


def get_ups_data_and_alerts(config: dict):
    global last_notification_time

    default_return: Tuple[Dict, str, bool, str] = {}, "configuration error", True, get_recent_logs()

    if not config or "nut_server" not in config:
        logger.error("'nut_server' section is missing in the configuration.")
        return default_return

    nut_server_config = config["nut_server"]
    required_keys = ["host", "port", "timeout"]
    if not all(key in nut_server_config for key in required_keys):
        logger.error(f"nut_server config is missing one of required keys: {required_keys}")
        return default_return

    raw_data = fetch_nut_data(
        host=nut_server_config["host"],
        port=nut_server_config["port"],
        timeout=nut_server_config["timeout"],
    )

    if not raw_data:
        logger.error("no data received from nut server. check connection and server status.")
        return {}, "error: no data from nut server", True, get_recent_logs()

    nut_values = parse_nut_data(raw_data)
    is_alerting, alert_message = should_alert(nut_values, config)

    if is_alerting:
        if "config error" not in alert_message.lower():
            logger.warning(f"alert triggered: {alert_message}")
            notifications_config = config.get("notifications", {})
            if notifications_config.get("enabled", False):
                cooldown = notifications_config.get("cooldown", 60)
                current_time = time.time()
                if current_time - last_notification_time > cooldown:
                    logger.info(f"cooldown period ({cooldown}s) has passed. sending notification.")
                    notifier = NutAlertNotifier(config)
                    notifier.send_all(title="UPS Alert", message=alert_message)
                    last_notification_time = current_time
                else:
                    logger.info(
                        f"cooldown period ({cooldown}s) has not passed. skipping notification. "
                        f"last notification sent {current_time - last_notification_time:.0f}s ago"
                    )
    else:
        ok_status = alert_message.split(":", 1)[-1].strip() if ":" in alert_message else alert_message
        logger.info(f"status ok: {ok_status}")

    return nut_values, alert_message, is_alerting, get_recent_logs()
