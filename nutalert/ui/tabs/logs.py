from nicegui import ui
from typing import Any, Dict
from nutalert.ui.theme import COLOR_THEME

def build_logs_tab(state, ui_elements: Dict[str, Any]):
    with ui.card().classes("w-full flex flex-col items-stretch gap-y-4"):
        ui.label("Live Logs").classes("text-lg font-semibold self-center")
        ui_elements["log_view"] = ui.log(max_lines=1000).classes(
            f"w-full font-mono text-sm flex-grow bg-[{COLOR_THEME['card']}] p-2 rounded-md h-screen"
        )
