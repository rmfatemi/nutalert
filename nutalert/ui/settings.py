from io import StringIO

from ruamel.yaml import YAML, YAMLError
from nicegui import ui
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ValidationError

from nutalert.ui.theme import COLOR_THEME
from nutalert.notifier import NutAlertNotifier
from nutalert.config import save_config_text, CONFIG_PATH

_yaml = YAML()
_yaml.preserve_quotes = True


class NutServerConfig(BaseModel):
    host: str
    port: int = Field(gt=0, le=65535)
    check_interval: int = Field(ge=5)


class NotificationsConfig(BaseModel):
    enabled: bool
    cooldown: int
    urls: List[Dict[str, Any]]


class AppConfig(BaseModel):
    ups_devices: Dict[str, Any]
    nut_server: NutServerConfig
    notifications: Optional[NotificationsConfig] = None


def build_configuration_tab(ui_elements: Dict[str, Any], state):
    with ui.column().classes("w-full gap-y-4"):
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
                def save_and_apply():
                    try:
                        new_config_data = _yaml.load(StringIO(state.config_text))
                        AppConfig.model_validate(new_config_data)
                        save_status = save_config_text(state.config_text)
                        state.config = dict(new_config_data)
                        ui.notify(save_status, color="positive" if "successfully" in save_status else "negative")
                    except ValidationError as e:
                        ui.notify(f"Configuration Error: {e}", color="negative", multi_line=True, wrap=True)
                    except YAMLError as e:
                        ui.notify(f"YAML Syntax Error: {e}", color="negative", multi_line=True, wrap=True)
                    except Exception as e:
                        ui.notify(f"An unexpected error occurred: {e}", color="negative")

                def send_test_notification():
                    notifier = NutAlertNotifier(state.config)
                    success = notifier.notify_apprise("Test Notification", "This is a test notification from nutalert.")
                    if success:
                        ui.notify("Test notification sent successfully!", color="positive")
                    else:
                        ui.notify("Failed to send test notification.", color="negative")

                ui.button("Save Configuration", on_click=save_and_apply, icon="save", color=COLOR_THEME["button_color"])
                ui.button("Test Notification", on_click=send_test_notification, icon="notification_important", color=COLOR_THEME["button_color"])
                ui.button("Download Config", on_click=lambda: ui.download(CONFIG_PATH), icon="download", color=COLOR_THEME["button_color"])
            
            ui.link(
                "Need help? Check the template",
                "https://github.com/rmfatemi/nutalert/blob/master/config.example.yaml",
                new_tab=True,
            ).classes("text-sm text-gray-500 hover:text-gray-400")
