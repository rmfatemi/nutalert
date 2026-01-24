from nicegui import ui
from typing import Dict, Any

from nutalert.ui.theme import COLOR_THEME


def _logs_have_errors(logs: str) -> bool:
    if not logs:
        return False
    for line in logs.splitlines():
        if "[ERROR]" in line.upper():
            return True
    return False


def get_overall_status(state):
    has_error = False
    has_waiting = False
    
    if not state.ups_names:
        if _logs_have_errors(state.logs):
            return "error", "warning", COLOR_THEME["warning"], "Check logs", COLOR_THEME["error_bg"]
        return "waiting", "hourglass_empty", COLOR_THEME["warning"], "No devices", COLOR_THEME["error_bg"]
    
    for ups in state.ups_names:
        status = state.ups_status.get(ups, "waiting")
        if status == "error":
            has_error = True
        elif status == "waiting":
            has_waiting = True
    
    if has_error or _logs_have_errors(state.logs):
        return "error", "warning", COLOR_THEME["warning"], "Check status", COLOR_THEME["error_bg"]
    elif has_waiting:
        return "waiting", "hourglass_empty", COLOR_THEME["warning"], "Checking...", COLOR_THEME["error_bg"]
    else:
        device_count = len(state.ups_names)
        status_text = "Device healthy" if device_count == 1 else "Devices healthy"
        return "ok", "check_circle", COLOR_THEME["success"], status_text, COLOR_THEME["success_bg"]


def build_header(ui_elements: Dict[str, Any], state, on_settings_click, on_logo_click):
    _, status_icon, status_color, status_label, status_bg = get_overall_status(state)

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
