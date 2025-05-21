# NutAlert - UPS Monitoring and Alert System

NutAlert is a flexible and modular UPS monitoring system that connects to NUT (Network UPS Tools) servers, analyzes UPS status data, and sends alerts when specific conditions are met.

## Features

- Connect to NUT servers to monitor UPS devices
- Configurable alert thresholds for battery charge, runtime, input voltage, and UPS status
- Two alert modes: basic (individual condition checks) and formula (custom expressions)
- Multiple notification methods (via Apprise integration)
- Lightweight FastAPI web server for status monitoring
- Highly modular and maintainable architecture

## Installation


### Using Poetry

```bash
# Clone the repository
git clone https://github.com/yourusername/nutalert.git
cd nutalert

# Install dependencies with Poetry
poetry install
```

## Configuration

Create a configuration file at `~/.config/nutalert/config.yaml` with the following structure:

```yaml
# NUT server connection details
nut_server:
  host: "192.168.1.100"  # NUT server host
  port: 3493             # NUT server port (default: 3493)
  timeout: 2             # Connection timeout in seconds

# How often to check UPS status (in seconds)
check_interval: 60

# Alert mode: "basic" or "formula"
alert_mode: "basic"

# Basic alert configuration

```
###############################################################################
# nut server configuration
###############################################################################

# these settings define the connection parameters to contact the nut (ups) server
nut_server:
  host: "10.0.10.101"            # ip address of the nut server
  port: 3493                     # port used for connection
  timeout: 3                     # socket connection timeout in seconds

###############################################################################
# notifications configuration
###############################################################################

# configure notification methods below; at least one must be enabled.
notifications:
  # ntfy:
  #   url: "http://your.ntfy.server.address"
  #   topic: "nutalert"
  #   tags: "ups"
  #   priority: "5"
  #   token: ""
  #   username: ""
  #   password: ""
  # apprise:
  #   url: "apprise://"
  # webhook:
  #   url: "http://your.webhook.address"
  #   headers:
  #     authorization: "your token"
  #     x-custom-header: "password123"
  tcp:
    enabled: true               # (recommended with bitvoker: https://github.com/rmfatemi/bitvoker)
    host: "10.0.10.101"         # tcp server ip to send notifications
    port: 8083                  # tcp server port

###############################################################################
# check interval and alert mode
###############################################################################

# how often to check the ups data (in seconds)
check_interval: 15

# choose alert mode: "basic" or "formula"
alert_mode: "basic"

###############################################################################
# basic alert confuguration - simple threshold-based alerts
###############################################################################

# if ANY enabled alert condition fails, an alert will be triggered (using OR logic)
basic_alerts:
  # battery charge alert
  battery_charge:
    enabled: true               # set to false to disable this check
    min: 90                     # minimum acceptable battery charge (%)
    message: "battery charge below minimum threshold"
  # runtime alert - simple threshold check
  runtime:
    enabled: true               # set to false to disable this check
    min: 15                     # minimum acceptable runtime in minutes
    message: "runtime below minimum threshold"
  # load alert - separate from runtime
  load:
    enabled: true               # set to false to disable this check
    max: 50                     # maximum acceptable load percentage
    message: "ups load exceeds maximum threshold"
  # voltage alert
  input_voltage:
    enabled: true               # set to false to disable this check
    min: 110.0                  # minimum acceptable input voltage (volts)
    max: 130.0                  # maximum acceptable input voltage (volts)
    message: "input voltage outside acceptable range"
  # status alert
  ups_status:
    enabled: true               # set to false to disable this check
    acceptable: ["ol", "online"] # acceptable ups operational statuses
    message: "ups status not in acceptable list"

###############################################################################
# advanced alert configuration - forumula-based alerts
###############################################################################

# formula mode: create a custom formula using ups data
# available variables for your formula:
#   ups_load - current ups load percentage
#   battery_charge - current battery charge percentage
#   actual_runtime_minutes - current battery runtime in minutes
#   battery_voltage - current battery voltage
#   input_voltage - current input voltage
#   ups_status - current ups status string (lowercase)

# your formula should return True to trigger an alert
# examples:
# - simple condition check: "battery_charge < 90 or ups_status != 'ol'"
# - load-based runtime: "actual_runtime_minutes < (60 if ups_load <= 15 else (30 if ups_load >= 50 else 60 - (ups_load * 0.6)))"
# - complex calculation: "(battery_charge / 100.0) * (battery_voltage / input_voltage) * (actual_runtime_minutes / 60) < 0.5"
formula_alert:
  expression: "(battery_charge < 90 or actual_runtime_minutes < 20) and ups_load > 20"
  message: "ups alert: custom formula conditions not met"

```

## Usage

### As a Service

```bash
# Start the NutAlert monitoring service
nutalert
```

### Programmatically

```python
from nutalert.processor import process_nut_data

# Run a single check
process_nut_data()
```

## Architecture

NutAlert is built with a modular architecture:

- `fetcher.py` - Connects to NUT server and retrieves raw data
- `parser.py` - Parses raw NUT data into structured format
- `alert.py` - Implements alert condition logic
- `processor.py` - Orchestrates the monitoring process
- `notifier.py` - Handles sending notifications
- `server.py` - Provides web interface for monitoring
- `utils.py` - Contains utility functions

## Available Environment Variables

- `NUTALERT_CONFIG_PATH` - Path to configuration file (default: ~/.config/nutalert/config.yaml)
- `NUTALERT_LOG_LEVEL` - Logging level (default: INFO)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
