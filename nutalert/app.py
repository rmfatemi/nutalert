import streamlit as st
import yaml
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from streamlit_ace import st_ace
from nutalert.processor import get_ups_data_and_alerts
from nutalert.utils import load_config, save_config

st.set_page_config(
    page_title="NUT Alert Dashboard",
    page_icon="⚡",
    layout="wide",
)

st.markdown("""
    <style>
           .block-container {
                padding-top: 1rem !important;
                padding-bottom: 0rem;
                padding-left: 5rem;
                padding-right: 5rem;
            }
           .st-emotion-cache-16txtl3 {
                padding-top: 0rem !important;
           }
    </style>
    """, unsafe_allow_html=True)


def create_dial_gauge(value, title, metric_type, range_min, range_max):
    bar_color = "#1565C0"
    steps = []

    if metric_type == 'load':
        steps = [
            {'range': [0, 70], 'color': '#4CAF50'},
            {'range': [70, 90], 'color': '#FFC107'},
            {'range': [90, 100], 'color': '#F44336'}
        ]
        bar_color = "#B71C1C" if value > 90 else "#FBC02D" if value > 70 else "#2E7D32"

    elif metric_type == 'charge':
        steps = [
            {'range': [0, 20], 'color': '#F44336'},
            {'range': [20, 50], 'color': '#FFC107'},
            {'range': [50, 100], 'color': '#4CAF50'}
        ]
        bar_color = "#B71C1C" if value < 20 else "#FBC02D" if value < 50 else "#2E7D32"

    elif metric_type == 'runtime':
        steps = [
            {'range': [0, 5], 'color': '#F44336'},
            {'range': [5, 15], 'color': '#FFC107'},
            {'range': [15, range_max], 'color': '#4CAF50'}
        ]
        bar_color = "#B71C1C" if value < 5 else "#FBC02D" if value < 15 else "#2E7D32"

    elif metric_type == 'voltage':
        if value > 180:
            safe_low, safe_high = 210, 245
            warn_low, warn_high = 200, 255
        else:
            safe_low, safe_high = 110, 128
            warn_low, warn_high = 105, 130

        steps = [
            {'range': [range_min, warn_low], 'color': '#F44336'},
            {'range': [warn_low, safe_low], 'color': '#FFC107'},
            {'range': [safe_low, safe_high], 'color': '#4CAF50'},
            {'range': [safe_high, warn_high], 'color': '#FFC107'},
            {'range': [warn_high, range_max], 'color': '#F44336'}
        ]

        if safe_low <= value <= safe_high:
            bar_color = "#2E7D32"
        elif warn_low <= value < safe_low or safe_high < value <= warn_high:
            bar_color = "#FBC02D"
        else:
            bar_color = "#B71C1C"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(float(value), 1),
        title={'text': title, 'font': {'size': 16}},
        gauge={
            'axis': {'range': [range_min, range_max]},
            'bar': {'color': bar_color},
            'steps': steps,
        }
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)")
    return fig


config = load_config()
st_autorefresh(interval=config.get("check_interval", 15) * 1000, key="data_refresher")

try:
    nut_values, alert_message, is_alerting, logs = get_ups_data_and_alerts()
    data_loaded_successfully = True
except Exception as e:
    st.error(f"Failed to fetch data from NUT server: {e}")
    data_loaded_successfully = False
    nut_values, alert_message, is_alerting, logs = {}, "Error fetching data", True, ""

status_text = nut_values.get('ups.status', 'unknown').upper()
status_color = "green" if "ol" in status_text.lower() else "orange"
st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h1 style="font-size: 2.5rem; font-weight: bold;">⚡ NUT Alert Dashboard</h1>
        <h2 style="font-size: 1.5rem;">Status: <span style='color:{status_color};'>{status_text}</span></h2>
    </div>
    """,
    unsafe_allow_html=True
)

if data_loaded_successfully:
    if is_alerting:
        st.error(f"**Alert:** {alert_message}", icon="🚨")
    else:
        st.success(f"**Status OK:** {alert_message}", icon="✅")

dashboard_tab, logs_tab = st.tabs(["Dashboard", "Logs"])

with dashboard_tab:
    editor_col, gauges_col = st.columns([2, 2])

    with editor_col:
        if 'yaml_text' not in st.session_state:
            st.session_state.yaml_text = yaml.dump(config, sort_keys=False, indent=2)

        edited_config = st_ace(
            value=st.session_state.yaml_text,
            language="yaml",
            theme="tomorrow_night",
            keybinding="vscode",
            font_size=14,
            height=400,
            auto_update=True,
            key="ace_editor"
        )

        if edited_config != st.session_state.yaml_text:
            st.session_state.yaml_text = edited_config

        if st.button("Save Configuration", type="primary"):
            try:
                config_data = yaml.safe_load(st.session_state.yaml_text)
                save_status = save_config(config_data)
                st.success(save_status)
                st.rerun()
            except yaml.YAMLError as e:
                st.error(f"YAML Parsing Error: {e}")

    with gauges_col:
        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(create_dial_gauge(nut_values.get("ups.load", 0), "UPS Load (%)", 'load', 0, 100),
                            use_container_width=True)
            runtime_mins = nut_values.get("battery.runtime", 0) / 60.0
            st.plotly_chart(create_dial_gauge(runtime_mins, "Runtime (min)", 'runtime', 0, max(30, runtime_mins * 1.2)),
                            use_container_width=True)
        with g2:
            st.plotly_chart(
                create_dial_gauge(nut_values.get("battery.charge", 0), "Battery Charge (%)", 'charge', 0, 100),
                use_container_width=True)
            input_voltage = nut_values.get("input.voltage", 0)
            voltage_max_range = 260 if input_voltage > 180 else 150
            st.plotly_chart(create_dial_gauge(input_voltage, "Input Voltage (V)", 'voltage', 0, voltage_max_range),
                            use_container_width=True)

with logs_tab:
    st.subheader("Live Logs")
    st.code(logs, height=500)
