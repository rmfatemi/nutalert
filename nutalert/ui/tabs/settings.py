from nicegui import ui
from typing import Any, Dict
from pydantic import ValidationError

from nutalert.config import save_config
from nutalert.ui.models import AppConfig
from nutalert.ui.theme import COLOR_THEME
from nutalert.notifier import NutAlertNotifier
from nutalert.ui.selector import ups_selector_row


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
    ui.label("NUT Server").classes("text-lg font-semibold mb-2")
    ui.label(
        "IP address or hostname of your NUT (Network UPS Tools) server. "
        "Port number for the NUT server (default: 3493). "
        "Check Interval: How often (in seconds) to poll the UPS data."
    ).classes("text-xs text-gray-500 mb-2")
    with ui.row().classes(f"w-full gap-4 p-2 rounded-md border bg-[{COLOR_THEME['card']}] items-center"):
        ui.input("Host").bind_value(config["nut_server"], "host").classes("w-48")
        ui.number("Port", min=1, max=65535, step=1).props("type=text").bind_value(config["nut_server"], "port").classes("w-32")
        ui.number("Check Interval (s)", min=5, step=1).props("type=text").bind_value(config["nut_server"], "check_interval").classes("w-48")


def basic_alert_rules(ups_config: Dict) -> None:
    ups_config.setdefault("alert_mode", "basic")
    basic_alerts_config = ups_config.get("basic_alerts", {})

    with ui.column().classes("w-full gap-4 mt-4"):
        basic_alert_card(basic_alerts_config, "battery_charge", "Battery Charge", has_min=True, has_max=False)
        basic_alert_card(basic_alerts_config, "runtime", "Battery Runtime", has_min=True, has_max=False)
        basic_alert_card(basic_alerts_config, "load", "UPS Load", has_min=False, has_max=True)
        basic_alert_card(basic_alerts_config, "input_voltage", "Input Voltage", has_min=True, has_max=True)
        ups_status_alert_card(basic_alerts_config)


def gauge_settings(gauge_config: Dict) -> None:
    ui.label("Gauge Settings").classes("text-lg font-semibold mb-2")
    ui.label(
        "Configure the display gauges for battery charge, runtime, load, and input voltage. "
        "Nominal: Normal value. Warn/High: Deviation thresholds for warnings."
    ).classes("text-xs text-gray-500 mb-2")
    icon_map = {
        "charge_remaining": "🔋",
        "runtime": "⏱️",
        "load": "⚡",
        "voltage": "🔌",
    }
    with ui.row().classes(f"w-full gap-4 p-2 rounded-md border bg-[{COLOR_THEME['card']}] items-center"):
        def gauge_row(conf: Dict, key: str, title: str):
            icon = icon_map.get(key, "🛑")
            with ui.row().classes("items-center gap-2"):
                ui.label(f"{icon}").classes("text-md w-6")
                ui.label(title).classes("text-sm font-semibold w-28")
                if key == "voltage":
                    ui.number("Nominal").props("type=text").classes("w-16").bind_value(conf, "nominal")
                    ui.number("Warn").props("type=text").classes("w-16").bind_value(conf, "warn_deviation")
                    ui.number("High").props("type=text").classes("w-16").bind_value(conf, "high_deviation")
                else:
                    ui.number("Warn").props("type=text").classes("w-16").bind_value(conf, "warn_threshold")
                    ui.number("High").props("type=text").classes("w-16").bind_value(conf, "high_threshold")
        gauge_row(gauge_config.setdefault("charge_remaining", {}), "charge_remaining", "Battery Charge")
        gauge_row(gauge_config.setdefault("runtime", {}), "runtime", "Battery Runtime")
        gauge_row(gauge_config.setdefault("load", {}), "load", "UPS Load")
        gauge_row(gauge_config.setdefault("voltage", {}), "voltage", "Input Voltage")


def basic_alert_card(basic_alerts_config: Dict, key: str, title: str, has_min: bool, has_max: bool) -> None:
    alert_conf = basic_alerts_config.setdefault(key, {})
    alert_conf.setdefault("enabled", False)
    alert_conf.setdefault("message", "")
    if has_min:
        alert_conf.setdefault("min", 110.0 if key == "input_voltage" else 0.0)
    if has_max:
        alert_conf.setdefault("max", 130.0 if key == "input_voltage" else 0.0)

    icon_map = {
        "battery_charge": "🔋",
        "runtime": "⏱️",
        "load": "⚡",
        "input_voltage": "🔌",
    }
    icon = icon_map.get(key, "🛑")

    with ui.row().classes(f"w-full items-center gap-2 p-2 rounded-md border bg-[{COLOR_THEME['card']}] mb-2"):
        ui.label(f"{icon} {title}").classes("font-semibold text-md w-40")
        with ui.column().classes("gap-1 flex-grow"):
            if has_min and not has_max:
                ui.number("Below", format="%.1f").props("type=text").classes("w-24").bind_value(alert_conf, "min")
            if has_max and not has_min:
                ui.number("Above", format="%.1f").props("type=text").classes("w-24").bind_value(alert_conf, "max")
            if has_min and has_max:
                with ui.row().classes("gap-2"):
                    ui.number("Below", format="%.1f").props("type=text").classes("w-20").bind_value(alert_conf, "min")
                    ui.number("Above", format="%.1f").props("type=text").classes("w-20").bind_value(alert_conf, "max")
            ui.input("Message", placeholder="Notification message...").classes("w-full").bind_value(alert_conf, "message")
        ui.switch("Enabled").bind_value(alert_conf, "enabled").props(f'color={COLOR_THEME["primary"]}').classes("ml-4")


