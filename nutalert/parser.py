import re

from nutalert.utils import setup_logger


logger = setup_logger(__name__)


def parse_nut_data(raw_data):
    pattern = re.compile(r'^VAR ups\s+([^ ]+)\s+"([^"]+)"$')
    nut_values = {}
    for line in raw_data.splitlines():
        m = pattern.match(line.strip())
        if m:
            key, value = m.groups()
            try:
                nut_values[key] = int(value)
            except ValueError:
                try:
                    nut_values[key] = float(value)
                except ValueError:
                    nut_values[key] = value.strip()
    return nut_values
