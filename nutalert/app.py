from typing import Dict, Any
from nicegui import ui, app

from nutalert.ui.state import AppState
from nutalert.ui.theme import COLOR_THEME
from nutalert.ui.header import build_header
from nutalert.ui.tabs.dashboard import build_dashboard_tab
from nutalert.ui.tabs.settings import build_settings_tab

state = AppState()


@ui.page("/", title="nutalert")
async def dashboard_page():
    ui.dark_mode(True)
    ui_elements: Dict[str, Any] = {}

    build_header(ui_elements)

    with ui.element("div").classes(f"w-full p-4 bg-[{COLOR_THEME['background']}] text-[{COLOR_THEME['text']}]"):
        # Use the header's tabs for tab_panels
        with ui.tab_panels(ui_elements["main_tabs"], value="Dashboard").classes("w-full"):
            with ui.tab_panel("Dashboard"):
                build_dashboard_tab(ui_elements, state)
            with ui.tab_panel("Configuration"):
                build_settings_tab(state, ui_elements)

        ui.timer(interval=1, callback=lambda: state.update_ui_components(ui_elements), active=True)


app.on_startup(state.poll_ups_data)

app.add_static_files("/assets", "assets")


def main():
    ui.run(title="nutalert", port=8087, favicon="assets/logo.ico", reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    main()
