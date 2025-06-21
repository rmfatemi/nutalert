from typing import Dict
from nicegui import ui
from pydantic import ValidationError

from nutalert.ui.models import AppConfig
from nutalert.notifier import NutAlertNotifier
from nutalert.utils import save_config
from nutalert.ui.theme import COLOR_THEME


def build_settings_tab(state):
    state.config.setdefault("nut_server", {"host": "localhost", "port": 3493, "timeout": 5, "check_interval": 15})
    state.config.setdefault("notifications", {"urls": [], "enabled": False, "cooldown": 60})
    state.config.setdefault("basic_alerts", {})
    state.config.setdefault("formula_alert", {"expression": "", "message": ""})

    with ui.column().classes("w-full gap-y-6"):
        with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
            ui.label("NUT Server").classes("text-lg font-semibold")
            
            with ui.row().classes("p-2 rounded-md bg-yellow-900/50 w-full"):
                 with ui.row().classes("items-center gap-x-2"):
                    ui.icon("warning", color="amber")
                    ui.label("Changes to Host, Port, or Timeout require a manual application restart to take effect.").classes("text-xs")

            with ui.grid(columns=4).classes("w-full gap-x-8 pt-4"):
                ui.input("Host").bind_value(state.config["nut_server"], "host")
                ui.number("Port", min=1, max=65535, step=1).bind_value(state.config["nut_server"], "port")
                ui.number("Timeout (s)", min=1, step=1).bind_value(state.config["nut_server"], "timeout")
                ui.number("Check Interval (s)", min=5, step=1).bind_value(state.config["nut_server"], "check_interval")

        with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
            ui.label("Alert Rules").classes("text-xl font-semibold")
            alert_mode_select = ui.select(["basic", "formula"], label="Alert Mode").bind_value(state.config, "alert_mode").classes("mt-2")
            
            with ui.column().classes('w-full').bind_visibility_from(alert_mode_select, 'value', value='basic'):
                with ui.grid(columns=2).classes('w-full gap-4'):
                    def build_basic_alert_card(key: str, title: str, guide: str, has_min: bool, has_max: bool):
                        state.config["basic_alerts"].setdefault(key, {})
                        alert_conf = state.config["basic_alerts"][key]
                        alert_conf.setdefault("enabled", False); alert_conf.setdefault("message", "")
                        alert_conf.setdefault("min", 110.0 if key == "input_voltage" else 0.0)
                        alert_conf.setdefault("max", 130.0 if key == "input_voltage" else 0.0)
                        with ui.card().classes('w-full'):
                            with ui.row().classes("w-full justify-between"):
                                ui.label(title).classes("text-lg font-semibold")
                                ui.switch().bind_value(alert_conf, "enabled")
                            ui.label(guide).classes("text-xs text-gray-400 -mt-2 mb-2")
                            if has_min and not has_max: ui.number("Minimum", format='%.1f').classes('w-full').bind_value(alert_conf, "min")
                            if has_max and not has_min: ui.number("Maximum", format='%.1f').classes('w-full').bind_value(alert_conf, "max")
                            if has_min and has_max:
                                with ui.row().classes('w-full'):
                                    ui.number("Min", format='%.1f').bind_value(alert_conf, "min")
                                    ui.number("Max", format='%.1f').bind_value(alert_conf, "max")
                            ui.input("Alert Message", placeholder="Notification message...").classes('w-full').bind_value(alert_conf, "message")
                    
                    build_basic_alert_card("battery_charge", "Battery Charge", "Alert when charge (%) is below a value.", True, False)
                    build_basic_alert_card("runtime", "Battery Runtime", "Alert when runtime (minutes) is below a value.", True, False)
                    build_basic_alert_card("load", "UPS Load", "Alert when load (%) is above a value.", False, True)
                    build_basic_alert_card("input_voltage", "Input Voltage", "Alert when voltage is outside a range.", True, True)

                    state.config["basic_alerts"].setdefault("ups_status", {"enabled": False, "acceptable": ['ol', 'online'], "message": "UPS status not in acceptable list", "alert_when_status_changed": False})
                    status_conf = state.config["basic_alerts"]["ups_status"]
                    with ui.card().classes('w-full'):
                        with ui.row().classes("w-full justify-between"):
                            ui.label("UPS Status").classes("text-lg font-semibold")
                            ui.switch().bind_value(status_conf, "enabled")
                        ui.label("Alert when the UPS status is not 'normal'.").classes("text-xs text-gray-400 -mt-2 mb-2")
                        acceptable_input = ui.input("Acceptable Statuses", placeholder="e.g. OL, ONLINE").bind_value_from(status_conf, 'acceptable', lambda l: ', '.join(l or [])).bind_value_to(status_conf, 'acceptable', lambda s: [i.strip().lower() for i in (s or '').split(',') if i.strip()])
                        ui.input("Alert Message", placeholder="Notification message...").classes('w-full').bind_value(status_conf, "message")
                        ui.switch("Alert on any status change").bind_value(status_conf, "alert_when_status_changed")

            with ui.column().classes('w-full').bind_visibility_from(alert_mode_select, 'value', value='formula'):
                formula_conf = state.config["formula_alert"]
                ui.input(label="Expression", placeholder="e.g. battery_charge < 90").classes("w-full font-mono").bind_value(formula_conf, "expression")
                ui.label("A Python expression that evaluates to True to trigger an alert.").classes("text-xs text-gray-400 -mt-2")
                ui.input(label="Alert Message", placeholder="e.g. Load is {ups_load}%").classes("w-full").bind_value(formula_conf, "message")
                ui.label("The message to send. You can use f-string-like placeholders.").classes("text-xs text-gray-400 -mt-2")

        with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Notifications").classes("text-lg font-semibold")
                ui.switch("Enable All Notifications").bind_value(state.config["notifications"], "enabled")
            ui.number("Cooldown (s)").tooltip("Time to wait before sending a notification for the same alert again.").bind_value(state.config["notifications"], "cooldown")
            ui.separator().classes("my-4")
            ui.label("Notification URLs").classes("text-md font-semibold")
            ui.label("Add one or more Apprise-compatible notification service URLs.").classes("text-xs text-gray-400")
            url_list = ui.column().classes("w-full gap-y-2 mt-2")
            
            def add_url_row(url_obj: Dict = None):
                if url_obj is None: url_obj = {"url": "", "enabled": True}; state.config["notifications"]["urls"].append(url_obj)
                else: url_obj.setdefault("url", ""); url_obj.setdefault("enabled", True)
                with url_list:
                    with ui.row().classes("w-full items-center gap-x-2") as row:
                        ui.input("URL", placeholder="e.g., tgram://...").classes("flex-grow").bind_value(url_obj, "url")
                        with ui.element('div').classes('w-32'): ui.switch("Enabled").bind_value(url_obj, "enabled")
                        ui.button(icon="delete", on_click=lambda: (state.config["notifications"]["urls"].remove(url_obj),row.delete())).props('flat dense color=negative')
            
            for url in state.config["notifications"]["urls"]: add_url_row(url)
            
            with ui.row().classes("w-full items-center mt-2 justify-between"):
                 ui.button("Add URL", icon="add", on_click=lambda: add_url_row())
                 ui.button("Test Notification", on_click=lambda: NutAlertNotifier(state.config).notify_apprise("Test Notification", "This is a test notification from nutalert."), icon="notification_important", color=COLOR_THEME["button_color"])

        with ui.row().classes("w-full justify-start items-center gap-x-4 pt-4"):
            def save_settings():
                try:
                    AppConfig.model_validate(state.config)
                    save_status = save_config(state.config)
                    ui.notify(save_status, color="positive" if "successfully" in save_status else "negative")
                except ValidationError as e:
                    ui.notify(f"Configuration Error: {e}", color="negative", multi_line=True, wrap=True)
                except Exception as e:
                    ui.notify(f"An unexpected error occurred: {e}", color="negative")
            
            ui.button("Save Settings", on_click=save_settings, icon="save", color=COLOR_THEME["button_color"])
