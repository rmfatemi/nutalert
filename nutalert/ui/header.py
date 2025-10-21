from nicegui import ui
from typing import Dict, Any

from nutalert.ui.theme import COLOR_THEME


def build_header(ui_elements: Dict[str, Any], state, on_settings_click, on_logo_click):
    all_ok = True
    for ups in state.ups_names:
        status = getattr(state, "ups_status", {}).get(ups, "ok")
        if status != "ok":
            all_ok = False
            break
    status_icon = "check_circle" if all_ok else "warning"
    status_color = COLOR_THEME["success"] if all_ok else COLOR_THEME["warning"]
    status_label = "Devices healthy" if all_ok else "Check status"
    status_bg = COLOR_THEME["success_bg"] if all_ok else COLOR_THEME["error_bg"]

    with ui.header(elevated=False).classes(f"flex px-4 py-2 bg-[{COLOR_THEME['log_bg']}] text-[{COLOR_THEME['text']}]"):
        with ui.row().classes("w-full items-center justify-between gap-4"):
            with ui.row().classes("items-center cursor-pointer gap-1.5").on("click", on_logo_click):
                ui.image("/assets/logo.svg").classes("w-10 h-9 no-darkreader")
                ui.label("nutalert").classes("text-2xl font-bold")
            
            ui_elements["header_center"] = ui.row().classes("items-center justify-center")
            
            with ui.row().classes("items-center gap-2"):
                with (
                    ui.card()
                    .classes("p-2 transition-all h-full flex items-center shadow-none")
                    .style(f"background:{status_bg};") as card
                ):
                    ui_elements["header_status_card"] = card
                    with ui.row().classes("items-center no-wrap gap-x-1 h-full flex-nowrap"):
                        ui_elements["header_status_icon"] = ui.icon(status_icon).style(f"color: {status_color}")
                        ui_elements["header_status_label"] = ui.label(status_label).classes("whitespace-nowrap")
                
                ui_elements["nav_button"] = ui.button(icon="settings", on_click=on_settings_click).props("flat round").classes("text-white")
