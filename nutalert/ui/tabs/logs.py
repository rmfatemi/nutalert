from typing import Dict, Any
from nicegui import ui
from nutalert.ui.theme import COLOR_THEME

def build_logs_tab(ui_elements: Dict[str, Any]):
    with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
        ui.label("Live Logs").classes("text-lg font-semibold")
        ui_elements["log_view"] = (
            ui.log(max_lines=1000)
            .classes(f"w-full bg-[{COLOR_THEME['log_bg']}] font-mono text-sm")
            .style("height: 75vh")
        )
