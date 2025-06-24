# UPS Monitoring and Alert System

<p align="left"> <img align="left" src="https://github.com/rmfatemi/nutalert/blob/master/assets/logo.png" width="75"> <strong>nutalert</strong> is a self-hosted UPS monitoring system for NUT (Network UPS Tools) servers. It features a modern web interface to visualize live data and manage settings, sends customizable alerts when specific conditions are met, and supports dozens of notification destinations </p>
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

![image](https://github.com/user-attachments/assets/d5137732-acfe-4c90-9eed-a1070990cb22)
![image](https://github.com/user-attachments/assets/e7721d9a-f097-44d5-873c-03a4b29486b3)
![image](https://github.com/user-attachments/assets/23afb7cf-9691-4d1b-b1a1-79ca90dd3127)

## 🏗️ Setup Guide

Before beginning your deployment, make sure your NUT server is operational. The instructions below cover two deployment scenarios: running both the NUT server and **nutalert** in a single Docker environment, or hosting **nutalert** while your NUT server runs externally. You can skip this step if you are setting up `nut-upds` at the same time using this guide.

### Verify NUT Server Connectivity
This set up guide assumes you already have NUT server set up. First, verify connectivity from the **nutalert** host:

```bash
/bin/echo -e "list ups\r" | /usr/bin/nc -w 1 <nut-server-ip> 3493
```

A successful response will display a list of available UPS devices from your NUT server confirming that **nutalert** can retrieve your monitoring data.

### Docker Deployment Scenarios

If you wish to run your NUT server using Docker alongside nutalert, create a `docker-compose.yaml` file with the following content:

```yaml
services:
  nutalert:
    image: ghcr.io/rmfatemi/nutalert:latest
    container_name: nutalert
    depends_on:
      - nut-upsd
    ports:
      - 8087:8087                   # web ui port
    volumes:
      - /path/to/config_dir:/config # set the correct config path
    restart: unless-stopped
```

Start the service with:
```bash
docker-compose up -d
```

## 🔑 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/rmfatemi/nutalert/blob/master/LICENSE) file for details.
