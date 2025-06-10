# ==============================================================================
# File: nutalert/processor.py
# ==============================================================================
from nutalert.fetcher import fetch_nut_data
from nutalert.parser import parse_nut_data
from nutalert.alert import should_alert
from nutalert.utils import setup_logger, load_config, get_recent_logs

# Setup one logger for this file. It will inherit the handlers from the root setup.
logger = setup_logger(__name__)

def get_ups_data_and_alerts():
    """
    The core function that fetches NUT data, checks for alerts, and returns
    all necessary information for the GUI.
    """
    config = load_config()

    # Default return values in case of an early exit
    default_return = {}, "Configuration error", True, get_recent_logs()

    if not config or "nut_server" not in config:
        logger.error("'nut_server' section is missing in the configuration.")
        return default_return

    nut_server_config = config["nut_server"]
    required_keys = ["host", "port", "timeout"]
    if not all(key in nut_server_config for key in required_keys):
        logger.error(f"nut_server config is missing one of required keys: {required_keys}")
        return default_return

    # Fetch raw data from the NUT server
    raw_data = fetch_nut_data(
        host=nut_server_config["host"],
        port=nut_server_config["port"],
        timeout=nut_server_config["timeout"],
    )

    if not raw_data:
        logger.error("No data received from NUT server. Check connection and server status.")
        # Return empty data but with the relevant error message and logs
        return {}, "Error: No data from NUT server", True, get_recent_logs()

    # Parse the data and check for alerts
    nut_values = parse_nut_data(raw_data)
    is_alerting, alert_message = should_alert(nut_values, config)

    # Log the outcome
    if is_alerting:
        # Avoid logging the full message if it's a config error, as it's not a real-time status
        if "config error" not in alert_message.lower():
            logger.warning(f"Alert Triggered: {alert_message}")
    else:
        # Log the "OK" status for visibility
        ok_status = alert_message.split(":", 1)[-1].strip() if ":" in alert_message else alert_message
        logger.info(f"Status OK: {ok_status}")

    # Return everything the frontend needs
    return nut_values, alert_message, is_alerting, get_recent_logs()