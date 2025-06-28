from nicegui import ui
from nutalert.ui.theme import COLOR_THEME


@ui.refreshable
def ups_selector_row(state, handler):
    with ui.row().classes("w-full items-stretch justify-center"):
        for ups in state.ups_names:
            selected = ups == state.selected_ups
            card_classes = f"p-0 !rounded-lg bg-[{COLOR_THEME['card']}]"
            button_classes = "rounded-l-lg rounded-r-none h-full font-bold"
            label_classes = "text-xs pr-4 " + ("text-white" if selected else "text-gray-400")
            ups_values = getattr(state, "nut_values", {}).get(ups, {})
            ups_config = getattr(state, "config", {}).get("ups_devices", {}).get(ups, {})
            model = ups_values.get("device.model") or ups_config.get("model") or "---"
            with ui.card().props("flat bordered").classes(card_classes):
                with ui.row().classes("items-center gap-4 w-full no-wrap"):
                    ui.button(
                        ups,
                        on_click=lambda u=ups: handler(u),
                    ).props(
                        "unelevated"
                    ).classes(button_classes).style(
                        f"background-color: {COLOR_THEME['primary']} !important; color: white !important;"
                        if selected
                        else "background-color: #6b7280 !important; color: white !important;"
                    )
                    ui.label(model).classes(label_classes)
