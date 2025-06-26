from nicegui import ui
from typing import Dict, Any

from nutalert.ui.theme import COLOR_THEME


@ui.refreshable
def ups_selector(state):
    with ui.row().classes("items-center justify-center w-full"):
        if not state.ups_names:
            ui.spinner(size="sm")
            ui.label("Waiting for UPS devices...").classes("text-gray-500")
        else:
            ui.select(
                options=state.ups_names,
                value=state.selected_ups,
                on_change=lambda e: setattr(state, "selected_ups", e.value),
            ).classes("min-w-[180px]")


def build_header(ui_elements: Dict[str, Any], state):
    with ui.header(elevated=True).classes(f"flex px-4 py-2 bg-[{COLOR_THEME['log_bg']}] text-[{COLOR_THEME['text']}]"):
        with ui.row().classes("w-full items-center"):
            with ui.row().classes("flex-1 items-center"):
                ui.image("/assets/logo.svg").classes("w-10 h-9 no-darkreader")
                ui.label("nutalert").classes("text-2xl font-bold ml-2")
            with ui.row().classes("flex-1 items-center justify-center"):
                ups_selector(state)
            with ui.row().classes("flex-1 items-center justify-center"):
                with ui.tabs().props("dense").classes("h-10") as tabs:
                    ui.tab("Dashboard")
                    ui.tab("Configuration")
                ui_elements["main_tabs"] = tabs
            with ui.row().classes("flex-1 items-center justify-end"):
                with ui.card().classes("p-2 transition-all") as card:
                    ui_elements["header_status_card"] = card
                    with ui.row().classes("items-center no-wrap gap-x-2"):
                        ui_elements["header_status_icon"] = ui.icon("check_circle").classes("text-lg")
                        ui_elements["header_status_label"] = ui.label("Initializing...")
