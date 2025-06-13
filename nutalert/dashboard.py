import yaml
import asyncio

from typing import Dict, Any, Optional, List

from nicegui import ui, run, app
import plotly.graph_objects as go
from pydantic import BaseModel, Field, ValidationError

from nutalert.utils import setup_logger
from nutalert.utils import load_config, save_config
from nutalert.processor import get_ups_data_and_alerts


logger = setup_logger(__name__)


# Color constants for dark mode theme
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
    "success_text": "#66BB6A",
    "error_text": "#EF5350",
    "log_bg": "#212121",
    "codemirror_theme": "dracula",
}


class MinMaxAlert(BaseModel):
    enabled: bool = False
    min: Optional[int] = None
    max: Optional[int] = None
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
    port: int = Field(gt=0, le=65535, description="Port must be between 1 and 65535")
    timeout: int = Field(gt=0, description="Timeout must be a positive number")


class FormulaAlert(BaseModel):
    expression: str
    message: str


class AppConfig(BaseModel):
    nut_server: NutServerConfig
    check_interval: int = Field(ge=5, description="check_interval must be 5 seconds or greater")
    alert_mode: str
    basic_alerts: Optional[BasicAlerts] = None
    formula_alert: Optional[FormulaAlert] = None


def create_dial_gauge(value: float, title: str, metric_type: str, range_min: float, range_max: float) -> go.Figure:
    bar_color = COLOR_THEME["primary"]
    if metric_type == "load":
        steps = [
            {"range": [0, 70], "color": COLOR_THEME["success"]},
            {"range": [70, 90], "color": COLOR_THEME["warning"]},
            {"range": [90, 100], "color": COLOR_THEME["error"]},
        ]
        bar_color = (
            COLOR_THEME["error"] if value > 90 else COLOR_THEME["warning"] if value > 70 else COLOR_THEME["success"]
        )
    elif metric_type == "charge":
        steps = [
            {"range": [0, 20], "color": COLOR_THEME["error"]},
            {"range": [20, 50], "color": COLOR_THEME["warning"]},
            {"range": [50, 100], "color": COLOR_THEME["success"]},
        ]
        bar_color = (
            COLOR_THEME["error"] if value < 20 else COLOR_THEME["warning"] if value < 50 else COLOR_THEME["success"]
        )
    elif metric_type == "runtime":
        value_mins = value / 60.0
        range_max_mins = max(30, value_mins * 1.2)
        steps = [
            {"range": [0, 5], "color": COLOR_THEME["error"]},
            {"range": [5, 15], "color": COLOR_THEME["warning"]},
            {"range": [15, range_max_mins], "color": COLOR_THEME["success"]},
        ]
        bar_color = (
            COLOR_THEME["error"]
            if value_mins < 5
            else COLOR_THEME["warning"] if value_mins < 15 else COLOR_THEME["success"]
        )
        value, range_min, range_max = value_mins, 0, range_max_mins
    elif metric_type == "voltage":
        safe_low, safe_high, warn_low, warn_high = (210, 245, 200, 255) if value > 180 else (110, 128, 105, 130)
        steps = [
            {"range": [range_min, warn_low], "color": COLOR_THEME["error"]},
            {"range": [warn_low, safe_low], "color": COLOR_THEME["warning"]},
            {"range": [safe_low, safe_high], "color": COLOR_THEME["success"]},
            {"range": [safe_high, warn_high], "color": COLOR_THEME["warning"]},
            {"range": [warn_high, range_max], "color": COLOR_THEME["error"]},
        ]
        bar_color = (
            COLOR_THEME["success"]
            if safe_low <= value <= safe_high
            else COLOR_THEME["warning"]
            if warn_low <= value < safe_low or safe_high < value <= warn_high
            else COLOR_THEME["error"]
        )

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
        self.config_text = yaml.dump(self.config, sort_keys=False, indent=2)
        self.nut_values: Dict[str, Any] = {"ups.status": "INITIALIZING"}
        self.alert_message: str = "Awaiting first data poll..."
        self.is_alerting: bool = False
        self.logs: str = "Initializing log view..."
        self.ui_elements: Dict[str, Any] = {}
        self.last_alert_state: Optional[bool] = None

    async def update_data_and_ui(self):
        try:
            result = await run.io_bound(get_ups_data_and_alerts)
            if result is None:
                return

            nut_values, alert_message, is_alerting, new_logs = result

            self.nut_values = nut_values or {}
            self.alert_message = alert_message
            self.is_alerting = is_alerting
            self.logs = new_logs or self.logs

            self.update_ui_components()

        except Exception as e:
            logger.error(f"error in data retrieval/update loop: {e}")
            self.alert_message = f"Error: {e}"
            self.is_alerting = True
            self.update_ui_components()

    def update_ui_components(self):
        if "status_dot" in self.ui_elements:
            dot = self.ui_elements["status_dot"]
            status = self.nut_values.get("ups.status", "unknown").lower()
            color = COLOR_THEME["error"]
            if "ol" in status:
                color = COLOR_THEME["success"]
            elif "ob" in status:
                color = COLOR_THEME["warning"]
            dot.style(f"background-color: {color}")
            dot.update()

        if "status_label" in self.ui_elements:
            label = self.ui_elements["status_label"]
            label.set_text(f"Status: {self.nut_values.get('ups.status', 'UNKNOWN').upper()}")
            label.update()

        if self.last_alert_state != self.is_alerting and "alert_card" in self.ui_elements:
            alert_card = self.ui_elements["alert_card"]
            alert_icon = self.ui_elements["alert_icon"]
            if self.is_alerting:
                alert_card.classes(
                    remove=f"bg-[{COLOR_THEME['success_bg']}] text-[{COLOR_THEME['success_text']}]",
                    add=f"bg-[{COLOR_THEME['error_bg']}] text-[{COLOR_THEME['error_text']}]",
                )
                alert_icon.props("name=priority_high")
            else:
                alert_card.classes(
                    remove=f"bg-[{COLOR_THEME['error_bg']}] text-[{COLOR_THEME['error_text']}]",
                    add=f"bg-[{COLOR_THEME['success_bg']}] text-[{COLOR_THEME['success_text']}]",
                )
                alert_icon.props("name=check_circle")
            self.last_alert_state = self.is_alerting

        if "alert_label" in self.ui_elements:
            self.ui_elements["alert_label"].set_text(self.alert_message)

        if "load_plot" in self.ui_elements:
            plot = self.ui_elements["load_plot"]
            plot.figure = create_dial_gauge(float(self.nut_values.get("ups.load", 0.0)), "UPS Load (%)", "load", 0, 100)
            plot.update()

        if "charge_plot" in self.ui_elements:
            plot = self.ui_elements["charge_plot"]
            plot.figure = create_dial_gauge(
                float(self.nut_values.get("battery.charge", 0.0)), "Battery Charge (%)", "charge", 0, 100
            )
            plot.update()

        if "runtime_plot" in self.ui_elements:
            plot = self.ui_elements["runtime_plot"]
            plot.figure = create_dial_gauge(
                float(self.nut_values.get("battery.runtime", 0.0)), "Runtime (min)", "runtime", 0, 0
            )
            plot.update()

        if "voltage_plot" in self.ui_elements:
            plot = self.ui_elements["voltage_plot"]
            voltage = float(self.nut_values.get("input.voltage", 0.0))
            plot.figure = create_dial_gauge(voltage, "Input Voltage (V)", "voltage", 0, 260 if voltage > 180 else 150)
            plot.update()

        if "raw_data_grid" in self.ui_elements:
            grid = self.ui_elements["raw_data_grid"]
            grid.clear()
            with grid:
                if self.nut_values:
                    sorted_items = sorted(self.nut_values.items())
                    for key, value in sorted_items:
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.label(f"{key}:").classes("font-mono text-sm font-bold")
                            ui.label(str(value)).classes("font-mono text-sm")

        if "log_view" in self.ui_elements:
            log_element = self.ui_elements["log_view"]
            log_element.clear()
            for line in self.logs.splitlines():
                log_element.push(line)


