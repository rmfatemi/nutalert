from typing import Dict, Any
import plotly.graph_objects as go
from .theme import COLOR_THEME


def create_dial_gauge(
    value: float, title: str, metric_type: str, range_min: float, range_max: float, config: Dict[str, Any]
) -> go.Figure:
    bar_color = COLOR_THEME["primary"]
    basic_alerts = config.get("basic_alerts", {})

    if metric_type == "load":
        max_load = basic_alerts.get("load", {}).get("max", 90)
        warn_load = max_load / 2
        steps = [
            {"range": [0, warn_load], "color": COLOR_THEME["success"]},
            {"range": [warn_load, max_load], "color": COLOR_THEME["warning"]},
            {"range": [max_load, 100], "color": COLOR_THEME["error"]},
        ]
        bar_color = (
            COLOR_THEME["error"]
            if value > max_load
            else COLOR_THEME["warning"] if value > warn_load else COLOR_THEME["success"]
        )
    elif metric_type == "charge":
        min_charge = basic_alerts.get("battery_charge", {}).get("min", 20)
        warn_low = min_charge - 5
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
        value_mins = value / 60.0
        min_runtime = basic_alerts.get("runtime", {}).get("min", 5)
        range_max_mins = max(30, value_mins * 1.2)
        warn_runtime = min_runtime + (range_max_mins - min_runtime) / 2
        steps = [
            {"range": [0, min_runtime], "color": COLOR_THEME["error"]},
            {"range": [min_runtime, warn_runtime], "color": COLOR_THEME["warning"]},
            {"range": [warn_runtime, range_max_mins], "color": COLOR_THEME["success"]},
        ]
        bar_color = (
            COLOR_THEME["error"]
            if value_mins < min_runtime
            else COLOR_THEME["warning"] if value_mins < warn_runtime else COLOR_THEME["success"]
        )
        value, range_min, range_max = value_mins, 0, range_max_mins
    elif metric_type == "voltage":
        voltage_config = basic_alerts.get("input_voltage", {})
        min_voltage = voltage_config.get("min", 110.0)
        max_voltage = voltage_config.get("max", 130.0)
        display_max = max_voltage + 20
        warn_low = min_voltage - 5
        warn_high = max_voltage + 5
        steps = [
            {"range": [0, warn_low], "color": COLOR_THEME["error"]},
            {"range": [warn_low, min_voltage], "color": COLOR_THEME["warning"]},
            {"range": [min_voltage, max_voltage], "color": COLOR_THEME["success"]},
            {"range": [max_voltage, warn_high], "color": COLOR_THEME["warning"]},
            {"range": [warn_high, display_max], "color": COLOR_THEME["error"]},
        ]
        bar_color = (
            COLOR_THEME["success"]
            if min_voltage <= value <= max_voltage
            else (
                COLOR_THEME["warning"]
                if warn_low <= value < min_voltage or max_voltage < value <= warn_high
                else COLOR_THEME["error"]
            )
        )
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
