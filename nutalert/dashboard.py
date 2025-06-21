import yaml
import asyncio
from typing import Dict, Any, Optional, List

from nicegui import ui, run, app, events
import plotly.graph_objects as go
from pydantic import BaseModel, Field, ValidationError

from nutalert.notifier import NutAlertNotifier
from nutalert.processor import get_ups_data_and_alerts
from nutalert.utils import setup_logger, load_config, save_config, get_config_path

logger = setup_logger(__name__)

COLOR_THEME = {
    "background": "#121212",
    "primary": "#1E88E5",
    "secondary": "#263238",
    "text": "#E0E0E0",
    "card": "#1E1E1E",
    "success": "#66BB6A",
    "warning": "#FFA726",
    "error": "#EF5350",
    "gauge_background": "rgba(0,0,0,0)",
    "success_bg": "rgba(102, 187, 106, 0.2)",
    "error_bg": "rgba(239, 83, 80, 0.2)",
    "success_banner_bg": "#66BB6A",
    "error_banner_bg": "#EF5350",
    "success_text": "#66BB6A",
    "error_text": "#EF5350",
    "log_bg": "#212121",
    "codemirror_theme": "darcula",
    "button_color": "#FF8F00",
}


class MinMaxAlert(BaseModel):
    enabled: bool = False
    min: Optional[float] = None
    max: Optional[float] = None
    message: Optional[str] = None


class StatusAlert(BaseModel):
    enabled: bool = False
    acceptable: List[str] = []
    message: Optional[str] = None
    alert_when_status_changed: bool = False


class BasicAlerts(BaseModel):
    battery_charge: Optional[MinMaxAlert] = None
    runtime: Optional[MinMaxAlert] = None
    load: Optional[MinMaxAlert] = None
    input_voltage: Optional[MinMaxAlert] = None
    ups_status: Optional[StatusAlert] = None


class NutServerConfig(BaseModel):
    host: str
    port: int = Field(gt=0, le=65535)
    timeout: int = Field(gt=0)
    check_interval: int = Field(ge=5)


class FormulaAlert(BaseModel):
    expression: str
    message: str


class NotificationsConfig(BaseModel):
    enabled: bool
    cooldown: int
    urls: List[Dict[str, Any]]


class AppConfig(BaseModel):
    nut_server: NutServerConfig
    alert_mode: str
    basic_alerts: Optional[BasicAlerts] = None
    formula_alert: Optional[FormulaAlert] = None
    notifications: Optional[NotificationsConfig] = None


