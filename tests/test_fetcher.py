import pytest
from unittest.mock import patch, MagicMock

from nutalert.fetcher import fetch_nut_ups_names, fetch_nut_data


class TestFetchNutUpsNames:
    @patch("nutalert.fetcher.socket.create_connection")
    @patch("nutalert.fetcher.select.select")
    def test_fetch_ups_names_success(self, mock_select, mock_connection):
        mock_sock = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_sock
        mock_select.return_value = ([mock_sock], [], [])
        
        mock_sock.recv.side_effect = [
            b'BEGIN LIST UPS\nUPS apc "APC UPS"\nUPS cyberpower "CyberPower"\nEND LIST UPS\n',
            b"",
        ]
        
        result = fetch_nut_ups_names("localhost", 3493)
        
        assert result == ["apc", "cyberpower"]
        mock_sock.sendall.assert_called_once_with(b"list ups\r\n")

    @patch("nutalert.fetcher.socket.create_connection")
    def test_fetch_ups_names_connection_error(self, mock_connection):
        mock_connection.side_effect = OSError("Connection refused")
        
        result = fetch_nut_ups_names("localhost", 3493)
        
        assert result == []

    @patch("nutalert.fetcher.socket.create_connection")
    @patch("nutalert.fetcher.select.select")
    def test_fetch_ups_names_empty_response(self, mock_select, mock_connection):
        mock_sock = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_sock
        mock_select.return_value = ([], [], [])
        
        result = fetch_nut_ups_names("localhost", 3493)
        
        assert result == []


class TestFetchNutData:
    @patch("nutalert.fetcher.socket.create_connection")
    @patch("nutalert.fetcher.select.select")
    def test_fetch_nut_data_success(self, mock_select, mock_connection):
        mock_sock = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_sock
        mock_select.return_value = ([mock_sock], [], [])
        
        mock_sock.recv.side_effect = [
            b'BEGIN LIST VAR ups\nVAR ups battery.charge "100"\nEND LIST VAR ups\n',
            b"",
        ]
        
        result = fetch_nut_data("localhost", 3493, "ups")
        
        assert 'VAR ups battery.charge "100"' in result
        mock_sock.sendall.assert_called_once_with(b"list var ups\r\n")

    @patch("nutalert.fetcher.socket.create_connection")
    def test_fetch_nut_data_connection_error(self, mock_connection):
        mock_connection.side_effect = OSError("Connection refused")
        
        result = fetch_nut_data("localhost", 3493, "ups")
        
        assert result == ""

    @patch("nutalert.fetcher.socket.create_connection")
    @patch("nutalert.fetcher.select.select")
    def test_fetch_nut_data_timeout(self, mock_select, mock_connection):
        mock_sock = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_sock
        mock_select.return_value = ([], [], [])
        
        result = fetch_nut_data("localhost", 3493, "ups")
        
        assert result == ""
