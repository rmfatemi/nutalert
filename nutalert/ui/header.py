from nicegui import ui
from typing import Dict, Any

from nutalert.ui.theme import COLOR_THEME


def _logs_have_recent_errors(state) -> bool:
    if state._consecutive_clean_polls >= 2:
        return False
    if not state.logs:
        return False
    for line in state.logs.splitlines():
        if "[ERROR]" in line.upper():
            return True
    return False


def _count_device_statuses(state):
    ok_count = 0
    error_count = 0
    waiting_count = 0
    
    for ups in state.ups_names:
        status = state.ups_status.get(ups, "waiting")
        if status == "ok":
            ok_count += 1
        elif status == "error":
            error_count += 1
        else:
            waiting_count += 1
    
    return ok_count, error_count, waiting_count


def get_overall_status(state):
    has_error = False
    has_waiting = False
    has_log_errors = _logs_have_recent_errors(state)
    
    if not state.ups_names:
        if has_log_errors:
            return (
                "error",
                "error_outline",
                COLOR_THEME["warning"],
                "Connection error",
                COLOR_THEME["error_bg"],
                "Cannot connect to NUT server. Check logs for details."
            )
        return (
            "waiting",
            "hourglass_empty",
            COLOR_THEME["warning"],
            "Connecting...",
            COLOR_THEME["error_bg"],
            "Waiting to discover UPS devices from NUT server."
        )
    
    ok_count, error_count, waiting_count = _count_device_statuses(state)
    total_count = len(state.ups_names)
    
    for ups in state.ups_names:
        status = state.ups_status.get(ups, "waiting")
        if status == "error":
            has_error = True
        elif status == "waiting":
            has_waiting = True
    
    if has_error or has_log_errors:
        if error_count == total_count:
            label = f"All {total_count} devices alerting"
        elif error_count > 0:
            label = f"{error_count}/{total_count} alerting"
        else:
            label = "Check logs"
        
        tooltip = f"Connected: {total_count} device(s)\nOK: {ok_count}, Alerting: {error_count}, Checking: {waiting_count}"
        if has_log_errors:
            tooltip += "\n\n⚠️ Errors detected in logs"
        
        return (
            "error",
            "warning",
            COLOR_THEME["warning"],
            label,
            COLOR_THEME["error_bg"],
            tooltip
        )
    elif has_waiting:
        label = f"Checking {waiting_count}/{total_count}..."
        tooltip = f"Connected: {total_count} device(s)\nOK: {ok_count}, Checking: {waiting_count}"
        return (
            "waiting",
            "sync",
            COLOR_THEME["warning"],
            label,
            COLOR_THEME["error_bg"],
            tooltip
        )
    else:
        if total_count == 1:
            label = "1 device healthy"
        else:
            label = f"{total_count} devices healthy"
        
        tooltip = f"Connected: {total_count} device(s)\nAll devices operating normally."
        return (
            "ok",
            "check_circle",
            COLOR_THEME["success"],
            label,
            COLOR_THEME["success_bg"],
            tooltip
        )


def build_header(ui_elements: Dict[str, Any], state, on_settings_click, on_logo_click):
    _, status_icon, status_color, status_label, status_bg, status_tooltip = get_overall_status(state)

    with ui.header(elevated=False).classes(f"flex px-4 py-2 bg-[{COLOR_THEME['log_bg']}] text-[{COLOR_THEME['text']}]"):
        with ui.row().classes("w-full items-center justify-between gap-4"):
            with ui.row().classes("items-center cursor-pointer gap-1.5").on("click", on_logo_click):
                ui.image("/assets/logo.svg").classes("w-10 h-9 no-darkreader")
                ui.label("nutalert").classes("text-2xl font-bold")
            
            ui_elements["header_center"] = ui.row().classes("items-center justify-center")
            
            with ui.row().classes("items-center gap-2"):
                with (
                    ui.card()
                    .classes("p-2 transition-all h-full flex items-center shadow-none cursor-help")
                    .style(f"background:{status_bg};") as card
                ):
                    ui_elements["header_status_card"] = card
                    with ui.row().classes("items-center no-wrap gap-x-1 h-full flex-nowrap"):
                        ui_elements["header_status_icon"] = ui.icon(status_icon).style(f"color: {status_color}")
                        ui_elements["header_status_label"] = ui.label(status_label).classes("whitespace-nowrap")
                    
                    ui_elements["header_status_tooltip"] = ui.tooltip(status_tooltip).classes("text-sm whitespace-pre-line")
                
                ui_elements["nav_button"] = ui.button(icon="settings", on_click=on_settings_click).props("flat round").classes("text-white")
