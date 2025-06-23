from nicegui import ui
from typing import Dict, Any
from pydantic import ValidationError

from nutalert.utils import save_config
from nutalert.ui.models import AppConfig
from nutalert.ui.theme import COLOR_THEME
from nutalert.notifier import NutAlertNotifier


def save_settings(config: Dict) -> None:
    try:
        AppConfig.model_validate(config)
        save_status = save_config(config)
        ui.notify(save_status, color="positive" if "successfully" in save_status else "negative")
    except ValidationError as e:
        ui.notify(f"Configuration Error: {e}", color="negative", multi_line=True, wrap=True)
    except Exception as e:
        ui.notify(f"An unexpected error occurred: {e}", color="negative")


def test_notifications(config: Dict) -> None:
    NutAlertNotifier(config).notify_apprise("Test Notification", "This is a test notification from nutalert.")


def nut_server_settings(config: Dict) -> None:
    ui.label("NUT Server").classes("text-lg font-semibold")
    with ui.grid(columns=4).classes("w-full gap-4 pt-4"):
        ui.input("Host").bind_value(config["nut_server"], "host")
        ui.number("Port", min=1, max=65535, step=1).bind_value(config["nut_server"], "port")
        ui.number("Timeout (s)", min=1, step=1).bind_value(config["nut_server"], "timeout")
        ui.number("Check Interval (s)", min=5, step=1).bind_value(config["nut_server"], "check_interval")


def alert_rules_settings(config: Dict) -> None:
    ui.label("Alert Rules").classes("text-xl font-semibold")
    with ui.row().classes("items-center mt-2"):
        ui.label("Alert Mode:").classes("mr-4 font-semibold")
        alert_mode_radio = (
            ui.radio(["basic", "formula"], value=config.get("alert_mode", "basic"))
            .bind_value(config, "alert_mode")
            .props(f'inline color={COLOR_THEME["primary"]}')
        )
    with ui.column().classes("w-full").bind_visibility_from(alert_mode_radio, "value", value="basic"):
        basic_alert_rules(config["basic_alerts"])
    with ui.column().classes("w-full").bind_visibility_from(alert_mode_radio, "value", value="formula"):
        formula_alert_rules(config["formula_alert"])


def basic_alert_rules(basic_alerts_config: Dict) -> None:
    with ui.column().classes("w-full gap-4 mt-4"):
        basic_alert_card(basic_alerts_config, "battery_charge", "Battery Charge", has_min=True, has_max=False)
        basic_alert_card(basic_alerts_config, "runtime", "Battery Runtime", has_min=True, has_max=False)
        basic_alert_card(basic_alerts_config, "load", "UPS Load", has_min=False, has_max=True)
        basic_alert_card(basic_alerts_config, "input_voltage", "Input Voltage", has_min=True, has_max=True)
        ups_status_alert_card(basic_alerts_config)


def basic_alert_card(config: Dict, key: str, title: str, has_min: bool, has_max: bool) -> None:
    config.setdefault(key, {})
    alert_conf = config[key]
    alert_conf.setdefault("enabled", False)
    alert_conf.setdefault("message", "")
    alert_conf.setdefault("min", 110.0 if key == "input_voltage" else 0.0)
    alert_conf.setdefault("max", 130.0 if key == "input_voltage" else 0.0)

    with ui.expansion(title, icon="rule").classes("w-full border rounded-md"):
        with ui.row().classes("w-full justify-end"):
            ui.switch("Enabled").bind_value(alert_conf, "enabled").props(f'color={COLOR_THEME["primary"]}')
        with ui.row().classes("w-full items-center"):
            if has_min and not has_max:
                ui.number("Minimum", format="%.1f").classes("flex-grow").bind_value(alert_conf, "min")
            if has_max and not has_min:
                ui.number("Maximum", format="%.1f").classes("flex-grow").bind_value(alert_conf, "max")
            if has_min and has_max:
                with ui.row().classes("w-full no-wrap"):
                    ui.number("Min", format="%.1f").bind_value(alert_conf, "min")
                    ui.number("Max", format="%.1f").bind_value(alert_conf, "max")
        ui.input("Alert Message", placeholder="Notification message...").classes("w-full pt-2").bind_value(
            alert_conf, "message"
        )


