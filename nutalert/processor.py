import time

from nutalert.alert import should_alert
from nutalert.parser import parse_nut_data
from nutalert.notifier import NutAlertNotifier
from nutalert.utils import setup_logger, get_recent_logs
from nutalert.fetcher import fetch_nut_data, fetch_nut_ups_names


logger = setup_logger(__name__)


last_notification_time: float = 0.0


def get_ups_data_and_alerts(config: dict):
    global last_notification_time

    if not config or "nut_server" not in config:
        logger.error("'nut_server' section is missing in the configuration.")
        return {}, "configuration error", True, get_recent_logs()

    nut_server_config = config["nut_server"]
    required_keys = ["host", "port", "check_interval"]
    if not all(key in nut_server_config for key in required_keys):
        logger.error(f"nut_server config is missing one of required keys: {required_keys}")
        return {}, "configuration error", True, get_recent_logs()

    host = nut_server_config["host"]
    port = nut_server_config["port"]

    ups_names = fetch_nut_ups_names(host, port)
    if not ups_names:
        logger.error("no ups devices found on nut server.")
        return {}, "error: no ups devices found", True, get_recent_logs()

    all_nut_values = {}
    all_alerts = {}
    any_alerting = False

    for ups_name in ups_names:
        raw_data = fetch_nut_data(host, port, ups_name)
        if not raw_data:
            logger.error(f"no data received for ups '{ups_name}'.")
            all_alerts[ups_name] = ("error: no data from nut server", True)
            continue

        nut_values = parse_nut_data(raw_data)
        ups_values = nut_values.get(ups_name, {})
        all_nut_values[ups_name] = ups_values

        ups_config = config.get("ups_devices", {}).get(ups_name)
        if not ups_config:
            logger.error(
                f"missing config for ups '{ups_name}'. this should not happen if config.py is working correctly."
            )
            continue

        is_alerting, alert_message = should_alert(ups_values, ups_config)

        all_alerts[ups_name] = (alert_message, is_alerting)
        if is_alerting and "config error" not in alert_message.lower():
            logger.warning(f"[{ups_name}] alert triggered: {alert_message}")
            notifications_config = config.get("notifications", {})
            if notifications_config.get("enabled", False):
                cooldown = notifications_config.get("cooldown", 60)
                current_time = time.time()
                if current_time - last_notification_time > cooldown:
                    logger.info(f"cooldown period ({cooldown}s) has passed. sending notification.")
                    notifier = NutAlertNotifier(config)
                    notifier.send_all(title=f"UPS Alert: {ups_name}", message=alert_message)
                    last_notification_time = current_time
                else:
                    logger.info(
                        f"cooldown period ({cooldown}s) has not passed. skipping notification. "
                        f"last notification sent {current_time - last_notification_time:.0f}s ago"
                    )
            any_alerting = True
        else:
            ok_status = alert_message.split(":", 1)[-1].strip() if ":" in alert_message else alert_message
            logger.info(f"[{ups_name}] status ok: {ok_status}")

    return all_nut_values, all_alerts, any_alerting, get_recent_logs()