state = AppState()


def build_header():
    with ui.header(elevated=True).classes(
        f"justify-between items-center px-4 py-2 bg-[{COLOR_THEME['secondary']}] text-[{COLOR_THEME['text']}]"
    ):
        with ui.row().classes("items-center"):
            ui.image("/assets/logo.png").classes("w-10 h-9 mr-0")
            ui.label("nutalert").classes("text-2xl font-bold")
        with ui.row().classes("items-center"):
            state.ui_elements["status_label"] = ui.label("Initializing...")
            state.ui_elements["status_dot"] = ui.element("div").classes(
                "w-4 h-4 rounded-full ml-2 transition-colors duration-500"
            )


def build_alert_banner():
    with ui.card().classes(f"w-full p-3 transition-all bg-[{COLOR_THEME['card']}]") as card:
        state.ui_elements["alert_card"] = card
        with ui.row().classes("items-center no-wrap"):
            state.ui_elements["alert_icon"] = ui.icon("check_circle")
            state.ui_elements["alert_label"] = ui.label()


def build_dashboard_gauges():
    with ui.grid().classes("grid-cols-2 md:grid-cols-4 w-full gap-4"):
        state.ui_elements["load_plot"] = ui.plotly(create_dial_gauge(0.0, "UPS Load (%)", "load", 0, 100))
        state.ui_elements["charge_plot"] = ui.plotly(create_dial_gauge(0.0, "Battery Charge (%)", "charge", 0, 100))
        state.ui_elements["runtime_plot"] = ui.plotly(create_dial_gauge(0.0, "Runtime (min)", "runtime", 0, 1800))
        state.ui_elements["voltage_plot"] = ui.plotly(create_dial_gauge(0.0, "Input Voltage (V)", "voltage", 0, 150))


