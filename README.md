# UPS Monitoring and Alert System

<p align="left"> <img align="left" src="https://github.com/user-attachments/assets/1c35f7da-0c58-4842-9b67-3f233edb2b13" width="75"> <strong>nutalert</strong> is a customizable UPS monitoring system designed to connect with NUT (Network UPS Tools) servers. It analyzes UPS status data, sends alerts when specific conditions are met, and supports multiple notification destinations. </p>
<br>

## Features
- **Seemless connection** to NUT servers to monitor UPS devices
- **Configurable Alerts** based-on:
  - 🔋 Battery charge
  - ⏳ Runtime
  - ⚡ Input voltage
  - 📈 UPS Load
  - 🔄 UPS status
- **Dual Configuration Modes**:
  - 🔤 Basic (individual condition checks)
  - 🧮 Formula (custom expressions)
- **Multiple Notification Methods**: Send notifications to over 100 services via:
  - 📢 [ntfy](https://ntfy.sh/) push notifications
  - 🔔 [Apprise](https://github.com/caronc/apprise) (e.g. Telegram, Discord, Slack, Gotify, etc.)
  - 🌎 Webhooks (e.g. [discord](https://discord.com/developers/docs/resources/webhook))
  - 💻 TCP (e.g. [bitvoker](https://github.com/rmfatemi/bitvoker))

## Setup Guide

Before beginning your deployment, make sure your NUT server is operational. The instructions below cover two deployment scenarios: running both the NUT server and **nutalert** in a single Docker environment, or hosting **nutalert** while your NUT server runs externally. You can skip this step if you are setting up `nut-upds` at the same time using this guide.

### Step 1: Verify NUT Server Connectivity
If your NUT server is hosted externally, first verify connectivity from the **nutalert** host:

`/bin/echo -e "list var ups\r" | /usr/bin/nc -w 1 <nut-server-ip> 3493`

A successful response will display a list of available UPS variables from your NUT server confirming that **nutalert** can retrieve your monitoring data.

### Step 2: Prepare the Configuration
1. Download & modify the configuration:

    - Download the [configuration template](https://github.com/rmfatemi/nutalert/blob/master/config.yaml)
    - Edit the template to set your alert thresholds, alert formula, notification preferences, and any sensor-specific parameters.

2. Save your config file:

   - Save your modified configuration as `config.yaml` in a dedicated directory (e.g., `/path/to/config_dir`).

### Docker Deployment Scenarios

#### Co-hosting nut-upds and nutalert
If you wish to run your NUT server using Docker alongside nutalert, create a `docker-compose.yaml` file with the following content:

```yaml
services:
  nut-upsd:
    image: instantlinux/nut-upsd
    container_name: nut
    environment:
      - TZ=America/New_York         # Modify if different
      - API_PASSWORD={PASSWORD}     # API password, nutalert will not need this
      - DRIVER=usbhid-ups           # Modify based on your UPS model
    devices:
      - /dev/bus/usb:/dev/bus/usb   # Your UPS device
    ports:
      - "3493:3493"                 # Modify if needed
    restart: unless-stopped

  nutalert:
    image: ghcr.io/rmfatemi/nutalert:latest
    container_name: nutalert    
    depends_on:
      - nut-upsd
    volumes:
      - /path/to/config_dir:/config # Set the correct config path
    environment:
      - NUT_PORT=3493               # Modify if needed
    restart: unless-stopped
```
#### Using an External NUT Server
If your NUT server is hosted separately, use this streamlined `docker-compose.yaml` for deploying nutalert alone:

````yaml
services:
  nutalert:
    image: ghcr.io/rmfatemi/nutalert:latest
    container_name: nutalert
    volumes:
      - /path/to/config_dir:/config # Set the correct config path
    ports:
      - "3493:3493"                 # NUT server port
    restart: unless-stopped
````
Once your `docker-compose.yaml` and `config.yaml` file are ready, start the service with:
```
docker-compose up -d
```
You can monitor the container's log to see the relevant information and to troubleshoot potential errors using `docker-compose logs -f nutalert`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/rmfatemi/nutalert/blob/master/LICENSE) file for details.
