from typing import Dict, List, Any
from nicegui import ui
from pydantic import ValidationError

# --- Mocked imports for demonstration ---
class AppConfig:
    @staticmethod
    def model_validate(config):
        print("Model validated:", config)
        # Simulate validation pass
        pass

def save_config(config):
    print("Configuration saved:", config)
    return "Configuration saved successfully."

class NutAlertNotifier:
    def __init__(self, config):
        self.config = config
        print("Notifier initialized with config:", self.config)
    def notify_apprise(self, title, message):
        ui.notify(f"TEST NOTIFICATION: {title} - {message}")
        print(f"Attempting to send test notification: {title} - {message}")

# The user wants all buttons to have the same color.
# We'll define this color here. 'primary' is a good default theme color in NiceGUI.
UI_COLOR = 'primary'
# --- End of Mocked imports ---


class Settings:
    def __init__(self, config: Dict):
        self.config = config
        self.config.setdefault("nut_server", {"host": "localhost", "port": 3493, "timeout": 5, "check_interval": 15})
        self.config.setdefault("notifications", {"urls": [{"url": "tgram://...", "enabled": True}], "enabled": True, "cooldown": 60})
        self.config.setdefault("basic_alerts", {})
        self.config.setdefault("formula_alert", {"expression": "", "message": ""})
        self.config.setdefault("alert_mode", "basic")

    def save(self) -> None:
        try:
            AppConfig.model_validate(self.config)
            save_status = save_config(self.config)
            ui.notify(save_status, color="positive" if "successfully" in save_status else "negative")
        except ValidationError as e:
            ui.notify(f"Configuration Error: {e}", color="negative", multi_line=True, wrap=True)
        except Exception as e:
            ui.notify(f"An unexpected error occurred: {e}", color="negative")

    def test_notifications(self) -> None:
        NutAlertNotifier(self.config).notify_apprise("Test Notification", "This is a test notification from nutalert.")

def nut_server_settings(settings: Settings) -> None:
    ui.label("NUT Server").classes("text-lg font-semibold")
    with ui.row().classes("p-2 rounded-md bg-yellow-900/50 w-full items-center gap-x-2"):
        ui.icon("warning", color="amber")
        ui.label("Changes to Host, Port, or Timeout require a manual application restart.").classes("text-xs")
    with ui.grid(columns=4).classes("w-full gap-4 pt-4"):
        ui.input("Host").bind_value(settings.config["nut_server"], "host")
        ui.number("Port", min=1, max=65535, step=1).bind_value(settings.config["nut_server"], "port")
        ui.number("Timeout (s)", min=1, step=1).bind_value(settings.config["nut_server"], "timeout")
        ui.number("Check Interval (s)", min=5, step=1).bind_value(settings.config["nut_server"], "check_interval")

def alert_rules_settings(settings: Settings) -> None:
    ui.label("Alert Rules").classes("text-xl font-semibold")
    with ui.row().classes("items-center mt-2"):
        ui.label("Alert Mode:").classes("mr-4 font-semibold")
        # CHANGED: Added color to the radio toggle
        alert_mode_radio = ui.radio(["basic", "formula"], value="basic").bind_value(settings.config, "alert_mode").props(f'inline color={UI_COLOR}')
    with ui.column().classes('w-full').bind_visibility_from(alert_mode_radio, 'value', value='basic'):
        basic_alert_rules(settings.config["basic_alerts"])
    with ui.column().classes('w-full').bind_visibility_from(alert_mode_radio, 'value', value='formula'):
        formula_alert_rules(settings.config["formula_alert"])

def basic_alert_rules(basic_alerts_config: Dict) -> None:
    with ui.column().classes('w-full gap-4 mt-4'):
        basic_alert_card(basic_alerts_config, "battery_charge", "Battery Charge", True, False)
        basic_alert_card(basic_alerts_config, "runtime", "Battery Runtime", True, False)
        basic_alert_card(basic_alerts_config, "load", "UPS Load", False, True)
        basic_alert_card(basic_alerts_config, "input_voltage", "Input Voltage", True, True)
        ups_status_alert_card(basic_alerts_config)

def basic_alert_card(config: Dict, key: str, title: str, has_min: bool, has_max: bool) -> None:
    config.setdefault(key, {})
    alert_conf = config[key]
    alert_conf.setdefault("enabled", False); alert_conf.setdefault("message", "")
    alert_conf.setdefault("min", 110.0 if key == "input_voltage" else 0.0)
    alert_conf.setdefault("max", 130.0 if key == "input_voltage" else 0.0)
    
    with ui.expansion(title, icon="rule").classes("w-full border rounded-md"):
        with ui.row().classes("w-full justify-end"):
            # CHANGED: Added color to the switch toggle
            ui.switch("Enabled").bind_value(alert_conf, "enabled").props(f'color={UI_COLOR}')
        with ui.row().classes("w-full items-center"):
            if has_min and not has_max: ui.number("Minimum", format='%.1f').classes('flex-grow').bind_value(alert_conf, "min")
            if has_max and not has_min: ui.number("Maximum", format='%.1f').classes('flex-grow').bind_value(alert_conf, "max")
            if has_min and has_max:
                with ui.row().classes('w-full no-wrap'):
                    ui.number("Min", format='%.1f').bind_value(alert_conf, "min")
                    ui.number("Max", format='%.1f').bind_value(alert_conf, "max")
        ui.input("Alert Message", placeholder="Notification message...").classes('w-full pt-2').bind_value(alert_conf, "message")

