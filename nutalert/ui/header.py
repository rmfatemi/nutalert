from typing import Dict, Any
from nicegui import ui
from nutalert.ui.theme import COLOR_THEME


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
