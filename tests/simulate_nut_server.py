import socket
import time
import random
import threading

HOST = "0.0.0.0"
PORT = 3493
POLL_FREQ_SECONDS = 2

UPS_DATA = {
    "apc": {
        "battery.charge": "100",
        "battery.charge.low": "10",
        "battery.charge.warning": "50",
        "battery.date": "2025/01/10",
        "battery.mfr.date": "2024/11/05",
        "battery.runtime": "2856",
        "battery.runtime.low": "120",
        "battery.type": "PbAc",
        "battery.voltage": "27.3",
        "battery.voltage.nominal": "24.0",
        "device.mfr": "American Power Conversion",
        "device.model": "Back-UPS RS 1350MS",
        "device.serial": "3B2026X27482",
        "device.type": "ups",
        "driver.debug": "0",
        "driver.flag.allow_killpower": "0",
        "driver.name": "usbhid-ups",
        "driver.parameter.pollfreq": "30",
        "driver.parameter.pollinterval": "2",
        "driver.parameter.port": "auto",
        "driver.parameter.synchronous": "auto",
        "driver.state": "quiet",
        "driver.version": "2.8.2",
        "driver.version.data": "APC HID 0.100",
        "driver.version.internal": "0.53",
        "driver.version.usb": "libusb-1.0.27",
        "input.sensitivity": "medium",
        "input.transfer.high": "144",
        "input.transfer.low": "88",
        "input.transfer.reason": "input voltage out of range",
        "input.voltage": "120.0",
        "input.voltage.nominal": "120",
        "ups.beeper.status": "enabled",
        "ups.delay.shutdown": "20",
        "ups.firmware": "951.e4 .D",
        "ups.firmware.aux": "e4",
        "ups.load": "15",
        "ups.mfr": "American Power Conversion",
        "ups.mfr.date": "2024/11/05",
        "ups.model": "Back-UPS RS 1350MS",
        "ups.productid": "0002",
        "ups.realpower.nominal": "810",
        "ups.serial": "3B2026X27482",
        "ups.status": "OL",
        "ups.test.result": "No test initiated",
        "ups.timer.reboot": "0",
        "ups.timer.shutdown": "-1",
        "ups.vendorid": "051d",
    },
    "cyberpower": {
        "battery.charge": "100",
        "battery.charge.low": "20",
        "battery.charge.warning": "40",
        "battery.date": "2026/05/20",
        "battery.mfr.date": "2026/03/15",
        "battery.runtime": "3600",
        "battery.runtime.low": "300",
        "battery.type": "PbAc",
        "battery.voltage": "13.7",
        "battery.voltage.nominal": "12.0",
        "device.mfr": "CyberPower Systems",
        "device.model": "CP1500PFCLCD",
        "device.serial": "CT5827B40192",
        "device.type": "ups",
        "driver.debug": "0",
        "driver.flag.allow_killpower": "0",
        "driver.name": "usbhid-ups",
        "driver.parameter.pollfreq": "30",
        "driver.parameter.pollinterval": "2",
        "driver.parameter.port": "auto",
        "driver.parameter.synchronous": "auto",
        "driver.state": "quiet",
        "driver.version": "2.8.2",
        "driver.version.data": "CyberPower HID 0.4",
        "driver.version.internal": "0.53",
        "driver.version.usb": "libusb-1.0.27",
        "input.sensitivity": "low",
        "input.transfer.high": "139",
        "input.transfer.low": "91",
        "input.transfer.reason": "input voltage out of range",
        "input.voltage": "119.5",
        "input.voltage.nominal": "120",
        "ups.beeper.status": "disabled",
        "ups.delay.shutdown": "30",
        "ups.firmware": "CR007.e1.1",
        "ups.firmware.aux": "e1",
        "ups.load": "30",
        "ups.mfr": "CyberPower Systems",
        "ups.mfr.date": "2026/03/15",
        "ups.model": "CP1500PFCLCD",
        "ups.productid": "0501",
        "ups.realpower.nominal": "900",
        "ups.serial": "CT5827B40192",
        "ups.status": "OL",
        "ups.test.result": "No test initiated",
        "ups.timer.reboot": "0",
        "ups.timer.shutdown": "-1",
        "ups.vendorid": "0764",
    },
    "eaton220": {
        "battery.charge": "100",
        "battery.charge.low": "15",
        "battery.charge.warning": "30",
        "battery.date": "2027/02/01",
        "battery.mfr.date": "2027/01/15",
        "battery.runtime": "4500",
        "battery.runtime.low": "600",
        "battery.type": "Li-Ion",
        "battery.voltage": "54.6",
        "battery.voltage.nominal": "48.0",
        "device.mfr": "Eaton",
        "device.model": "5P 1550 R 220V",
        "device.serial": "G201E4C02987",
        "device.type": "ups",
        "driver.debug": "0",
        "driver.flag.allow_killpower": "0",
        "driver.name": "usbhid-ups",
        "driver.parameter.pollfreq": "30",
        "driver.parameter.pollinterval": "2",
        "driver.parameter.port": "auto",
        "driver.parameter.synchronous": "auto",
        "driver.state": "quiet",
        "driver.version": "2.8.2",
        "driver.version.data": "Eaton HID 0.9",
        "driver.version.internal": "0.53",
        "driver.version.usb": "libusb-1.0.27",
        "input.sensitivity": "high",
        "input.transfer.high": "264",
        "input.transfer.low": "176",
        "input.transfer.reason": "input voltage out of range",
        "input.voltage": "220.5",
        "input.voltage.nominal": "220",
        "ups.beeper.status": "enabled",
        "ups.delay.shutdown": "60",
        "ups.firmware": "02.14.0017",
        "ups.firmware.aux": "17",
        "ups.load": "55",
        "ups.mfr": "Eaton",
        "ups.mfr.date": "2027/01/15",
        "ups.model": "5P 1550 R 220V",
        "ups.productid": "ffff",
        "ups.realpower.nominal": "1100",
        "ups.serial": "G201E4C02987",
        "ups.status": "OL",
        "ups.test.result": "No test initiated",
        "ups.timer.reboot": "0",
        "ups.timer.shutdown": "-1",
        "ups.vendorid": "0463",
    },
}
INITIAL_RUNTIMES = {name: int(data["battery.runtime"]) for name, data in UPS_DATA.items()}


