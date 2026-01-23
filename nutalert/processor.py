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
        logger.error("nut_server section missing in config")
        return {}, "configuration error", True, get_recent_logs()

    nut_server_config = config["nut_server"]
    required_keys = ["host", "port", "check_interval"]
    if not all(key in nut_server_config for key in required_keys):
        logger.error(f"nut_server config missing required keys: {required_keys}")
        return {}, "configuration error", True, get_recent_logs()

    host = nut_server_config["host"]
    port = nut_server_config["port"]

    ups_names_on_server = fetch_nut_ups_names(host, port)
    if not config.get("ups_devices"):
        logger.error("no ups devices configured")
        return {}, "error: no ups devices configured", True, get_recent_logs()

    all_nut_values = {}
    all_alerts = {}
    any_alerting = False

    for ups_name in config["ups_devices"]:
        if ups_name in ups_names_on_server:
            raw_data = fetch_nut_data(host, port, ups_name)
            if not raw_data:
                logger.error(f"[{ups_name}] no data received from nut server")
                all_alerts[ups_name] = ("error: no data from nut server", True)
                continue
            nut_values = parse_nut_data(raw_data)
            ups_values = nut_values.get(ups_name, {})
            all_nut_values[ups_name] = ups_values
            ups_config = config.get("ups_devices", {}).get(ups_name)
            if not ups_config:
                logger.error(f"[{ups_name}] missing config entry")
                continue
            is_alerting, alert_message = should_alert(ups_values, ups_config)
            all_alerts[ups_name] = (alert_message, is_alerting)
            if is_alerting and "config error" not in alert_message.lower():
                logger.warning(f"[{ups_name}] alert: {alert_message}")
                notifications_config = config.get("notifications", {})
                if notifications_config.get("enabled", False):
                    cooldown = notifications_config.get("cooldown", 60)
                    current_time = time.time()
                    if current_time - last_notification_time > cooldown:
                        logger.info(f"[{ups_name}] sending notification (cooldown {cooldown}s passed)")
                        notifier = NutAlertNotifier(config)
                        notifier.send_all(title=f"UPS Alert: {ups_name}", message=alert_message)
                        last_notification_time = current_time
                    else:
                        remaining = cooldown - (current_time - last_notification_time)
                        logger.info(f"[{ups_name}] notification skipped (cooldown {remaining:.0f}s remaining)")
                any_alerting = True
            else:
                ok_status = alert_message.split(":", 1)[-1].strip() if ":" in alert_message else alert_message
                logger.info(f"[{ups_name}] ok: {ok_status}")
        else:
            logger.error(f"[{ups_name}] device not found on nut server")
            all_alerts[ups_name] = ("error: ups device not found on nut server", True)
            any_alerting = True

    return all_nut_values, all_alerts, any_alerting, get_recent_logs()