def ups_status_alert_card(config: Dict) -> None:
    config.setdefault(
        "ups_status",
        {
            "enabled": False,
            "acceptable": ["ol", "online"],
            "message": "UPS status not in acceptable list",
            "alert_when_status_changed": False,
        },
    )
    status_conf = config["ups_status"]
    with ui.expansion("UPS Status", icon="power").classes("w-full border rounded-md"):
        with ui.row().classes("w-full justify-end"):
            ui.switch("Enabled").bind_value(status_conf, "enabled").props(f'color={COLOR_THEME["primary"]}')
        ui.switch("Alert on any status change").bind_value(status_conf, "alert_when_status_changed").props(
            f'color={COLOR_THEME["primary"]}'
        )
        ui.input("Acceptable Statuses", placeholder="e.g. OL, ONLINE").bind_value_from(
            status_conf, "acceptable", lambda s: ", ".join(s or [])
        ).bind_value_to(
            status_conf, "acceptable", lambda s: [i.strip().lower() for i in (s or "").split(",") if i.strip()]
        )
        ui.input("Alert Message", placeholder="Notification message...").classes("w-full").bind_value(
            status_conf, "message"
        )


def formula_alert_rules(formula_alert_config: Dict) -> None:
    ui.input(label="Expression", placeholder="e.g. battery_charge < 90").classes("w-full font-mono").bind_value(
        formula_alert_config, "expression"
    )
    ui.input(label="Alert Message", placeholder="e.g. Load is {ups_load}%").classes("w-full").bind_value(
        formula_alert_config, "message"
    )


def notification_settings(config: Dict) -> None:
    with ui.row().classes("w-full justify-between items-center"):
        ui.label("Notifications").classes("text-lg font-semibold")
        enable_switch = (
            ui.switch("Enable").bind_value(config["notifications"], "enabled").props(f'color={COLOR_THEME["primary"]}')
        )

    with ui.column().classes("w-full").bind_visibility_from(enable_switch, "value"):

        @ui.refreshable
        def url_list() -> None:
            if not config["notifications"]["urls"]:
                ui.label("No notification URLs added.").classes("text-xs text-gray-500 self-center py-4")
            for url_obj in config["notifications"]["urls"]:
                with ui.row().classes("w-full items-center gap-x-2"):
                    ui.input("URL", placeholder="e.g., tgram://...").classes("flex-grow").bind_value(url_obj, "url")
                    ui.switch().props(f'dense color={COLOR_THEME["primary"]}').bind_value(url_obj, "enabled")
                    ui.button(
                        icon="delete",
                        on_click=lambda u=url_obj: (config["notifications"]["urls"].remove(u), url_list.refresh()),
                    ).props(f'flat dense color={COLOR_THEME["primary"]}')

        ui.number("Cooldown (s)").bind_value(config["notifications"], "cooldown")
        ui.separator().classes("my-2")

        url_list()

        with ui.row().classes("w-full items-center mt-2 gap-x-2"):
            ui.button(
                "Add URL",
                icon="add",
                color=COLOR_THEME["primary"],
                on_click=lambda: (
                    config["notifications"]["urls"].append({"url": "", "enabled": True}),
                    url_list.refresh(),
                ),
            )
            ui.button(
                "Test Alerts",
                on_click=lambda: test_notifications(config),
                icon="notification_important",
                color=COLOR_THEME["primary"],
            )


def build_settings_tab(state, ui_elements: Dict[str, Any]):
    config = state.config
    config.setdefault("nut_server", {"host": "localhost", "port": 3493, "timeout": 5, "check_interval": 15})
    config.setdefault("notifications", {"urls": [], "enabled": True, "cooldown": 60})
    config.setdefault("basic_alerts", {})
    config.setdefault("formula_alert", {"expression": "", "message": ""})
    config.setdefault("alert_mode", "basic")

    with ui.grid(columns=2).classes("w-full gap-4"):
        with ui.card().classes("w-full items-stretch gap-y-4"):
            ui.label("Settings").classes("text-semibold text-2xl self-center")

            nut_server_settings(config)
            ui.separator()
            alert_rules_settings(config)
            ui.separator()
            notification_settings(config)
            ui.separator()

            with ui.row().classes("w-full justify-start pt-4"):
                ui.button(
                    "Save Settings",
                    on_click=lambda: save_settings(config),
                    icon="save",
                    color=COLOR_THEME["primary"],
                )

        with ui.card().classes("w-full flex flex-col items-stretch gap-y-4"):
            ui.label("Live Logs").classes("text-lg font-semibold self-center")
            ui_elements["log_view"] = ui.log(max_lines=1000).classes(
                f"w-full font-mono text-sm flex-grow bg-[{COLOR_THEME['card']}] p-2 rounded-md"
            )
