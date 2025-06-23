import asyncio

from nicegui import ui, run
from typing import Dict, Any

from nutalert.ui.theme import COLOR_THEME
from nutalert.utils import setup_logger, load_config
from nutalert.ui.components import create_dial_gauge
from nutalert.processor import get_ups_data_and_alerts


logger = setup_logger(__name__)


class AppState:
    def __init__(self):
        self.config = load_config()
        self.nut_values: Dict[str, Any] = {"ups.status": "INITIALIZING"}
        self.alert_message: str = "Awaiting first data poll..."
        self.is_alerting: bool = False
        self.logs: str = "Initializing log view..."

    async def poll_ups_data(self):
        while True:
            interval = 15
            try:
                self.config = load_config()
                check_interval = self.config.get("nut_server", {}).get("check_interval", 15)
                interval = max(5, check_interval)
                result = await run.io_bound(get_ups_data_and_alerts, self.config)
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
