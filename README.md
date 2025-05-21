<p align="center">
  <img src="https://github.com/user-attachments/assets/1c35f7da-0c58-4842-9b67-3f233edb2b13" width="100">
  <img src="https://github.com/user-attachments/assets/ca070ec4-b918-48f5-a201-e9ec2141cc65" width="353">
</p>

# UPS Monitoring and Alert System

**nutalert** is a flexible highly customizable and modular UPS monitoring system that connects to NUT (Network UPS Tools) servers, analyzes UPS status data, and sends alerts when specific conditions are met.

## Features
- Connect to **NUT servers** to monitor UPS devices
- **Configurable Alert Thresholds** for:
  - 🔋 Battery charge
  - ⏳ Runtime
  - ⚡ Input voltage
  - 📈 UPS Load
  - 🔄 UPS status
- **Two Alert Modes**:
  - 🔤 Basic (individual condition checks)
  - 🧮 Formula (custom expressions)
- **Multiple Notification Methods**: Send notifications to over 100 services via:
  - 📢 [ntfy](https://ntfy.sh/)
  - 🔔 [apprise](https://github.com/caronc/apprise) (e.g. Telegram, Discord, Slack, Amazon SNS, Gotify, etc.)
  - 🌎 webhooks (e.g. [discord](https://discord.com/developers/docs/resources/webhook))
  - 💻 tcp (e.g. [bitvoker](https://github.com/rmfatemi/bitvoker))
- **Highly Modular & Maintainable Architecture**


## Setup
Before proceeding, make sure your NUT server is set up and running. To check if **nutalert** has the necessary access to retrieve data, run the following command:

`/bin/echo -e "list var ups\r" | /usr/bin/nc -w 1 <nut-server-ip> <nut-server-port (usually 3493)>`

This will return a list of available variables provided by your NUT server, confirming successful access.

This repository supports two ways of running **nutalert**. For a consistent and isolated environment, using Docker is recommended.
### Docker

Create a `docker-compose.yaml` file copy the following inside it:

```
services:
  nutalert:
    image: ghcr.io/rmfatemi/nutalert:latest
    container_name: nutalert
    ports:
      - "3493:3493"    # NUT server port
    volumes:
      - /path/to/your/config:/config
    restart: unless-stopped
```
Then start the service with:
```
docker-compose up -d
```
### Standalone Installation
#### Prerequisites

- Python 3.11 or higher
- [Poetry](https://python-poetry.org/docs/#installation) package manager
- [GNU Make](https://www.gnu.org/software/make/) utility
  -    `sudo apt-get install make` (Debian-based Linux), or `brew install make` (macOS)
1. Clone the repository:
    ```bash
    git clone https://github.com/rmfatemi/nutalert.git
    cd nutalert
    ```

2. Install dependencies:
    ```bash
    make install
    ```

3. Run the application:
    ```bash
    poetry run nutalert
    ```

## Configuration

Create a configuration file at `config.yaml` with the following structure and customize it based on your needs and environment:

```yaml
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
  ntfy:
    enabled: false
    url: "http://your.ntfy.server.address"
    topic: "nutalert"
    tags: "ups"
    priority: "5"
    token: ""
    username: ""
    password: ""
  apprise:
    enabled: false
    url: "apprise://"
  webhook:
    enabled: false
    url: "http://your.webhook.address"
    headers:
      authorization: "your token"
      x-custom-header: "password123"
  tcp:
    enabled: true
    host: "10.0.10.101"
    port: 8083

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
    enabled: true
    min: 90                     # minimum acceptable battery charge (%)
    message: "battery charge below minimum threshold"
  # runtime alert - simple threshold check
  runtime:
    enabled: true
    min: 15                     # minimum acceptable runtime in minutes
    message: "runtime below minimum threshold"
  # load alert - separate from runtime
  load:
    enabled: true
    max: 50                     # maximum acceptable load percentage
    message: "ups load exceeds maximum threshold"
  # voltage alert
  input_voltage:
    enabled: false
    min: 110.0                  # minimum acceptable input voltage (volts)
    max: 130.0                  # maximum acceptable input voltage (volts)
    message: "input voltage outside acceptable range"
  # status alert
  ups_status:
    enabled: true
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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/rmfatemi/nutalert/blob/master/LICENSE) file for details.