def create_dial_gauge(
    value: float, title: str, metric_type: str, range_min: float, range_max: float, config: Dict[str, Any]
) -> go.Figure:
    bar_color = COLOR_THEME["primary"]
    basic_alerts = config.get("basic_alerts", {})

    if metric_type == "load":
        max_load = basic_alerts.get("load", {}).get("max", 90)
        warn_load = max_load / 2
        steps = [
            {"range": [0, warn_load], "color": COLOR_THEME["success"]},
            {"range": [warn_load, max_load], "color": COLOR_THEME["warning"]},
            {"range": [max_load, 100], "color": COLOR_THEME["error"]},
        ]
        bar_color = (
            COLOR_THEME["error"]
            if value > max_load
            else COLOR_THEME["warning"] if value > warn_load else COLOR_THEME["success"]
        )
    elif metric_type == "charge":
        min_charge = basic_alerts.get("battery_charge", {}).get("min", 20)
        warn_low = min_charge - 5
        warn_high = min_charge + 5
        steps = [
            {"range": [0, warn_low], "color": COLOR_THEME["error"]},
            {"range": [warn_low, warn_high], "color": COLOR_THEME["warning"]},
            {"range": [warn_high, 100], "color": COLOR_THEME["success"]},
        ]
        bar_color = (
            COLOR_THEME["error"]
            if value < warn_low
            else COLOR_THEME["warning"] if value < warn_high else COLOR_THEME["success"]
        )
    elif metric_type == "runtime":
        value_mins = value / 60.0
        min_runtime = basic_alerts.get("runtime", {}).get("min", 5)
        range_max_mins = max(30, value_mins * 1.2)
        warn_runtime = min_runtime + (range_max_mins - min_runtime) / 2
        steps = [
            {"range": [0, min_runtime], "color": COLOR_THEME["error"]},
            {"range": [min_runtime, warn_runtime], "color": COLOR_THEME["warning"]},
            {"range": [warn_runtime, range_max_mins], "color": COLOR_THEME["success"]},
        ]
        bar_color = (
            COLOR_THEME["error"]
            if value_mins < min_runtime
            else COLOR_THEME["warning"] if value_mins < warn_runtime else COLOR_THEME["success"]
        )
        value, range_min, range_max = value_mins, 0, range_max_mins
    elif metric_type == "voltage":
        voltage_config = basic_alerts.get("input_voltage", {})
        min_voltage = voltage_config.get("min", 110.0)
        max_voltage = voltage_config.get("max", 130.0)
        display_max = max_voltage + 20
        warn_low = min_voltage - 5
        warn_high = max_voltage + 5
        steps = [
            {"range": [0, warn_low], "color": COLOR_THEME["error"]},
            {"range": [warn_low, min_voltage], "color": COLOR_THEME["warning"]},
            {"range": [min_voltage, max_voltage], "color": COLOR_THEME["success"]},
            {"range": [max_voltage, warn_high], "color": COLOR_THEME["warning"]},
            {"range": [warn_high, display_max], "color": COLOR_THEME["error"]},
        ]
        bar_color = (
            COLOR_THEME["success"]
            if min_voltage <= value <= max_voltage
            else (
                COLOR_THEME["warning"]
                if warn_low <= value < min_voltage or max_voltage < value <= warn_high
                else COLOR_THEME["error"]
            )
        )
        range_max = display_max

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=round(float(value), 1),
            title={"text": title, "font": {"size": 16}},
            gauge={"axis": {"range": [range_min, range_max]}, "bar": {"color": bar_color}, "steps": steps},
        )
    )
    fig.update_layout(
        height=200,
        margin=dict(l=30, r=30, t=50, b=20),
        paper_bgcolor=COLOR_THEME["gauge_background"],
        plot_bgcolor=COLOR_THEME["gauge_background"],
        font={"color": COLOR_THEME["text"]},
    )
    return fig


class AppState:
    def __init__(self):
        self.config = load_config()
        self.nut_values: Dict[str, Any] = {"ups.status": "INITIALIZING"}
        self.alert_message: str = "Awaiting first data poll..."
        self.is_alerting: bool = False
        self.logs: str = "Initializing log view..."

    async def poll_ups_data(self):
        while True:
            try:
                interval = max(5, self.config.get("nut_server", {}).get("check_interval", 15))
                result = await run.io_bound(get_ups_data_and_alerts)
                if result:
                    nut_values, alert_message, is_alerting, new_logs = result
                    self.nut_values = nut_values or self.nut_values
                    self.alert_message = alert_message
                    self.is_alerting = is_alerting
                    self.logs = new_logs or self.logs
            except Exception as e:
                logger.error(f"Error in background polling task: {e}")
                self.alert_message = f"Error: {e}"
                self.is_alerting = True
            await asyncio.sleep(interval)

    def update_ui_components(self, ui_elements: Dict[str, Any]):
        if "header_status_card" in ui_elements:
            header_status_card = ui_elements["header_status_card"]
            header_status_icon = ui_elements["header_status_icon"]
            header_status_label = ui_elements["header_status_label"]
            if self.is_alerting:
                header_status_card.classes(
                    remove=f"bg-[{COLOR_THEME['success_banner_bg']}]",
                    add=f"bg-[{COLOR_THEME['error_banner_bg']}] text-[{COLOR_THEME['text']}]",
                )
                header_status_icon.props("name=error")
                header_status_label.set_text(self.alert_message)
            else:
                header_status_card.classes(
                    remove=f"bg-[{COLOR_THEME['error_banner_bg']}]",
                    add=f"bg-[{COLOR_THEME['success_banner_bg']}] text-[{COLOR_THEME['text']}]",
                )
                header_status_icon.props("name=check_circle")
                header_status_label.set_text(f"Status: {self.nut_values.get('ups.status', 'UNKNOWN').upper()}")
            header_status_card.update()
            header_status_icon.update()
            header_status_label.update()
        if "load_plot" in ui_elements:
            ui_elements["load_plot"].figure = create_dial_gauge(
                float(self.nut_values.get("ups.load", 0.0)), "UPS Load (%)", "load", 0, 100, self.config
            )
            ui_elements["load_plot"].update()
        if "charge_plot" in ui_elements:
            ui_elements["charge_plot"].figure = create_dial_gauge(
                float(self.nut_values.get("battery.charge", 0.0)), "Battery Charge (%)", "charge", 0, 100, self.config
            )
            ui_elements["charge_plot"].update()
        if "runtime_plot" in ui_elements:
            ui_elements["runtime_plot"].figure = create_dial_gauge(
                float(self.nut_values.get("battery.runtime", 0.0)), "Runtime (min)", "runtime", 0, 0, self.config
            )
            ui_elements["runtime_plot"].update()
        if "voltage_plot" in ui_elements:
            voltage = float(self.nut_values.get("input.voltage", 0.0))
            ui_elements["voltage_plot"].figure = create_dial_gauge(
                voltage, "Input Voltage (V)", "voltage", 0, 260 if voltage > 180 else 150, self.config
            )
            ui_elements["voltage_plot"].update()
        if "raw_data_grid" in ui_elements:
            grid = ui_elements["raw_data_grid"]
            grid.clear()
            with grid:
                if self.nut_values:
                    for key, value in sorted(self.nut_values.items()):
                        with ui.row().classes("w-full items-center justify-between pr-10"):
                            ui.label(f"{key}:").classes("font-mono text-sm font-bold")
                            ui.label(str(value)).classes("font-mono text-sm")
        if "log_view" in ui_elements:
            log_element = ui_elements["log_view"]
            log_element.clear()
            for line in self.logs.splitlines():
                log_element.push(line)