def update_dynamic_values():
    global UPS_DATA
    while True:
        for ups_name, data in UPS_DATA.items():
            load = int(data["ups.load"])
            new_load = load + random.randint(-2, 2)
            data["ups.load"] = str(min(100, max(5, new_load)))

            nominal_voltage = int(data["input.voltage.nominal"])
            if nominal_voltage == 120:
                data["input.voltage"] = f"{random.uniform(118.5, 121.5):.1f}"
            else:
                data["input.voltage"] = f"{random.uniform(218.0, 222.0):.1f}"

            if data["ups.status"] == "OB" or data["ups.status"] == "LB":
                charge = int(data["battery.charge"])
                if charge > 0:
                    charge -= 1
                    data["battery.charge"] = str(charge)
                    runtime = int(float(data["battery.runtime"]))
                    data["battery.runtime"] = str(max(0, int(runtime * 0.95)))
                    data["battery.voltage"] = f"{float(data['battery.voltage']) - 0.05:.2f}"
                if charge <= int(data["battery.charge.low"]):
                    data["ups.status"] = "LB"

            elif data["ups.status"] == "OL":
                charge = int(data["battery.charge"])
                if charge < 100:
                    charge = min(100, charge + 1)
                    data["battery.charge"] = str(charge)

                    max_runtime = INITIAL_RUNTIMES[ups_name]
                    current_runtime = int(data["battery.runtime"])
                    data["battery.runtime"] = str(min(max_runtime, int(current_runtime * 1.05)))

                nominal_batt_volt = float(data["battery.voltage.nominal"])
                charge_volt_cap = nominal_batt_volt * 1.14
                current_batt_volt = float(data["battery.voltage"])
                if current_batt_volt < charge_volt_cap:
                    new_volt = min(charge_volt_cap, current_batt_volt + 0.05)
                    data["battery.voltage"] = f"{new_volt:.2f}"

            if random.randint(1, 200) == 1 and data["ups.status"] == "OL":
                data["ups.status"] = "OB"
                data["input.transfer.reason"] = "simulated power loss"

        time.sleep(POLL_FREQ_SECONDS)


def handle_client(conn, addr):
    try:
        raw_data = conn.recv(1024)
        if not raw_data:
            return

        command = raw_data.decode("utf-8").strip().upper()

        response = ""
        if command == "LIST UPS":
            response = "BEGIN LIST UPS\n"
            for ups_name in UPS_DATA:
                description = UPS_DATA[ups_name].get("device.model", "Simulated UPS")
                response += f'UPS {ups_name} "{description}"\n'
            response += "END LIST UPS\n"

        elif command.startswith("LIST VAR"):
            parts = command.split()
            if len(parts) == 3:
                ups_name = parts[2].lower()
                if ups_name in UPS_DATA:
                    response = f"BEGIN LIST VAR {ups_name}\n"
                    for key, value in UPS_DATA[ups_name].items():
                        response += f'VAR {ups_name} {key} "{value}"\n'
                    response += f"END LIST VAR {ups_name}\n"
                else:
                    response = "ERR UNKNOWN-UPS\n"
            else:
                response = "ERR SYNTAX-ERROR\n"

        elif command.startswith("LOGIN"):
            response = "OK\n"

        elif command.startswith("SET VAR"):
            parts = raw_data.decode("utf-8").strip().split()
            if len(parts) >= 5 and parts[3] == "=":
                ups_name = parts[2]
                var_name = parts[4]
                var_value = " ".join(parts[6:])
                if ups_name in UPS_DATA and var_name in UPS_DATA[ups_name]:
                    UPS_DATA[ups_name][var_name] = var_value
                    response = "OK\n"
                else:
                    response = "ERR UNKNOWN-UPS-OR-VAR\n"
            else:
                response = "ERR SYNTAX-ERROR\n"

        else:
            response = "ERR UNKNOWN-COMMAND\n"

        conn.sendall(response.encode("utf-8"))

    except Exception:
        pass
    finally:
        conn.close()


def main():
    updater_thread = threading.Thread(target=update_dynamic_values, daemon=True)
    updater_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((HOST, PORT))
        except OSError as e:
            print(f"FATAL: Could not bind to port {PORT}. Is another service running? Error: {e}")
            return

        server_socket.listen()
        print(f"NUT server simulator listening on {HOST}:{PORT}")

        while True:
            try:
                conn, addr = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                client_thread.start()
            except KeyboardInterrupt:
                print("\nServer shutting down.")
                break


if __name__ == "__main__":
    main()
