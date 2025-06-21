from nicegui import ui
from typing import Dict, Any
from nutalert.ui.theme import COLOR_THEME
from nutalert.ui.components import create_dial_gauge


def build_dashboard_tab(ui_elements: Dict[str, Any], state):
    with ui.column().classes("w-full gap-y-4"):
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
        
        with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
            ui.label("UPS Data").classes("text-lg font-semibold")
            ui_elements["raw_data_grid"] = ui.grid().classes(
                "w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-2 mt-4 divide-x divide-gray-700"
            )
