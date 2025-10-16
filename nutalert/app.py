import yaml

from nicegui import ui, app
from typing import Dict, Any

from nutalert.ui.state import AppState
from nutalert.ui.theme import COLOR_THEME
from nutalert.ui.header import build_header
from nutalert.ui.selector import ups_selector_row
from nutalert.ui.dashboard import build_dashboard_tab
from nutalert.ui.settings import build_configuration_tab


state = AppState()


@ui.page("/", title="nutalert")
async def dashboard_page():
    ui.dark_mode(True)
    ui_elements: Dict[str, Any] = {}

    build_header(ui_elements, state)

    def handle_selection(selected_ups):
        state.selected_ups = selected_ups
        ups_selector_row.refresh()
        build_dashboard_tab.refresh()
    
    state._selector_refresh_callback = ups_selector_row.refresh

    with ui.element("div").classes(f"w-full px-4 bg-[{COLOR_THEME['background']}] text-[{COLOR_THEME['text']}]"):
        with ui.tab_panels(ui_elements["main_tabs"], value="Dashboard").classes("w-full"):
            with ui.tab_panel("Dashboard"):
                ups_selector_row(state, handle_selection)
                build_dashboard_tab(ui_elements, state)
            with ui.tab_panel("Settings"):
                build_configuration_tab(ui_elements, state)

        ui.timer(interval=1, callback=lambda: state.update_ui_components(ui_elements), active=True)


app.on_startup(state.poll_ups_data)
app.add_static_files("/assets", "assets")


def main():
    ui.run(title="nutalert", port=8087, favicon="assets/logo.ico", reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    main()
