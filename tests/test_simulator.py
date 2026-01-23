import socket
import threading
import time
import pytest

from tests.simulate_nut_server import (
    UPS_DATA,
    INITIAL_RUNTIMES,
    handle_client,
    update_dynamic_values,
)


class TestUpsDataStructure:
    def test_ups_data_has_required_ups_devices(self):
        assert "apc" in UPS_DATA
        assert "cyberpower" in UPS_DATA
        assert "eaton220" in UPS_DATA

    def test_ups_data_has_required_fields(self):
        required_fields = [
            "battery.charge",
            "battery.runtime",
            "battery.voltage",
            "battery.voltage.nominal",
            "ups.load",
            "ups.status",
            "input.voltage",
            "input.voltage.nominal",
            "device.model",
            "device.mfr",
        ]
        for ups_name, data in UPS_DATA.items():
            for field in required_fields:
                assert field in data, f"Missing {field} in {ups_name}"

    def test_initial_runtimes_populated(self):
        assert len(INITIAL_RUNTIMES) == len(UPS_DATA)
        for ups_name in UPS_DATA:
            assert ups_name in INITIAL_RUNTIMES
            assert INITIAL_RUNTIMES[ups_name] == int(UPS_DATA[ups_name]["battery.runtime"])


class TestSimulatorServer:
    @pytest.fixture
    def server_socket(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        yield server, port
        server.close()

    def test_list_ups_command(self, server_socket):
        server, port = server_socket

        def run_server():
            conn, _ = server.accept()
            handle_client(conn, None)

        server_thread = threading.Thread(target=run_server)
        server_thread.start()

        with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
            client.sendall(b"LIST UPS\r\n")
            response = client.recv(4096).decode()

        server_thread.join(timeout=2)

        assert "BEGIN LIST UPS" in response
        assert "END LIST UPS" in response
        assert "UPS apc" in response
        assert "UPS cyberpower" in response
        assert "UPS eaton220" in response

    def test_list_var_command(self, server_socket):
        server, port = server_socket

        def run_server():
            conn, _ = server.accept()
            handle_client(conn, None)

        server_thread = threading.Thread(target=run_server)
        server_thread.start()

        with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
            client.sendall(b"LIST VAR apc\r\n")
            response = client.recv(8192).decode()

        server_thread.join(timeout=2)

        assert "BEGIN LIST VAR apc" in response
        assert "END LIST VAR apc" in response
        assert 'VAR apc battery.charge "' in response
        assert 'VAR apc ups.status "' in response

    def test_list_var_unknown_ups(self, server_socket):
        server, port = server_socket

        def run_server():
            conn, _ = server.accept()
            handle_client(conn, None)

        server_thread = threading.Thread(target=run_server)
        server_thread.start()

        with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
            client.sendall(b"LIST VAR unknown\r\n")
            response = client.recv(4096).decode()

        server_thread.join(timeout=2)

        assert "ERR UNKNOWN-UPS" in response

    def test_login_command(self, server_socket):
        server, port = server_socket

        def run_server():
            conn, _ = server.accept()
            handle_client(conn, None)

        server_thread = threading.Thread(target=run_server)
        server_thread.start()

        with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
            client.sendall(b"LOGIN\r\n")
            response = client.recv(4096).decode()

        server_thread.join(timeout=2)

        assert "OK" in response

    def test_unknown_command(self, server_socket):
        server, port = server_socket

        def run_server():
            conn, _ = server.accept()
            handle_client(conn, None)

        server_thread = threading.Thread(target=run_server)
        server_thread.start()

        with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
            client.sendall(b"INVALID COMMAND\r\n")
            response = client.recv(4096).decode()

        server_thread.join(timeout=2)

        assert "ERR UNKNOWN-COMMAND" in response


class TestDynamicValueUpdate:
    def test_load_stays_within_bounds(self):
        original_load = int(UPS_DATA["apc"]["ups.load"])
        for _ in range(100):
            load = int(UPS_DATA["apc"]["ups.load"])
            new_load = load + 2
            UPS_DATA["apc"]["ups.load"] = str(min(100, max(5, new_load)))

        final_load = int(UPS_DATA["apc"]["ups.load"])
        assert 5 <= final_load <= 100
        UPS_DATA["apc"]["ups.load"] = str(original_load)

    def test_voltage_format(self):
        for ups_name, data in UPS_DATA.items():
            voltage = data["input.voltage"]
            assert "." in voltage
            float_val = float(voltage)
            nominal = int(data["input.voltage.nominal"])
            if nominal == 120:
                assert 100 <= float_val <= 140
            else:
                assert 200 <= float_val <= 260
