import asyncio
import yaml
from typing import Dict, Any, Optional

import plotly.graph_objects as go
from nicegui import ui, run, app

from nutalert.processor import get_ups_data_and_alerts
from nutalert.utils import load_config, save_config


def create_dial_gauge(value: float, title: str, metric_type: str, range_min: float, range_max: float) -> go.Figure:
    bar_color = "#1565C0"
    if metric_type == "load":
        steps = [
            {"range": [0, 70], "color": "#4CAF50"},
            {"range": [70, 90], "color": "#FFC107"},
            {"range": [90, 100], "color": "#F44336"},
        ]
        bar_color = "#B71C1C" if value > 90 else "#FBC02D" if value > 70 else "#2E7D32"
    elif metric_type == "charge":
        steps = [
            {"range": [0, 20], "color": "#F44336"},
            {"range": [20, 50], "color": "#FFC107"},
            {"range": [50, 100], "color": "#4CAF50"},
        ]
        bar_color = "#B71C1C" if value < 20 else "#FBC02D" if value < 50 else "#2E7D32"
    elif metric_type == "runtime":
        value_mins = value / 60.0
        range_max_mins = max(30, value_mins * 1.2)
        steps = [
            {"range": [0, 5], "color": "#F44336"},
            {"range": [5, 15], "color": "#FFC107"},
            {"range": [15, range_max_mins], "color": "#4CAF50"},
        ]
        bar_color = "#B71C1C" if value_mins < 5 else "#FBC02D" if value_mins < 15 else "#2E7D32"
        value, range_min, range_max = value_mins, 0, range_max_mins
    elif metric_type == "voltage":
        safe_low, safe_high, warn_low, warn_high = (210, 245, 200, 255) if value > 180 else (110, 128, 105, 130)
        steps = [
            {"range": [range_min, warn_low], "color": "#F44336"},
            {"range": [warn_low, safe_low], "color": "#FFC107"},
            {"range": [safe_low, safe_high], "color": "#4CAF50"},
            {"range": [safe_high, warn_high], "color": "#FFC107"},
            {"range": [warn_high, range_max], "color": "#F44336"},
        ]
        bar_color = (
            "#2E7D32"
            if safe_low <= value <= safe_high
            else "#FBC02D" if warn_low <= value < safe_low or safe_high < value <= warn_high else "#B71C1C"
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
        height=200, margin=dict(l=30, r=30, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
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
            print(f"Error in data retrieval/update loop: {e}")
            self.alert_message = f"Error: {e}"
            self.is_alerting = True
            self.update_ui_components()

    def update_ui_components(self):
        if "status_dot" in self.ui_elements:
            dot = self.ui_elements["status_dot"]
            status = self.nut_values.get("ups.status", "unknown").lower()
            if "ol" in status:
                color = "mediumseagreen"
            elif "ob" in status:
                color = "darkorange"
            else:
                color = "crimson"
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
                alert_card.classes(remove="bg-green-100 text-green-800", add="bg-red-100 text-red-800")
                alert_icon.props("name=priority_high")
            else:
                alert_card.classes(remove="bg-red-100 text-red-800", add="bg-green-100 text-green-800")
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

        if "log_view" in self.ui_elements:
            log_element = self.ui_elements["log_view"]
            log_element.clear()
            for line in self.logs.splitlines():
                log_element.push(line)


state = AppState()


def build_header():
    with ui.header(elevated=True).classes("justify-between items-center px-4 py-2 bg-gray-800 text-white"):
        ui.label("⚡ NUT Alert Dashboard").classes("text-2xl font-bold")
        with ui.row().classes("items-center"):
            state.ui_elements["status_label"] = ui.label("Initializing...")
            state.ui_elements["status_dot"] = ui.element("div").classes(
                "w-4 h-4 rounded-full ml-2 transition-colors duration-500"
            )


def build_alert_banner():
    with ui.card().classes("w-full p-3 transition-all") as card:
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


def build_config_editor():
    with ui.card().classes("w-full"):
        ui.label("Configuration").classes("text-lg font-semibold")
        ui.codemirror(
            value=state.config_text, language="yaml", on_change=lambda e: setattr(state, "config_text", e.value)
        ).props("line-numbers").classes("w-full border").style("height: 60vh")

        def save_and_apply():
            try:
                new_config = yaml.safe_load(state.config_text)
                save_status = save_config(new_config)
                state.config = new_config
                ui.notify(save_status, color="positive" if "successfully" in save_status else "negative")
            except yaml.YAMLError as e:
                ui.notify(f"YAML Parsing Error: {e}", color="negative")
            except Exception as e:
                ui.notify(f"Failed to apply configuration: {e}", color="negative")

        ui.button("Save Configuration", on_click=save_and_apply, icon="save").classes("mt-4")


def build_log_viewer():
    with ui.card().classes("w-full"):
        ui.label("Live Logs").classes("text-lg font-semibold")
        state.ui_elements["log_view"] = (
            ui.log(max_lines=1000).classes("w-full bg-gray-100 font-mono text-sm").style("height: 40vh")
        )


@ui.page("/", title="NUT Alert Dashboard")
async def dashboard_page():
    build_header()
    with ui.element("div").classes("w-full p-4 space-y-4"):
        build_alert_banner()
        with ui.tabs().classes("w-full") as tabs:
            ui.tab("Dashboard")
            ui.tab("Configuration")

        with ui.tab_panels(tabs, value="Dashboard").classes("w-full mt-4"):
            with ui.tab_panel("Dashboard"):
                with ui.column().classes("w-full gap-y-4"):
                    build_dashboard_gauges()
                    build_log_viewer()

            with ui.tab_panel("Configuration"):
                build_config_editor()

    await state.update_data_and_ui()


app.on_startup(lambda: asyncio.create_task(update_loop()))


async def update_loop():
    while True:
        try:
            await asyncio.sleep(state.config.get("check_interval", 15))
            await state.update_data_and_ui()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"CRITICAL ERROR in background update loop: {e}")
            await asyncio.sleep(30)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="NUT Alert Dashboard")