state = AppState()


def build_header(ui_elements: Dict[str, Any]):
    with ui.header(elevated=True).classes(
        f"justify-between items-center px-4 py-2 bg-[{COLOR_THEME['log_bg']}] text-[{COLOR_THEME['text']}]"
    ):
        with ui.row().classes("items-center"):
            ui.image("/assets/logo.svg").classes("w-10 h-9 mr-0 no-darkreader")
            ui.label("nutalert").classes("text-2xl font-bold")
        with ui.row().classes("items-center"):
            with ui.card().classes("p-2 transition-all") as card:
                ui_elements["header_status_card"] = card
                with ui.row().classes("items-center no-wrap gap-x-2"):
                    ui_elements["header_status_icon"] = ui.icon("check_circle").classes("text-lg")
                    ui_elements["header_status_label"] = ui.label("Initializing...")


def build_dashboard_gauges(ui_elements: Dict[str, Any]):
    with ui.grid().classes("grid-cols-2 md:grid-cols-4 w-full gap-4"):
        ui_elements["load_plot"] = ui.plotly(create_dial_gauge(0.0, "UPS Load (%)", "load", 0, 100, state.config))
        ui_elements["charge_plot"] = ui.plotly(
            create_dial_gauge(0.0, "Battery Charge (%)", "charge", 0, 100, state.config)
        )
        ui_elements["runtime_plot"] = ui.plotly(
            create_dial_gauge(0.0, "Runtime (min)", "runtime", 0, 1800, state.config)
        )
        ui_elements["voltage_plot"] = ui.plotly(
            create_dial_gauge(0.0, "Input Voltage (V)", "voltage", 0, 150, state.config)
        )


def build_raw_data_display(ui_elements: Dict[str, Any]):
    with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
        ui.label("UPS Data").classes("text-lg font-semibold")
        ui_elements["raw_data_grid"] = ui.grid().classes(
            "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-2 mt-4 divide-x divide-gray-700"
        )


