from nutalert.utils import setup_logger


logger = setup_logger("alert")


def prepare_ups_env(nut_values):
    ups_load = float(nut_values.get("ups.load", 0))
    battery_charge = float(nut_values.get("battery.charge", 0))
    battery_runtime = float(nut_values.get("battery.runtime", 0))
    actual_runtime_minutes = battery_runtime / 60.0
    battery_voltage = float(nut_values.get("battery.voltage", 0))
    input_voltage = float(nut_values.get("input.voltage", 0))
    ups_status = nut_values.get("ups.status", "").lower()

    return {
        "ups_load": ups_load,
        "battery_charge": battery_charge,
        "battery_runtime": battery_runtime,
        "actual_runtime_minutes": actual_runtime_minutes,
        "battery_voltage": battery_voltage,
        "input_voltage": input_voltage,
        "ups_status": ups_status,
    }


def check_battery_charge(basic_alerts, env):
    if "min" not in basic_alerts["battery_charge"]:
        logger.error("missing required config: basic_alerts.battery_charge.min")
        return "config error: battery_charge.min not specified"

    min_charge = basic_alerts["battery_charge"]["min"]
    if env["battery_charge"] < min_charge:
        if "message" not in basic_alerts["battery_charge"]:
            logger.warning("missing config: basic_alerts.battery_charge.message")
            return "battery charge below threshold"
        else:
            return basic_alerts["battery_charge"]["message"]
    return None


def check_runtime(basic_alerts, env):
    if "min" not in basic_alerts["runtime"]:
        logger.error("missing required config: basic_alerts.runtime.min")
        return "config error: runtime.min not specified"

    min_runtime = basic_alerts["runtime"]["min"]

    if env["actual_runtime_minutes"] < min_runtime:
        if "message" not in basic_alerts["runtime"]:
            logger.warning("missing config: basic_alerts.runtime.message")
            message = "runtime below minimum threshold"
        else:
            message = basic_alerts["runtime"]["message"]
        return f"{message} ({env['actual_runtime_minutes']:.1f}min < {min_runtime}min)"
    return None


def check_load(basic_alerts, env):
    if "max" not in basic_alerts["load"]:
        logger.error("missing required config: basic_alerts.load.max")
        return "config error: load.max not specified"

    max_load = basic_alerts["load"]["max"]

    if env["ups_load"] > max_load:
        if "message" not in basic_alerts["load"]:
            logger.warning("missing config: basic_alerts.load.message")
            message = "ups load exceeds maximum threshold"
        else:
            message = basic_alerts["load"]["message"]
        return f"{message} ({env['ups_load']:.1f}% > {max_load}%)"
    return None


def check_input_voltage(basic_alerts, env):
    if env["input_voltage"] <= 0:
        return None

    if "min" not in basic_alerts["input_voltage"] or "max" not in basic_alerts["input_voltage"]:
        logger.error("missing required config: basic_alerts.input_voltage.min or max")
        return "config error: voltage min/max not specified"

    min_voltage = basic_alerts["input_voltage"]["min"]
    max_voltage = basic_alerts["input_voltage"]["max"]

    if env["input_voltage"] < min_voltage or env["input_voltage"] > max_voltage:
        if "message" not in basic_alerts["input_voltage"]:
            logger.warning("missing config: basic_alerts.input_voltage.message")
            message = "input voltage outside acceptable range"
        else:
            message = basic_alerts["input_voltage"]["message"]
        return f"{message} ({env['input_voltage']:.1f}v)"
    return None


def check_ups_status(basic_alerts, env):
    if not env["ups_status"]:
        return None

    if "acceptable" not in basic_alerts["ups_status"]:
        logger.error("missing required config: basic_alerts.ups_status.acceptable")
        return "config error: acceptable ups statuses not defined"

    acceptable_statuses = basic_alerts["ups_status"]["acceptable"]
    if env["ups_status"] not in acceptable_statuses:
        if "message" not in basic_alerts["ups_status"]:
            logger.warning("missing config: basic_alerts.ups_status.message")
            message = "ups status not in acceptable list"
        else:
            message = basic_alerts["ups_status"]["message"]
        if _should_skip_due_to_unchanged_status(basic_alerts, env["ups_status"]):
            return None
        return f"{message} ({env['ups_status']})"
    return None