def ups_status_alert_card(basic_alerts_config: Dict) -> None:
    status_conf = basic_alerts_config.setdefault(
        "ups_status",
        {
            "enabled": False,
            "acceptable": ["ol", "online"],
            "message": "UPS status not in acceptable list",
            "alert_when_status_changed": False,
        },
    )
    with ui.row().classes(f"w-full items-center gap-2 p-2 rounded-md border bg-[{COLOR_THEME['card']}] mb-2"):
        ui.label("🔎 UPS Status").classes("font-semibold text-md w-40")
        with ui.column().classes("gap-1 flex-grow"):
            with ui.row().classes("w-full items-center gap-x-2"):
                alert_status_checkbox = (
                    ui.checkbox("Alert on any status change")
                    .classes("flex-1")
                    .bind_value(status_conf, "alert_when_status_changed")
                )
                acceptable_input = (
                    ui.input("Acceptable Statuses", placeholder="e.g. OL, ONLINE")
                    .classes("flex-1 ml-auto")
                    .bind_value_from(status_conf, "acceptable", lambda s: ", ".join(s or []))
                    .bind_value_to(
                        status_conf,
                        "acceptable",
                        lambda s: [i.strip().lower() for i in (s or "").split(",") if i.strip()],
                    )
                )
                acceptable_input.bind_enabled_from(alert_status_checkbox, "value", backward=lambda checked: not checked)
            ui.input("Alert Message", placeholder="Notification message...").classes("w-full").bind_value(
                status_conf, "message"
            )
        ui.switch("Enabled").bind_value(status_conf, "enabled").props(f'color={COLOR_THEME["primary"]}').classes("ml-4")


def formula_alert_rules(formula_alert_config: Dict) -> None:
    with ui.row().classes(f"w-full items-center gap-2 p-2 rounded-md border bg-[{COLOR_THEME['card']}] mb-2"):
        ui.label("🧮 Formula Alert").classes("font-semibold text-md w-40")
        with ui.column().classes("gap-1 flex-grow"):
            ui.input(label="Alert Condition", placeholder="e.g. battery_charge < 90").classes("w-full font-mono").bind_value(
                formula_alert_config, "expression"
            )
            ui.label(
                "Enter a valid Python condition. Available variables: battery_charge, ups_status, ups_load, "
                "actual_runtime_minutes, battery_voltage, input_voltage."
            ).classes("text-xs text-gray-500 mb-2")
            ui.input(label="Alert Message", placeholder="e.g. Load is {ups_load}%").classes("w-full").bind_value(
                formula_alert_config, "message"
            )
            ui.label("You can use f-strings and reference the same variables in your message.").classes(
                "text-xs text-gray-500 mb-2"
            )


