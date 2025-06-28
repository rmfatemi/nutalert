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
            with ui.row().classes("gap-2"):
                for ups in state.ups_names:
                    selected = ups == state.selected_ups
                    btn_classes = "rounded unelevated dense " + ("text-white" if selected else "text-primary")
                    ui.button(
                        ups,
                        color=COLOR_THEME["primary"] if selected else COLOR_THEME["card"],
                        on_click=lambda u=ups: setattr(state, "selected_ups", u),
                    ).classes(btn_classes)


def build_header(ui_elements: Dict[str, Any], state):
    with ui.header(elevated=True).classes(f"flex px-4 py-2 bg-[{COLOR_THEME['log_bg']}] text-[{COLOR_THEME['text']}]"):
        with ui.row().classes("w-full items-center"):
            with ui.row().classes("flex-1 items-center"):
                ui.image("/assets/logo.svg").classes("w-10 h-9 no-darkreader")
                ui.label("nutalert").classes("text-2xl font-bold ml-2")
            with ui.row().classes("flex-1 items-center justify-center"):
                with ui.tabs().props("dense").classes("h-10") as tabs:
                    ui.tab("Dashboard")
                    ui.tab("Configuration")
                ui_elements["main_tabs"] = tabs
            with ui.row().classes("flex-1 items-center justify-end no-wrap h-full gap-0"):
                with ui.card().classes("p-2 transition-all h-full flex items-center") as card:
                    ui_elements["header_status_card"] = card
                    with ui.row().classes("items-center no-wrap gap-x-2 h-full flex-nowrap"):
                        ups_selector(state)
                        ui_elements["header_status_icon"] = ui.icon("check_circle").classes("text-lg")
                        ui_elements["header_status_label"] = ui.label("Initializing...").classes("whitespace-nowrap")
