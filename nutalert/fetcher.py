import socket
import select

from nutalert.utils import setup_logger


logger = setup_logger(__name__)


def fetch_nut_ups_names(host, port, timeout=2):
    command = "list ups\r\n"
    ups_names = []
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(command.encode())
            raw = ""
            while True:
                ready, _, _ = select.select([sock], [], [], timeout)
                if not ready:
                    break
                chunk = sock.recv(4096)
                if not chunk:
                    break
                raw += chunk.decode("utf-8", errors="replace")
            for line in raw.splitlines():
                if line.startswith("UPS "):
                    parts = line.split()
                    if len(parts) >= 2:
                        ups_names.append(parts[1])
    except socket.error as e:
        logger.error(f"socket error when contacting nut server: {e}")
    return ups_names


def fetch_nut_data(host, port, ups_name, timeout=2):
    command = f"list var {ups_name}\r\n"
    raw_nut_data = ""
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(command.encode())
            while True:
                ready, _, _ = select.select([sock], [], [], timeout)
                if not ready:
                    break
                chunk = sock.recv(4096)
                if not chunk:
                    break
                raw_nut_data += chunk.decode("utf-8", errors="replace")
    except socket.error as e:
        logger.error(f"socket error when contacting nut server: {e}")
    return raw_nut_data