def notification_settings(config: Dict) -> None:
    ui.label("Notifications").classes("text-lg font-semibold mb-2")
    ui.html(
        "Enable: Toggle to enable or disable all notifications. "
        "Cooldown: Minimum seconds between sending new alerts. "
        "URLs: List of Apprise-compatible notification URLs. "
        "Each URL can be enabled/disabled individually. "
        "Use 'Add URL' to add a new notification method. "
        "'Test Alerts' sends a test notification to all enabled URLs. "
        "See <a href='https://github.com/caronc/apprise' target='_blank' class='text-blue-600 underline'>Apprise documentation</a> for supported services."
    ).classes("text-xs text-gray-500 mb-2")
    with ui.column().classes(f"w-full gap-2 p-2 rounded-md border bg-[{COLOR_THEME['card']}]"):
        with ui.row().classes("gap-4 items-center"):
            ui.switch("Enable").bind_value(config["notifications"], "enabled").props(f'color={COLOR_THEME["primary"]}')
            ui.number("Cooldown (s)").props("type=text").bind_value(config["notifications"], "cooldown").classes("w-32")
            ui.label("Time to wait between sending notifications to prevent spam.").classes("text-xs text-gray-500 ml-1")
        with ui.column().classes("gap-2 w-full"):
            @ui.refreshable
            def url_list() -> None:
                if not config["notifications"]["urls"]:
                    ui.label("No notification URLs added.").classes("text-xs text-gray-500 self-center py-4")
                for url_obj in config["notifications"]["urls"]:
                    with ui.row().classes("w-full items-center gap-x-2"):
                        ui.input("Apprise URL", placeholder="e.g., tgram://...").classes("flex-grow").bind_value(
                            url_obj, "url"
                        )
                        ui.switch().props(f'dense color={COLOR_THEME["primary"]}').bind_value(url_obj, "enabled")
                        ui.button(
                            icon="delete",
                            on_click=lambda u=url_obj: (config["notifications"]["urls"].remove(u), url_list.refresh()),
                        ).props(f'flat dense color={COLOR_THEME["primary"]}')
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
    if not hasattr(state, "selected_ups_settings"):
        state.selected_ups_settings = state.selected_ups or (state.ups_names[0] if state.ups_names else None)

    def handle_settings_ups_tab(selected_ups):
        state.selected_ups = selected_ups
        state.selected_ups_settings = selected_ups
        if "device_settings_refresh" in ui_elements:
            ui_elements["device_settings_refresh"].refresh()

    with ui.card().classes("w-full h-full min-h-[600px] p-4"):
        with ui.grid(columns=2).classes("w-full h-full gap-4 items-stretch"):
            with ui.column().classes("items-stretch gap-y-4"):
                ups_names = state.ups_names if hasattr(state, "ups_names") else list(config.get("ups_devices", {}).keys())
                if not ups_names:
                    ui.label("No UPS devices configured.").classes("text-red-500")
                else:
                    with ui.tabs(value=state.selected_ups_settings).classes("w-full mb-2") as ups_tabs:
                        tab_objs = [ui.tab(ups_name) for ups_name in ups_names]
                    def on_tab_change(e):
                        handle_settings_ups_tab(e.args)
                    ups_tabs.on("update:model-value", on_tab_change)

                    @ui.refreshable
                    def device_settings():
                        ups_name = state.selected_ups_settings
                        ups_config = config["ups_devices"].setdefault(ups_name, {})
                        if ups_config.get("alert_mode") not in ("basic", "formula"):
                            ups_config["alert_mode"] = "basic"
                        ups_config.setdefault("basic_alerts", {})
                        ups_config.setdefault("formula_alert", {"expression": "", "message": ""})
                        ups_config.setdefault("gauge_settings", {})

                        gauge_settings(ups_config.get("gauge_settings", {}))
                        ui.separator()

                        with ui.column().classes("w-full gap-4"):
                            ui.label("Alert Settings").classes("text-lg font-semibold mb-2")
                            with ui.row().classes("items-center gap-x-4 mb-2"):
                                ui.label("Alert Mode:").classes("font-semibold")
                                ui.select(
                                    options=["basic", "formula"],
                                    value=ups_config["alert_mode"],
                                    on_change=lambda e: (ups_config.update({"alert_mode": e.value}), device_settings.refresh()),
                                )

                            if ups_config["alert_mode"] == "basic":
                                ui.label(
                                    "Set thresholds for battery charge, runtime, load, input voltage, and UPS status. "
                                    "If ANY enabled alert condition fails, an alert will be triggered (using OR logic, only for enabled ones). "
                                    "A basic alert is triggered if any enabled threshold is crossed or the UPS status is not acceptable. "
                                    "Min/Max: Set minimum/maximum acceptable values. "
                                    "Message: Custom notification message for each alert. "
                                    "Acceptable Statuses: List of UPS statuses considered normal (e.g., ol, online). "
                                    "Alert on any status change: Enable to alert only when the UPS status changes."
                                ).classes("text-xs text-gray-500 mb-2")
                                basic_alert_rules(ups_config)
                            else:
                                formula_alert_rules(ups_config.get("formula_alert", {}))

                    ui_elements["device_settings_refresh"] = device_settings
                    device_settings()

                with ui.row().classes("w-full justify-start pt-4"):
                    ui.button(
                        "Save Settings", on_click=lambda: save_settings(config), icon="save", color=COLOR_THEME["primary"]
                    )

            with ui.column().classes("items-stretch gap-y-4"):
                nut_server_settings(config)
                notification_settings(config)
                ui.separator()

    ui_elements["settings_tab_refresh"] = lambda: build_settings_tab(state, ui_elements)


def build_logs_tab(state, ui_elements: Dict[str, Any]):
    with ui.card().classes("w-full flex flex-col items-stretch gap-y-4"):
        ui.label("Live Logs").classes("text-lg font-semibold self-center")
        ui_elements["log_view"] = ui.log(max_lines=1000).classes(
            f"w-full font-mono text-sm flex-grow bg-[{COLOR_THEME['card']}] p-2 rounded-md"
        )
