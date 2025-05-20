import re

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
        "actual_runtime_minutes": actual_runtime_minutes
    }
    try:
        result = eval(formula_expr, {"__builtins__": {}}, env)
        return bool(result)
    except Exception as e:
        logger.error("error evaluating alert formula: %s", e)
        return True


def process_nut_data():
    config = load_config()
    raw_data = fetch_nut_data(
        host=config["nut_server"]["host"],
        port=config["nut_server"]["port"],
        command=config["nut_server"]["command"],
        timeout=config["nut_server"]["timeout"]
    )
    if not raw_data:
        logger.error("no data received from nut server")
        return
    nut_values = parse_nut_data(raw_data)
    logger.info("parsed nut data: %s", nut_values)
    if should_alert(nut_values, config):
        logger.warning("alert condition met! sending alert...")
        preset = config["runtime_formula"]["selected"]
        alert_message = config["runtime_formula"]["alert_messages"].get(preset, "ups alert: conditions not met")
        title = "nutalert notification"
        notifier = NutAlertNotifier(config)
        notifier.send_all(title=title, message=alert_message)
    else:
        logger.info("ups conditions are within acceptable range.")

if __name__ == "__main__":
    process_nut_data()