def build_settings_page():
    state.config.setdefault("nut_server", {})
    state.config["nut_server"].setdefault("host", "localhost")
    state.config["nut_server"].setdefault("port", 3493)
    state.config["nut_server"].setdefault("timeout", 5)
    state.config["nut_server"].setdefault("check_interval", 15)
    state.config.setdefault("notifications", {"urls": []})
    state.config["notifications"].setdefault("enabled", False)
    state.config["notifications"].setdefault("cooldown", 60)
    state.config.setdefault("basic_alerts", {})
    state.config.setdefault("formula_alert", {})
    state.config["formula_alert"].setdefault("expression", "")
    state.config["formula_alert"].setdefault("message", "")

    with ui.column().classes("w-full gap-y-6"):
        with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
            ui.label("NUT Server").classes("text-lg font-semibold")
            ui.label("Settings for connecting to the Network UPS Tools (NUT) server.").classes("text-xs text-gray-400 mb-2")
            with ui.grid(columns=4).classes("w-full gap-x-8"):
                ui.input("Host").bind_value(state.config["nut_server"], "host")
                ui.number("Port", min=1, max=65535, step=1).bind_value(state.config["nut_server"], "port")
                ui.number("Timeout (s)", min=1, step=1).bind_value(state.config["nut_server"], "timeout")
                ui.number("Check Interval (s)", min=5, step=1).bind_value(state.config["nut_server"], "check_interval")

        with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Alert Rules").classes("text-xl font-semibold")
                alert_mode_select = ui.select(["basic", "formula"], label="Alert Mode").bind_value(state.config, "alert_mode")
            ui.separator().classes("my-2")

            with ui.column().classes('w-full').bind_visibility_from(alert_mode_select, 'value', value='basic'):
                with ui.grid(columns=2).classes('w-full gap-4'):
                    def build_basic_alert_card(key: str, title: str, guide: str, has_min: bool, has_max: bool):
                        state.config["basic_alerts"].setdefault(key, {})
                        alert_conf = state.config["basic_alerts"][key]
                        alert_conf.setdefault("enabled", False)
                        alert_conf.setdefault("min", 110.0 if key == "input_voltage" else 0.0)
                        alert_conf.setdefault("max", 130.0 if key == "input_voltage" else 0.0)
                        alert_conf.setdefault("message", "")
                        with ui.card().classes('w-full'):
                            with ui.row().classes("w-full justify-between"):
                                ui.label(title).classes("text-lg font-semibold")
                                ui.switch().bind_value(alert_conf, "enabled")
                            ui.label(guide).classes("text-xs text-gray-400 -mt-2 mb-2")
                            if has_min and not has_max:
                                ui.number("Minimum", format='%.1f').classes('w-full').bind_value(alert_conf, "min")
                            if has_max and not has_min:
                                ui.number("Maximum", format='%.1f').classes('w-full').bind_value(alert_conf, "max")
                            if has_min and has_max:
                                with ui.row().classes('w-full'):
                                    ui.number("Min", format='%.1f').bind_value(alert_conf, "min")
                                    ui.number("Max", format='%.1f').bind_value(alert_conf, "max")
                            ui.input("Alert Message", placeholder="Notification message...").classes('w-full').bind_value(alert_conf, "message")
                    
                    build_basic_alert_card("battery_charge", "Battery Charge", "Alert when charge (%) is below a value.", True, False)
                    build_basic_alert_card("runtime", "Battery Runtime", "Alert when runtime (minutes) is below a value.", True, False)
                    build_basic_alert_card("load", "UPS Load", "Alert when load (%) is above a value.", False, True)
                    build_basic_alert_card("input_voltage", "Input Voltage", "Alert when voltage is outside a range.", True, True)

                    state.config["basic_alerts"].setdefault("ups_status", {})
                    status_conf = state.config["basic_alerts"]["ups_status"]
                    status_conf.setdefault("enabled", False)
                    status_conf.setdefault("acceptable", ['ol', 'online'])
                    status_conf.setdefault("message", "UPS status not in acceptable list")
                    status_conf.setdefault("alert_when_status_changed", False)
                    with ui.card().classes('w-full'):
                        with ui.row().classes("w-full justify-between"):
                            ui.label("UPS Status").classes("text-lg font-semibold")
                            ui.switch().bind_value(status_conf, "enabled")
                        ui.label("Alert when the UPS status is not 'normal'.").classes("text-xs text-gray-400 -mt-2 mb-2")
                        acceptable_input = ui.input("Acceptable Statuses", placeholder="e.g. OL, ONLINE")
                        acceptable_input.bind_value_from(status_conf, 'acceptable', lambda l: ', '.join(l or []))
                        acceptable_input.bind_value_to(status_conf, 'acceptable', lambda s: [item.strip().lower() for item in (s or '').split(',') if item.strip()])
                        ui.input("Alert Message", placeholder="Notification message...").classes('w-full').bind_value(status_conf, "message")
                        ui.switch("Alert on any status change").bind_value(status_conf, "alert_when_status_changed")

            with ui.column().classes('w-full').bind_visibility_from(alert_mode_select, 'value', value='formula'):
                formula_conf = state.config["formula_alert"]
                ui.input(label="Expression", placeholder="e.g. battery_charge < 90").classes("w-full font-mono").bind_value(formula_conf, "expression")
                ui.label("A Python expression that evaluates to True to trigger the alert. Available variables: `ups_load`, `battery_charge`, etc.").classes("text-xs text-gray-400 -mt-2")
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
            ui.button("Add URL", icon="add", on_click=lambda: add_url_row()).classes("mt-2")
        
        with ui.row().classes("w-full justify-start items-center gap-x-4 pt-4"):
            def save_and_apply():
                try:
                    AppConfig.model_validate(state.config); save_status = save_config(state.config)
                    ui.notify(save_status, color="positive" if "successfully" in save_status else "negative")
                    ui.notify("Restarting server to apply changes...", color="warning"); app.shutdown()
                except ValidationError as e: ui.notify(f"Configuration Error: {e}", color="negative", multi_line=True, wrap=True)
                except Exception as e: ui.notify(f"An unexpected error occurred: {e}", color="negative")
            
            async def handle_upload(e: events.UploadEventArguments):
                try:
                    content = e.content.read().decode('utf-8')
                    new_config = yaml.safe_load(content)
                    AppConfig.model_validate(new_config)
                    save_config(new_config)
                    ui.notify('Configuration uploaded successfully! Reloading page.', color='positive')
                    await asyncio.sleep(1)
                    ui.navigate.reload()
                except yaml.YAMLError as err: ui.notify(f"Invalid YAML file: {err}", color='negative', multi_line=True)
                except ValidationError as err: ui.notify(f"Invalid Configuration: {err}", color='negative', multi_line=True)
                except Exception as err: ui.notify(f"An unexpected error occurred during upload: {err}", color='negative')

            ui.button("Save & Apply", on_click=save_and_apply, icon="save", color=COLOR_THEME["button_color"])
            
            # Hidden uploader element
            uploader = ui.upload(on_upload=handle_upload, auto_upload=True).style('display: none')
            # Visible button that triggers the hidden uploader by calling its 'pickFiles' JavaScript method
            ui.button("Upload Config", on_click=lambda: uploader.run_method('pickFiles'), icon="upload", color=COLOR_THEME["button_color"])

            ui.button("Download Config", on_click=lambda: ui.download(get_config_path()), icon="download", color=COLOR_THEME["button_color"])
            ui.button("Test Notification", on_click=lambda: NutAlertNotifier(state.config).notify_apprise("Test Notification", "This is a test notification from nutalert."), icon="notification_important", color=COLOR_THEME["button_color"])

