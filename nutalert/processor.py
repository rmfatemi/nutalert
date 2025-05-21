import time

from nutalert.fetcher import fetch_nut_data
from nutalert.notifier import NutAlertNotifier
from nutalert.utils import setup_logger, load_config
from nutalert.parser import parse_nut_data
from nutalert.alert import should_alert


logger = setup_logger("processor")


def process_nut_data():
    config = load_config()

    if "nut_server" not in config:
        logger.error("missing required config: nut_server")
        return

    if "host" not in config["nut_server"] or "port" not in config["nut_server"] or "timeout" not in config["nut_server"]:
        logger.error("missing required nut_server config: host, port, or timeout")
        return

    raw_data = fetch_nut_data(
        host=config["nut_server"]["host"],
        port=config["nut_server"]["port"],
        timeout=config["nut_server"]["timeout"],
    )
    if not raw_data:
        logger.error("no data received from nut server")
        return

    nut_values = parse_nut_data(raw_data)
    alert, message = should_alert(nut_values, config)

    if alert:
        logger.warning("alert condition met! sending alert...")
        logger.warning(message)
        title = "ups alert"
        notifier = NutAlertNotifier(config)
        notifier.send_all(title=title, message=message)
    else:
        logger.info(message)


if __name__ == "__main__":
    config = load_config()
    if "check_interval" not in config:
        logger.error("missing required config: check_interval")
        check_interval = 15
        logger.warning(f"using default check interval: {check_interval} seconds")
    else:
        check_interval = config["check_interval"]

    while True:
        process_nut_data()
        time.sleep(check_interval)
