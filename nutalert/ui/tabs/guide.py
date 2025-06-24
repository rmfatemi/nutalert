from nicegui import ui

def settings_guide():
    with ui.expansion("Settings Guide", icon="help").classes("w-full mb-4 border rounded-md"):
        ui.markdown(
            """
- **NUT Server**
    - `Host`: IP address or hostname of your NUT (Network UPS Tools) server.
    - `Port`: Port number for the NUT server (default: 3493).
    - `Timeout`: Connection timeout in seconds.
    - `Check Interval`: How often (in seconds) to poll the UPS data.

- **Notifications**
    - `Enable`: Toggle to enable or disable all notifications.
    - `Cooldown`: Minimum seconds between sending new alerts.
    - `URLs`: List of Apprise-compatible notification URLs. [See Apprise documentation](https://github.com/caronc/apprise) for supported services.
    - Each URL can be enabled/disabled individually.
    - Use "Add URL" to add a new notification method.
    - "Test Alerts" sends a test notification to all enabled URLs.

- **Alert Rules**
    - `Alert Mode`: Choose between "basic" (threshold-based) or "formula" (advanced, custom logic).
    - **Basic Alerts**:
        - Set thresholds for battery charge, runtime, load, input voltage, and UPS status.
        - If any enabled alert condition fails, an alert is triggered.
        - `Min`/`Max`: Set minimum/maximum acceptable values.
        - `Message`: Custom notification message for each alert.
        - `Acceptable Statuses`: List of UPS statuses considered normal (e.g., `ol`, `online`).
        - `Alert on any status change`: Enable to alert only when the UPS status changes.
    - **Formula Alert**:
        - Write a custom Python expression using UPS data variables.
        - If the formula evaluates to `True`, an alert is triggered.
        - Available variables: `ups_load`, `battery_charge`, `actual_runtime_minutes`, `battery_voltage`, `input_voltage`, `ups_status`.
        - Example: `battery_charge < 90 or ups_status != 'ol'`
        - `Message`: Custom notification message, can use variables (e.g., `{ups_load}`).
            """
        )
