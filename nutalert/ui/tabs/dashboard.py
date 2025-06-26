from typing import Dict, Any
from nicegui import ui
import plotly.graph_objects as go

from nutalert.ui.theme import COLOR_THEME


def create_dial_gauge(
    value: float,
    title: str,
    metric_type: str,
    range_min: float,
    range_max: float,
    config: Dict[str, Any],
    warn=None,
    high=None,
    nominal=None,
) -> go.Figure:
    bar_color = COLOR_THEME["primary"]
    basic_alerts = config.get("basic_alerts", {})

    if metric_type == "load":
        max_load = high if high is not None else basic_alerts.get("load", {}).get("max", 90)
        warn_load = warn if warn is not None else max_load / 2
        steps = [
            {"range": [0, warn_load], "color": COLOR_THEME["success"]},
            {"range": [warn_load, max_load], "color": COLOR_THEME["warning"]},
            {"range": [max_load, range_max], "color": COLOR_THEME["error"]},
        ]
        bar_color = (
            COLOR_THEME["error"]
            if value > max_load
            else COLOR_THEME["warning"] if value > warn_load else COLOR_THEME["success"]
        )
    elif metric_type == "charge":
        min_charge = high if high is not None else basic_alerts.get("battery_charge", {}).get("min", 20)
        warn_low = warn if warn is not None else min_charge - 5
        warn_high = min_charge + 5
        steps = [
            {"range": [0, warn_low], "color": COLOR_THEME["error"]},
            {"range": [warn_low, warn_high], "color": COLOR_THEME["warning"]},
            {"range": [warn_high, 100], "color": COLOR_THEME["success"]},
        ]
        bar_color = (
            COLOR_THEME["error"]
            if value < warn_low
            else COLOR_THEME["warning"] if value < warn_high else COLOR_THEME["success"]
        )
    elif metric_type == "runtime":
        min_runtime = high if high is not None else basic_alerts.get("runtime", {}).get("min", 5)
        warn_runtime = warn if warn is not None else min_runtime + ((range_max - min_runtime) / 2)
        steps = [
            {"range": [0, min_runtime], "color": COLOR_THEME["error"]},
            {"range": [min_runtime, warn_runtime], "color": COLOR_THEME["warning"]},
            {"range": [warn_runtime, range_max], "color": COLOR_THEME["success"]},
        ]
        bar_color = (
            COLOR_THEME["error"]
            if value < min_runtime
            else COLOR_THEME["warning"] if value < warn_runtime else COLOR_THEME["success"]
        )
    elif metric_type == "voltage":
        nominal_voltage = nominal if nominal is not None else 120
        warn_deviation = warn if warn is not None else 10
        high_deviation = high if high is not None else 15
        min_voltage = nominal_voltage - warn_deviation
        max_voltage = nominal_voltage + warn_deviation
        display_max = nominal_voltage + high_deviation
        display_min = nominal_voltage - high_deviation
        steps = [
            {"range": [display_min, min_voltage], "color": COLOR_THEME["warning"]},
            {"range": [min_voltage, max_voltage], "color": COLOR_THEME["success"]},
            {"range": [max_voltage, display_max], "color": COLOR_THEME["warning"]},
        ]
        bar_color = (
            COLOR_THEME["success"]
            if min_voltage <= value <= max_voltage
            else (
                COLOR_THEME["warning"]
                if display_min <= value < min_voltage or max_voltage < value <= display_max
                else COLOR_THEME["error"]
            )
        )
        range_min = display_min
        range_max = display_max

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=round(float(value), 1),
            title={"text": title, "font": {"size": 16}},
            gauge={"axis": {"range": [range_min, range_max]}, "bar": {"color": bar_color}, "steps": steps},
        )
    )
    fig.update_layout(
        height=200,
        margin=dict(l=30, r=30, t=50, b=20),
        paper_bgcolor=COLOR_THEME["gauge_background"],
        plot_bgcolor=COLOR_THEME["gauge_background"],
        font={"color": COLOR_THEME["text"]},
    )
    return fig


def build_dashboard_tab(ui_elements: Dict[str, Any], state):
    ups_values = state.nut_values.get(state.selected_ups, {})

    gs = state.config.get("ups_devices", {}).get(state.selected_ups, {}).get("gauge_settings", {})

    def safe_get(d, key, default):
        v = d.get(key, default)
        return default if v is None else v

    load_warn = safe_get(gs.get("load", {}), "warn_threshold", 80)
    load_high = safe_get(gs.get("load", {}), "high_threshold", 100)
    charge_warn = safe_get(gs.get("charge_remaining", {}), "warn_threshold", 35)
    charge_high = safe_get(gs.get("charge_remaining", {}), "high_threshold", 15)
    runtime_warn = safe_get(gs.get("runtime", {}), "warn_threshold", 15)
    runtime_high = safe_get(gs.get("runtime", {}), "high_threshold", 10)
    voltage_nominal = safe_get(gs.get("voltage", {}), "nominal", 120)
    voltage_warn = safe_get(gs.get("voltage", {}), "warn_deviation", 10)
    voltage_high = safe_get(gs.get("voltage", {}), "high_deviation", 15)

    with ui.column().classes("w-full gap-y-4"):
        with ui.grid().classes("grid-cols-2 md:grid-cols-4 w-full gap-4"):
            ui_elements["load_plot"] = ui.plotly(
                create_dial_gauge(
                    float(ups_values.get("ups.load", 0.0)),
                    "UPS Load (%)",
                    "load",
                    0,
                    load_high,
                    state.config,
                    warn=load_warn,
                    high=load_high,
                )
            )
            ui_elements["charge_plot"] = ui.plotly(
                create_dial_gauge(
                    float(ups_values.get("battery.charge", 0.0)),
                    "Battery Charge (%)",
                    "charge",
                    0,
                    100,
                    state.config,
                    warn=charge_warn,
                    high=charge_high,
                )
            )
            ui_elements["runtime_plot"] = ui.plotly(
                create_dial_gauge(
                    float(ups_values.get("actual_runtime_minutes", 0.0)),
                    "Runtime (min)",
                    "runtime",
                    0,
                    180,
                    state.config,
                    warn=runtime_warn,
                    high=runtime_high,
                )
            )
            ui_elements["voltage_plot"] = ui.plotly(
                create_dial_gauge(
                    float(ups_values.get("input.voltage", 0.0)),
                    "Input Voltage (V)",
                    "voltage",
                    voltage_nominal - voltage_high,
                    voltage_nominal + voltage_high,
                    state.config,
                    nominal=voltage_nominal,
                    warn=voltage_warn,
                    high=voltage_high,
                )
            )

        with ui.card().classes(f"w-full bg-[{COLOR_THEME['card']}]"):
            ui.label("UPS Data").classes("text-lg font-semibold")
            ui_elements["raw_data_grid"] = ui.grid().classes(
                "w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-2 mt-4 divide-x divide-gray-700"
            )
