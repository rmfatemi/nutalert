from io import StringIO

from ruamel.yaml import YAML, YAMLError
from nicegui import ui
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

from nutalert.ui.theme import COLOR_THEME
from nutalert.notifier import NutAlertNotifier
from nutalert.config import save_config_text, load_config, load_config_text, CONFIG_PATH
from nutalert.utils import setup_logger

logger = setup_logger("settings")

_yaml = YAML()
_yaml.preserve_quotes = True

NOTIFY_SUCCESS_TIMEOUT = 5000
NOTIFY_ERROR_TIMEOUT = 20000
NOTIFY_CRITICAL_TIMEOUT = 30000


class NutServerConfig(BaseModel):
    host: str
    port: int = Field(gt=0, le=65535)
    timeout: Optional[int] = Field(default=5, ge=1)
    check_interval: Optional[int] = Field(default=15, ge=5)


class NotificationsConfig(BaseModel):
    enabled: bool
    cooldown: int
    urls: str = ""


class AppConfig(BaseModel):
    config_version: Optional[int] = None
    ups_devices: Dict[str, Any]
    nut_server: NutServerConfig
    notifications: Optional[NotificationsConfig] = None


def build_configuration_tab(ui_elements: Dict[str, Any], state):
    original_nut_server = state.config.get("nut_server", {}).copy()
    
    with ui.column().classes("w-full gap-y-4"):
        error_banner_container = ui.row().classes("w-full")
        ui_elements["error_banner_container"] = error_banner_container
        
        with ui.row().classes("w-full gap-4").style("align-items: flex-start;"):
            with ui.column().classes("flex-1").style("min-width: 0;"):
                ui.label("YAML Editor").classes("text-md font-medium mb-2")
                ui.codemirror(
                    value=state.config_text,
                    language="yaml",
                    on_change=lambda e: setattr(state, "config_text", e.value)
                ).props(f"line-numbers theme={COLOR_THEME['codemirror_theme']}").classes("w-full border text-xs").style("height: 75vh; width: 100%; font-size: 0.75rem;")
            
            with ui.column().classes("flex-1").style("min-width: 0;"):
                ui.label("Live Logs").classes("text-md font-medium mb-2")
                ui_elements["log_view"] = ui.log(max_lines=500).classes(
                    f"w-full bg-[{COLOR_THEME['log_bg']}] font-mono text-xs p-2 rounded border"
                ).style("height: 75vh; width: 100%; overflow-y: auto; flex-shrink: 0;")

        with ui.row().classes("w-full justify-between items-center gap-x-4 mt-4"):
            with ui.row().classes("items-center gap-x-4"):
                def show_persistent_error(message: str):
                    error_banner_container.clear()
                    with error_banner_container:
                        with ui.card().classes("w-full p-3 bg-red-900 border border-red-700"):
                            with ui.row().classes("w-full items-center justify-between"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon("error", color="red-400").classes("text-xl")
                                    ui.label(message).classes("text-red-200 text-sm")
                                ui.button(icon="close", on_click=lambda: error_banner_container.clear()).props("flat dense round").classes("text-red-400")
                
                def clear_error_banner():
                    error_banner_container.clear()
                
                def check_nut_server_changed(new_config_data: dict) -> bool:
                    new_nut = new_config_data.get("nut_server", {})
                    return (
                        new_nut.get("host") != original_nut_server.get("host") or
                        new_nut.get("port") != original_nut_server.get("port")
                    )
                
                async def save_and_apply():
                    clear_error_banner()
                    try:
                        logger.info("validating configuration...")
                        new_config_data = _yaml.load(StringIO(state.config_text))
                        AppConfig.model_validate(new_config_data)
                        logger.info("configuration validated successfully")
                        
                        nut_server_changed = check_nut_server_changed(new_config_data)
                        
                        save_status = save_config_text(state.config_text)
                        reloaded_config = load_config()
                        state.config = reloaded_config
                        state.config_text = load_config_text()
                        state.ups_names = list(reloaded_config.get("ups_devices", {}).keys())
                        state.ups_status = {name: state.ups_status.get(name, "waiting") for name in state.ups_names}
                        if not state.selected_ups or state.selected_ups not in state.ups_names:
                            state.selected_ups = state.ups_names[0] if state.ups_names else ""
                        logger.info("configuration saved and applied")
                        
                        if "successfully" in save_status:
                            if nut_server_changed:
                                logger.info("nut server settings changed, reloading page...")
                                ui.navigate.reload()
                            else:
                                ui.notify(save_status, color="positive", timeout=NOTIFY_SUCCESS_TIMEOUT)
                        else:
                            ui.notify(save_status, color="negative", timeout=NOTIFY_ERROR_TIMEOUT)
                            
                    except ValidationError as e:
                        errors = e.errors()
                        if errors:
                            first_error = errors[0]
                            field_path = " -> ".join(str(loc) for loc in first_error.get("loc", []))
                            error_type = first_error.get("type", "unknown")
                            error_msg = first_error.get("msg", str(e))
                            if field_path:
                                full_error = f"field '{field_path}': {error_msg} (type: {error_type})"
                            else:
                                full_error = f"{error_msg} (type: {error_type})"
                        else:
                            full_error = str(e)
                        logger.error(f"configuration validation failed: {full_error}")
                        ui.notify(f"validation error: {full_error}", color="negative", multi_line=True, timeout=NOTIFY_CRITICAL_TIMEOUT)
                        show_persistent_error(f"Validation Error: {full_error}")
                    except YAMLError as e:
                        error_msg = str(e)
                        logger.error(f"yaml syntax error: {error_msg}")
                        ui.notify(f"yaml syntax error: {error_msg}", color="negative", multi_line=True, timeout=NOTIFY_CRITICAL_TIMEOUT)
                        show_persistent_error(f"YAML Syntax Error: {error_msg}")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"unexpected error saving config: {error_msg}")
                        ui.notify(f"unexpected error: {error_msg}", color="negative", timeout=NOTIFY_ERROR_TIMEOUT)
                        show_persistent_error(f"Error: {error_msg}")

                def send_test_notification():
                    notifier = NutAlertNotifier(state.config)
                    logger.info("sending test notification...")
                    success, error_msg = notifier.notify_apprise("Test Notification", "This is a test notification from nutalert.")
                    if success:
                        logger.info("test notification sent successfully")
                        ui.notify("test notification sent successfully", color="positive", timeout=NOTIFY_SUCCESS_TIMEOUT)
                    else:
                        logger.error(f"test notification failed: {error_msg}")
                        ui.notify(f"notification failed: {error_msg}", color="negative", multi_line=True, timeout=NOTIFY_ERROR_TIMEOUT)

                ui.button("Save Configuration", on_click=save_and_apply, icon="save", color=COLOR_THEME["button_color"])
                ui.button("Test Notification", on_click=send_test_notification, icon="notification_important", color=COLOR_THEME["button_color"])
                ui.button("Download Config", on_click=lambda: ui.download(CONFIG_PATH), icon="download", color=COLOR_THEME["button_color"])
            
            ui.link(
                "Need help? Check the template",
                "https://github.com/rmfatemi/nutalert/blob/master/config.example.yaml",
                new_tab=True,
            ).classes("text-sm text-gray-500 hover:text-gray-400")
