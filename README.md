# UPS Monitoring and Alert System

<p align="left"> <img align="left" src="https://github.com/rmfatemi/nutalert/blob/master/assets/logo.png" width="75"> <strong>nutalert</strong> is a customizable UPS monitoring system designed to connect with NUT (Network UPS Tools) servers. It analyzes UPS status data, sends alerts when specific conditions are met, and supports multiple notification destinations. </p>
<br>

## ✅ Features
- **Seemless connection** to NUT servers to monitor UPS devices
- **Multi-platform support**: **nutalert** supports notifications for
  <p>
  <span>
    <img src="https://github.com/homarr-labs/dashboard-icons/blob/main/svg/telegram.svg" width="20">
    <img src="https://github.com/homarr-labs/dashboard-icons/blob/main/svg/slack.svg" width="20">
    <img src="https://github.com/homarr-labs/dashboard-icons/blob/main/svg/microsoft-teams.svg" width="20">
    <img src="https://github.com/homarr-labs/dashboard-icons/blob/main/svg/gmail.svg" width="20">
    <img src="https://github.com/homarr-labs/dashboard-icons/blob/main/svg/discord.svg" width="20">
    <img src="https://github.com/homarr-labs/dashboard-icons/blob/main/svg/whatsapp.svg" width="20">
    <img src="https://github.com/homarr-labs/dashboard-icons/blob/main/svg/gotify.svg" width="20">
    <img src="https://github.com/homarr-labs/dashboard-icons/blob/main/svg/ntfy.svg" width="20">
    <img src="https://github.com/homarr-labs/dashboard-icons/blob/main/svg/pushover.svg" width="20">
    <img src="https://github.com/homarr-labs/dashboard-icons/blob/main/svg/home-assistant.svg" width="20">
  </span>
   and many more Thanks to <a href="https://github.com/caronc/apprise">Apprise</a> integration.
</p>

- **Modern Web UI** monitor UPS device data and adjust settings
- **Configurable Alerts** based-on:
  - ⏳ Runtime
  - 🔋 Battery charge
  - ⚡ Input voltage
  - 📈 UPS Load
  - 🔄 UPS status
- **Dual Configuration Modes**:
  - 🔤 Basic (individual condition checks)
  - 🧮 Formula (custom expressions)

## 📺 Web Interface
Access the web interface at `http://{server_ip}:8087` to:
- Configure notification destinations
- Adjust rules and UPS limits
- View system logs

<img src="https://github.com/user-attachments/assets/3bfa467c-63d5-4742-8e1e-003b7b947ecd">
<img src="https://github.com/user-attachments/assets/33c5195a-dc40-4a43-a332-abda6b132346">
<img src="https://github.com/user-attachments/assets/2c0b461d-1909-4d1b-a1fb-796640c9da4b">

## 🏗️ Setup Guide

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
      - TZ=America/New_York         # modify if different\
      - API_PASSWORD={PASSWORD}     # required for nut, not nutalert
      - DRIVER=usbhid-ups           # modify based on your ups model
    devices:
      - /dev/bus/usb:/dev/bus/usb   # your ups device
    ports:
      - 3493:3493                   # nut port, modify if needed
    restart: unless-stopped

  nutalert:
    image: ghcr.io/rmfatemi/nutalert:latest
    container_name: nutalert    
    depends_on:
      - nut-upsd
    ports:
      - 8087:8087                   # web ui port, modify if needed
    volumes:
      - /path/to/config_dir:/config # set the correct config path
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
      - /path/to/config_dir:/config # set the correct config path
    ports:
      - "3493:3493"                 # nut server port
      - "8087:8087"                 # web ui port
    restart: unless-stopped
````
Once your `docker-compose.yaml` and `config.yaml` file are ready, start the service with:
```
docker-compose up -d
```

## 🔑 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/rmfatemi/nutalert/blob/master/LICENSE) file for details.
