import re

from nutalert.utils import setup_logger


logger = setup_logger(__name__)


def parse_nut_data(raw_data):
    pattern = re.compile(r'^VAR\s+(\S+)\s+(\S+)\s+"([^"]+)"$')
    nut_values = {}
    for line in raw_data.splitlines():
        m = pattern.match(line.strip())
        if m:
            ups_name, key, value = m.groups()
            if ups_name not in nut_values:
                nut_values[ups_name] = {}
            try:
                nut_values[ups_name][key] = int(value)
            except ValueError:
                try:
                    nut_values[ups_name][key] = float(value)
                except ValueError:
                    nut_values[ups_name][key] = value.strip()
    return nut_values