previous_ups_status: str = ""


def _should_skip_due_to_unchanged_status(basic_alerts, current_status: str) -> bool:
    global previous_ups_status
    if not _is_enabled_alert_when_status_changed(basic_alerts):
        return False

    logger.info("'alert_when_status_changed' is true")
    if current_status == previous_ups_status:
        logger.info(f"ups status unchanged: {current_status} (no alert)")
        return True

    previous_ups_status = current_status
    return False


def _is_enabled_alert_when_status_changed(basic_alerts) -> bool:
    return basic_alerts["ups_status"].get("alert_when_status_changed", False)


def check_basic_alerts(config, env):
    if "basic_alerts" not in config:
        logger.error("missing required config: basic_alerts")
        return ["config error: basic_alerts not specified"]

    basic_alerts = config["basic_alerts"]
    alerts_triggered = []

    if "battery_charge" in basic_alerts and basic_alerts["battery_charge"].get("enabled"):
        alert = check_battery_charge(basic_alerts, env)
        if alert:
            alerts_triggered.append(alert)

    if "runtime" in basic_alerts and basic_alerts["runtime"].get("enabled"):
        alert = check_runtime(basic_alerts, env)
        if alert:
            alerts_triggered.append(alert)

    if "load" in basic_alerts and basic_alerts["load"].get("enabled"):
        alert = check_load(basic_alerts, env)
        if alert:
            alerts_triggered.append(alert)

    if "input_voltage" in basic_alerts and basic_alerts["input_voltage"].get("enabled"):
        alert = check_input_voltage(basic_alerts, env)
        if alert:
            alerts_triggered.append(alert)

    if "ups_status" in basic_alerts and basic_alerts["ups_status"].get("enabled"):
        alert = check_ups_status(basic_alerts, env)
        if alert:
            alerts_triggered.append(alert)

    return alerts_triggered


def check_formula_alert(config, env):
    if "formula_alert" not in config:
        logger.error("missing required config: formula_alert")
        return True, "ups alert: configuration error - formula_alert not specified"

    formula_alert = config["formula_alert"]

    if "expression" not in formula_alert:
        logger.error("missing required config: formula_alert.expression")
        return True, "ups alert: configuration error - formula expression not specified"

    formula_expr = formula_alert["expression"]

    if "message" not in formula_alert:
        logger.warning("missing config: formula_alert.message")
        alert_message = "ups alert: formula conditions not met"
    else:
        try:
            alert_message = formula_alert["message"].format(**env)
        except KeyError as e:
            error_msg = f"invalid variable in formula message: {e}"
            logger.error(error_msg)
            return True, f"ups alert: {error_msg}"

    try:
        result = eval(formula_expr, {"__builtins__": {}}, env)
        if result:
            return True, alert_message
        else:
            return (
                False,
                (
                    f"ups ok: {env['actual_runtime_minutes']:.1f}min runtime, {env['ups_load']}% load,"
                    f" {env['battery_charge']}% charge"
                ),
            )
    except Exception as e:
        error_msg = f"error evaluating formula '{formula_expr}': {e}"
        logger.error(error_msg)
        return True, f"ups alert: {error_msg}"


def should_alert(nut_values, config):
    env = prepare_ups_env(nut_values)

    if "alert_mode" not in config:
        logger.error("missing required config: alert_mode")
        return True, "ups alert: configuration error - alert_mode not specified"

    alert_mode = config["alert_mode"]

    if alert_mode == "basic":
        alerts_triggered = check_basic_alerts(config, env)

        if alerts_triggered:
            return True, "ups alert: " + "; ".join(alerts_triggered)
        else:
            return (
                False,
                (
                    f"ups ok: {env['actual_runtime_minutes']:.1f} min runtime, {env['ups_load']}% load,"
                    f" {env['battery_charge']}% charge"
                ),
            )

    elif alert_mode == "formula":
        return check_formula_alert(config, env)
    else:
        logger.error(f"unknown alert mode '{alert_mode}'")
        return True, f"ups alert: unknown alert mode '{alert_mode}'"
