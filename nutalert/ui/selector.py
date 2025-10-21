from nicegui import ui
from nutalert.ui.theme import COLOR_THEME


def ups_selector_row(ui_elements, state, handler):
    ui_elements["tabs_container"] = ui.row().classes("items-center justify-center")
    
    def rebuild_tabs():
        ui_elements["tabs_container"].clear()
        with ui_elements["tabs_container"]:
            if state.ups_names:
                with ui.tabs().props(
                    "dense align=center "
                    "active-color=orange "
                    "indicator-color=orange "
                    "active-bg-color=rgba(255,143,0,0.15)"
                ).classes(
                    "text-grey-5 transition-all duration-300"
                ).style(
                    "font-weight: 500;"
                ).on("update:model-value", lambda e: handler(e.args)) as tabs:
                    for ups in state.ups_names:
                        ui.tab(ups).classes("transition-all duration-300")
                ui_elements["ups_tabs"] = tabs
                # Set initial value
                if state.selected_ups:
                    tabs.set_value(state.selected_ups)
    
    rebuild_tabs()
    ui_elements["rebuild_ups_tabs"] = rebuild_tabs