def ups_status_alert_card(config: Dict) -> None:
    config.setdefault("ups_status", {"enabled": False, "acceptable": ['ol', 'online'], "message": "UPS status not in acceptable list", "alert_when_status_changed": False})
    status_conf = config["ups_status"]
    with ui.expansion("UPS Status", icon="power").classes("w-full border rounded-md"):
        with ui.row().classes("w-full justify-end"):
            # CHANGED: Added color to the switch toggle
            ui.switch("Enabled").bind_value(status_conf, "enabled").props(f'color={UI_COLOR}')
        ui.input("Acceptable Statuses", placeholder="e.g. OL, ONLINE").bind_value_from(status_conf, 'acceptable', lambda l: ', '.join(l or [])).bind_value_to(status_conf, 'acceptable', lambda s: [i.strip().lower() for i in (s or '').split(',') if i.strip()])
        ui.input("Alert Message", placeholder="Notification message...").classes('w-full').bind_value(status_conf, "message")
        # CHANGED: Added color to the switch toggle
        ui.switch("Alert on any status change").bind_value(status_conf, "alert_when_status_changed").props(f'color={UI_COLOR}')

def formula_alert_rules(formula_alert_config: Dict) -> None:
    ui.input(label="Expression", placeholder="e.g. battery_charge < 90").classes("w-full font-mono").bind_value(formula_alert_config, "expression")
    ui.input(label="Alert Message", placeholder="e.g. Load is {ups_load}%").classes("w-full").bind_value(formula_alert_config, "message")

def notification_settings(settings: Settings) -> None:
    @ui.refreshable
    def url_list() -> None:
        if not settings.config["notifications"]["urls"]:
            ui.label("No notification URLs added.").classes("text-xs text-gray-500 self-center py-4")
        for url_obj in settings.config["notifications"]["urls"]:
            with ui.row().classes("w-full items-center gap-x-2") as row:
                ui.input("URL", placeholder="e.g., tgram://...").classes("flex-grow").bind_value(url_obj, "url")
                # CHANGED: Added color to the switch toggle
                ui.switch().props(f"dense color={UI_COLOR}").bind_value(url_obj, "enabled")
                # CHANGED: Changed delete button color to match other buttons
                ui.button(icon="delete", on_click=lambda u=url_obj: (settings.config["notifications"]["urls"].remove(u), url_list.refresh())).props(f'flat dense color={UI_COLOR}')

    with ui.row().classes("w-full justify-between items-center"):
        ui.label("Notifications").classes("text-lg font-semibold")
        # CHANGED: Added color to the switch toggle
        ui.switch("Enable All").bind_value(settings.config["notifications"], "enabled").props(f'color={UI_COLOR}')
    ui.number("Cooldown (s)").bind_value(settings.config["notifications"], "cooldown")
    ui.separator().classes("my-2")
    
    url_list()

    # CHANGED: Placed "Add URL" and "Test" buttons next to each other
    with ui.row().classes("w-full items-center mt-2 gap-x-2"):
         ui.button("Add URL", icon="add", color=UI_COLOR, on_click=lambda: (settings.config["notifications"]["urls"].append({"url": "", "enabled": True}), url_list.refresh()))
         ui.button("Test Alerts", on_click=settings.test_notifications, icon="notification_important", color=UI_COLOR)


def build_settings_tab(state, ui_elements: Dict[str, Any]):
    settings = Settings(state.config)
    with ui.grid(columns=2).classes("w-full gap-4"):
        with ui.card().classes("w-full items-stretch gap-y-4"):
            ui.label("Settings").classes("text-semibold text-2xl self-center")
            
            nut_server_settings(settings)
            ui.separator()
            alert_rules_settings(settings)
            ui.separator()
            notification_settings(settings)
            ui.separator()
            
            # CHANGED: Aligned the "Save" button to the bottom-left
            with ui.row().classes("w-full justify-start pt-4"):
                ui.button("Save Settings", on_click=settings.save, icon="save", color=UI_COLOR)
        
        with ui.card().classes("w-full items-stretch gap-y-4"):
            ui.label("Live Logs").classes("text-lg font-semibold self-center")
            ui_elements["log_view"] = (
                ui.log(max_lines=1000)
                .classes("w-full font-mono text-sm")
                .style("height: 120vh")
            )