def build_raw_data_display():
    with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
        ui.label("Raw UPS Data").classes("text-lg font-semibold")
        state.ui_elements["raw_data_grid"] = ui.grid().classes(
            "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-2 mt-4"
        )


def build_config_editor():
    with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
        ui.label("Configuration").classes("text-lg font-semibold")
        ui.codemirror(
            value=state.config_text, language="yaml", on_change=lambda e: setattr(state, "config_text", e.value)
        ).props(f"line-numbers theme={COLOR_THEME['codemirror_theme']}").classes("w-full border").style("height: 60vh")

        def save_and_apply():
            try:
                new_config_data = yaml.safe_.load(state.config_text)
                AppConfig.model_validate(new_config_data)
                save_status = save_config(new_config_data)
                state.config = new_config_data
                ui.notify(save_status, color="positive" if "successfully" in save_status else "negative")
            except ValidationError as e:
                ui.notify(f"Configuration Error: {e}", color="negative", multi_line=True, wrap=True)
            except yaml.YAMLError as e:
                ui.notify(f"YAML Syntax Error: {e}", color="negative", multi_line=True, wrap=True)
            except Exception as e:
                ui.notify(f"An unexpected error occurred: {e}", color="negative")

        ui.button("Save Configuration", on_click=save_and_apply, icon="save").classes("mt-4")


def build_log_viewer():
    with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
        ui.label("Live Logs").classes("text-lg font-semibold")
        state.ui_elements["log_view"] = (
            ui.log(max_lines=1000).classes(f"w-full bg-[{COLOR_THEME['log_bg']}] font-mono text-sm").style("height: 40vh")
        )


@ui.page("/", title="nutalert")
async def dashboard_page():
    ui.dark_mode(True)
    build_header()
    with ui.element("div").classes(f"w-full p-4 space-y-4 bg-[{COLOR_THEME['background']}] text-[{COLOR_THEME['text']}]"):
        build_alert_banner()
        with ui.tabs().classes("w-full") as tabs:
            ui.tab("Dashboard")
            ui.tab("Configuration")
            ui.tab("Logs")

        with ui.tab_panels(tabs, value="Dashboard").classes("w-full mt-4"):
            with ui.tab_panel("Dashboard"):
                with ui.column().classes("w-full gap-y-4"):
                    build_dashboard_gauges()
                    build_raw_data_display()

            with ui.tab_panel("Configuration"):
                build_config_editor()

            with ui.tab_panel("Logs"):
                build_log_viewer()

    await state.update_data_and_ui()


app.on_startup(lambda: asyncio.create_task(update_loop()))


async def update_loop():
    await asyncio.sleep(1)
    while True:
        try:
            await state.update_data_and_ui()
            await asyncio.sleep(state.config.get("check_interval", 15))
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"critical error in background update loop: {e}")
            await asyncio.sleep(30)


app.add_static_files("/assets", "assets")

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="nutalert")