def build_log_viewer(ui_elements: Dict[str, Any]):
    with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
        ui.label("Live Logs").classes("text-lg font-semibold")
        ui_elements["log_view"] = (
            ui.log(max_lines=1000)
            .classes(f"w-full bg-[{COLOR_THEME['log_bg']}] font-mono text-sm")
            .style("height: 75vh")
        )


@ui.page("/", title="nutalert")
async def dashboard_page():
    ui.dark_mode(True)
    ui_elements: Dict[str, Any] = {}
    build_header(ui_elements)
    with ui.element("div").classes(
        f"w-full p-4 space-y-4 bg-[{COLOR_THEME['background']}] text-[{COLOR_THEME['text']}]"
    ):
        with ui.tabs().classes("w-full") as tabs:
            ui.tab("Dashboard")
            ui.tab("Settings")
            ui.tab("Logs")
        with ui.tab_panels(tabs, value="Dashboard").classes("w-full mt-4"):
            with ui.tab_panel("Dashboard"):
                with ui.column().classes("w-full gap-y-4"):
                    build_dashboard_gauges(ui_elements)
                    build_raw_data_display(ui_elements)
            with ui.tab_panel("Settings"):
                build_settings_page()
            with ui.tab_panel("Logs"):
                build_log_viewer(ui_elements)
    ui.timer(interval=1, callback=lambda: state.update_ui_components(ui_elements), active=True)


app.on_startup(state.poll_ups_data)
app.add_static_files("/assets", "assets")

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="nutalert", port=8087, favicon="assets/logo.ico", reload=False)
