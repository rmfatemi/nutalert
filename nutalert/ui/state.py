import yaml
import asyncio

from nicegui import ui, run
from typing import Dict, Any

from nutalert.utils import setup_logger
from nutalert.config import load_config
from nutalert.ui.dashboard import create_dial_gauge
from nutalert.processor import get_ups_data_and_alerts


logger = setup_logger(__name__)


class AppState:
    def __init__(self):
        self.config = load_config()
        self.config_text = yaml.dump(self.config, sort_keys=False, indent=2)
        self.nut_values: Dict[str, Dict[str, Any]] = {}
        self.ups_names: list[str] = list(self.config.get("ups_devices", {}).keys())
        self.ups_status: Dict[str, str] = {name: "waiting" for name in self.ups_names}
        self.selected_ups: str = self.ups_names[0] if self.ups_names else ""
        self.alert_message: str = "Awaiting first data poll..."
        self.is_alerting: bool = False
        self.logs: str = "Initializing log view..."
        self.current_page: str = "dashboard"
        self._initial_load_done: bool = False
        self._selector_refresh_callback = None
        self._rebuild_tabs_callback = None

    async def poll_ups_data(self):
        while True:
            try:
                result = await run.io_bound(get_ups_data_and_alerts, self.config)
                if result:
                    nut_values, all_alerts, is_alerting, new_logs = result
                    self.nut_values = nut_values or self.nut_values
                    new_status = {}
                    for ups_name in self.config.get("ups_devices", {}):
                        if ups_name in all_alerts:
                            _, ups_is_alerting = all_alerts[ups_name]
                            new_status[ups_name] = "error" if ups_is_alerting else "ok"
                        elif ups_name in nut_values:
                            new_status[ups_name] = "ok"
                        else:
                            new_status[ups_name] = self.ups_status.get(ups_name, "waiting")
                    self.ups_status = new_status
                    self.ups_names = list(self.config.get("ups_devices", {}).keys())
                    if not self.selected_ups or self.selected_ups not in self.ups_names:
                        self.selected_ups = self.ups_names[0] if self.ups_names else ""
                    self.alert_message = str(all_alerts)
                    self.is_alerting = is_alerting
                    self.logs = new_logs or self.logs
                    
                    if not self._initial_load_done and self.ups_names:
                        self._initial_load_done = True
                        if self._selector_refresh_callback:
                            self._selector_refresh_callback()
                        if hasattr(self, '_rebuild_tabs_callback') and self._rebuild_tabs_callback:
                            self._rebuild_tabs_callback()
            except Exception as e:
                logger.error(f"Error in background polling task: {e}")
                self.alert_message = f"Error: {e}"
                self.is_alerting = True

            await asyncio.sleep(self.config.get("check_interval", 15))

    def update_ui_components(self, ui_elements: Dict[str, Any]):
        try:
            ups = self.selected_ups
            ups_values = self.nut_values.get(ups, {}) if ups else {}
            gs = self.config.get("ups_devices", {}).get(ups, {}).get("gauge_settings", {})

            def safe_get(d, key, default):
                v = d.get(key, default)
                return default if v is None else v

            load_warn = safe_get(gs.get("load", {}), "warn_threshold", 80)
            load_high = safe_get(gs.get("load", {}), "high_threshold", 100)
            charge_warn = safe_get(gs.get("charge_remaining", {}), "warn_threshold", 35)
            charge_high = safe_get(gs.get("charge_remaining", {}), "high_threshold", 15)
            runtime_warn = safe_get(gs.get("runtime", {}), "warn_threshold", 15)
            runtime_high = safe_get(gs.get("runtime", {}), "high_threshold", 10)
            voltage_nominal = safe_get(gs.get("voltage", {}), "nominal", 120)
            voltage_warn = safe_get(gs.get("voltage", {}), "warn_deviation", 10)
            voltage_high = safe_get(gs.get("voltage", {}), "high_deviation", 15)

            if "load_plot" in ui_elements:
                ui_elements["load_plot"].figure = create_dial_gauge(
                    float(ups_values.get("ups.load", 0.0)),
                    "UPS Load (%)",
                    "load",
                    0,
                    load_high,
                    self.config,
                    warn=load_warn,
                    high=load_high,
                )
                ui_elements["load_plot"].update()
            if "charge_plot" in ui_elements:
                ui_elements["charge_plot"].figure = create_dial_gauge(
                    float(ups_values.get("battery.charge", 0.0)),
                    "Battery Charge (%)",
                    "charge",
                    0,
                    100,
                    self.config,
                    warn=charge_warn,
                    high=charge_high,
                )
                ui_elements["charge_plot"].update()
            if "runtime_plot" in ui_elements:
                runtime_seconds = float(ups_values.get("battery.runtime", 0.0))
                runtime_minutes = runtime_seconds / 60 if runtime_seconds else 0.0
                runtime_range_max = max(180, runtime_warn * 2)
                ui_elements["runtime_plot"].figure = create_dial_gauge(
                    runtime_minutes,
                    "Runtime (min)",
                    "runtime",
                    0,
                    runtime_range_max,
                    self.config,
                    warn=runtime_warn,
                    high=runtime_high,
                )
                ui_elements["runtime_plot"].update()
            if "voltage_plot" in ui_elements:
                voltage = float(ups_values.get("input.voltage", 0.0))
                ui_elements["voltage_plot"].figure = create_dial_gauge(
                    voltage,
                    "Input Voltage (V)",
                    "voltage",
                    voltage_nominal - voltage_high,
                    voltage_nominal + voltage_high,
                    self.config,
                    nominal=voltage_nominal,
                    warn=voltage_warn,
                    high=voltage_high,
                )
                ui_elements["voltage_plot"].update()

            if "raw_data_grid" in ui_elements:
                grid = ui_elements["raw_data_grid"]
                grid.clear()
                with grid:
                    if ups_values:
                        for idx, (key, value) in enumerate(sorted(ups_values.items())):
                            with ui.row().classes(f"w-full items-center justify-between px-4"):
                                ui.label(f"{key}:").classes("font-mono text-sm font-bold")
                                ui.label(str(value)).classes("font-mono text-sm")

            if "log_view" in ui_elements:
                log_element = ui_elements["log_view"]
                log_element.clear()
                for line in self.logs.splitlines():
                    log_element.push(line)
            
            if "header_status_card" in ui_elements and "header_status_icon" in ui_elements and "header_status_label" in ui_elements:
                from nutalert.ui.header import get_overall_status
                _, status_icon, status_color, status_label, status_bg = get_overall_status(self)

                ui_elements["header_status_card"].style(f"background:{status_bg};")
                ui_elements["header_status_icon"].props(f"name={status_icon}").style(f"color: {status_color}")
                ui_elements["header_status_label"].set_text(status_label)
            
            if "ups_tabs" in ui_elements:
                ui_elements["ups_tabs"].set_value(self.selected_ups)
        
        except RuntimeError as e:
            if "has been deleted" not in str(e):
                logger.error(f"Error updating UI components: {e}")
