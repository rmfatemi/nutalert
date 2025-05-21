import re
import time

from nutalert.fetcher import fetch_nut_data
from nutalert.notifier import NutAlertNotifier
from nutalert.utils import setup_logger, load_config


logger = setup_logger("processor")


def parse_nut_data(raw_data):
    pattern = re.compile(r'^VAR ups\s+([^ ]+)\s+"([^"]+)"$')
    nut_values = {}
    for line in raw_data.splitlines():
        m = pattern.match(line.strip())
        if m:
            key, value = m.groups()
            try:
                nut_values[key] = int(value)
            except ValueError:
                try:
                    nut_values[key] = float(value)
                except ValueError:
                    nut_values[key] = value.strip()
    return nut_values


def should_alert(nut_values, config):
    selected = config["runtime_formula"]["selected"]
    formula_expr = config["runtime_formula"]["formulas"][selected]
    actual_runtime_minutes = float(nut_values.get("battery.runtime", 0)) / 60.0
    env = {
        "ups_load": float(nut_values.get("ups.load", 0)),
        "battery_charge": float(nut_values.get("battery.charge", 0)),
        "battery_runtime": float(nut_values.get("battery.runtime", 0)),
        "battery_voltage": float(nut_values.get("battery.voltage", 0)),
        "input_voltage": float(nut_values.get("input.voltage", 0)),
        "actual_runtime_minutes": actual_runtime_minutes,
        "ups_status": nut_values.get("ups.status", "").lower()
    }
    try:
        result = eval(formula_expr, {"__builtins__": {}}, env)
        details = f"selected profile: {selected}, environment {env}"
        return bool(result), details
    except Exception as e:
        details = f"error evaluating formula '{formula_expr}' with environment {env}: {e}"
        logger.error(details)
        return True, details


def process_nut_data():
    config = load_config()
    raw_data = fetch_nut_data(
        host=config["nut_server"]["host"],
        port=config["nut_server"]["port"],
        timeout=config["nut_server"]["timeout"],
    )
    if not raw_data:
        logger.error("no data received from nut server")
        return
    nut_values = parse_nut_data(raw_data)
    alert, details = should_alert(nut_values, config)
    if alert:
        logger.warning("alert condition met! sending alert...")
        logger.warning(details)
        preset = config["runtime_formula"]["selected"]
        alert_message = config["runtime_formula"]["alert_messages"].get(preset, "ups alert: conditions not met")
        title = "nutalert notification"
        notifier = NutAlertNotifier(config)
        notifier.send_all(title=title, message=alert_message)
    else:
        logger.info("ups conditions are within acceptable range.")


if __name__ == "__main__":
    config = load_config()
    interval = config.get("check_interval", 15)
    while True:
        process_nut_data()
        time.sleep(interval)
