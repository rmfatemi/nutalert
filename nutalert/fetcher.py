import socket

from nutalert.utils import setup_logger


logger = setup_logger("nutalert")


def fetch_nut_data(host, port, command, timeout=2):
    raw_nut_data = ""
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(command.encode())
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                raw_nut_data += chunk.decode("utf-8", errors="replace")
    except socket.error as e:
        logger.error(f"socket error when contacting nut server: {e}")
    return raw_nut_data
