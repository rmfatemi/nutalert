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

    def show_dashboard():
        state.current_page = "dashboard"
        ui_elements["main_content"].clear()
        with ui_elements["main_content"]:
            build_dashboard_tab(ui_elements, state)
        # Update header
        ui_elements["nav_button"].props("icon=settings")
        ui_elements["tabs_container"].set_visibility(True)
    
    def show_settings():
        state.current_page = "settings"
        ui_elements["main_content"].clear()
        with ui_elements["main_content"]:
            build_configuration_tab(ui_elements, state)
        # Update header
        ui_elements["nav_button"].props("icon=home")
        ui_elements["tabs_container"].set_visibility(False)
    
    def handle_selection(selected_ups):
        state.selected_ups = selected_ups
    
    def toggle_page():
        if state.current_page == "dashboard":
            show_settings()
        else:
            show_dashboard()
    
    build_header(ui_elements, state, on_settings_click=toggle_page, on_logo_click=show_dashboard)
    
    # Add UPS selector to header center
    with ui_elements["header_center"]:
        ups_selector_row(ui_elements, state, handle_selection)
    
    state._selector_refresh_callback = lambda: None  # No-op, not needed anymore
    state._rebuild_tabs_callback = ui_elements.get("rebuild_ups_tabs")

    with ui.element("div").classes(f"w-full px-4 bg-[{COLOR_THEME['background']}] text-[{COLOR_THEME['text']}]"):
        ui_elements["main_content"] = ui.column().classes("w-full")
        show_dashboard()  # Start with dashboard

        ui.timer(interval=1, callback=lambda: state.update_ui_components(ui_elements), active=True)


app.on_startup(state.poll_ups_data)
app.add_static_files("/assets", "assets")


def main():
    ui.run(title="nutalert", port=8087, favicon="assets/logo.ico", reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    main()
