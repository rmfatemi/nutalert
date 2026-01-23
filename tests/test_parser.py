import pytest
from unittest.mock import patch, MagicMock

from nutalert.parser import parse_nut_data


class TestParseNutData:
    def test_parse_single_ups(self):
        raw_data = '''BEGIN LIST VAR ups
VAR ups battery.charge "100"
VAR ups ups.load "15"
VAR ups ups.status "OL"
VAR ups input.voltage "120.5"
VAR ups battery.runtime "3600"
END LIST VAR ups'''
        
        result = parse_nut_data(raw_data)
        
        assert "ups" in result
        assert result["ups"]["battery.charge"] == 100
        assert result["ups"]["ups.load"] == 15
        assert result["ups"]["ups.status"] == "OL"
        assert result["ups"]["input.voltage"] == 120.5
        assert result["ups"]["battery.runtime"] == 3600

    def test_parse_multiple_ups(self):
        raw_data = '''VAR apc battery.charge "100"
VAR apc ups.load "20"
VAR cyberpower battery.charge "95"
VAR cyberpower ups.load "30"'''
        
        result = parse_nut_data(raw_data)
        
        assert "apc" in result
        assert "cyberpower" in result
        assert result["apc"]["battery.charge"] == 100
        assert result["apc"]["ups.load"] == 20
        assert result["cyberpower"]["battery.charge"] == 95
        assert result["cyberpower"]["ups.load"] == 30

    def test_parse_string_values(self):
        raw_data = '''VAR ups device.model "Back-UPS RS 1350MS"
VAR ups ups.status "OL"'''
        
        result = parse_nut_data(raw_data)
        
        assert result["ups"]["device.model"] == "Back-UPS RS 1350MS"
        assert result["ups"]["ups.status"] == "OL"

    def test_parse_float_values(self):
        raw_data = '''VAR ups input.voltage "120.5"
VAR ups battery.voltage "27.3"'''
        
        result = parse_nut_data(raw_data)
        
        assert result["ups"]["input.voltage"] == 120.5
        assert result["ups"]["battery.voltage"] == 27.3

    def test_parse_empty_data(self):
        result = parse_nut_data("")
        assert result == {}

    def test_parse_invalid_lines(self):
        raw_data = '''not a valid line
VAR ups battery.charge "100"
another invalid line'''
        
        result = parse_nut_data(raw_data)
        
        assert "ups" in result
        assert result["ups"]["battery.charge"] == 100
        assert len(result["ups"]) == 1
