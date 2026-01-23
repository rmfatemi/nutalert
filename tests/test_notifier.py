import pytest
from unittest.mock import patch, MagicMock

from nutalert.notifier import NutAlertNotifier


class TestNutAlertNotifier:
    def test_init(self):
        config = {"notifications": {"urls": []}}
        notifier = NutAlertNotifier(config)
        
        assert notifier.config == config

    @patch("nutalert.notifier.apprise.Apprise")
    def test_notify_apprise_with_string_urls(self, mock_apprise_class):
        mock_apprise = MagicMock()
        mock_apprise.servers = [MagicMock()]
        mock_apprise_class.return_value = mock_apprise
        
        config = {
            "notifications": {
                "urls": ["mailto://user@example.com", "slack://token"]
            }
        }
        notifier = NutAlertNotifier(config)
        
        success, error_msg = notifier.notify_apprise("Test Title", "Test Message")
        
        assert mock_apprise.add.call_count == 2
        mock_apprise.notify.assert_called_once()
        assert success is True
        assert error_msg == ""

    @patch("nutalert.notifier.apprise.Apprise")
    def test_notify_apprise_with_dict_urls(self, mock_apprise_class):
        mock_apprise = MagicMock()
        mock_apprise.servers = [MagicMock()]
        mock_apprise_class.return_value = mock_apprise
        
        config = {
            "notifications": {
                "urls": [
                    {"url": "mailto://user@example.com", "enabled": True},
                    {"url": "slack://token", "enabled": False},
                ]
            }
        }
        notifier = NutAlertNotifier(config)
        
        success, error_msg = notifier.notify_apprise("Test Title", "Test Message")
        
        mock_apprise.add.assert_called_once_with("mailto://user@example.com")
        mock_apprise.notify.assert_called_once()

    @patch("nutalert.notifier.apprise.Apprise")
    def test_notify_apprise_no_urls(self, mock_apprise_class):
        config = {"notifications": {"urls": []}}
        notifier = NutAlertNotifier(config)
        
        success, error_msg = notifier.notify_apprise("Test Title", "Test Message")
        
        assert success is False
        assert "no apprise urls configured" in error_msg

    @patch("nutalert.notifier.apprise.Apprise")
    def test_notify_apprise_no_valid_servers(self, mock_apprise_class):
        mock_apprise = MagicMock()
        mock_apprise.servers = []
        mock_apprise_class.return_value = mock_apprise
        
        config = {
            "notifications": {
                "urls": [{"url": "invalid://url", "enabled": True}]
            }
        }
        notifier = NutAlertNotifier(config)
        
        success, error_msg = notifier.notify_apprise("Test Title", "Test Message")
        
        assert success is False
        assert "no enabled apprise urls found" in error_msg

    @patch("nutalert.notifier.apprise.Apprise")
    def test_notify_apprise_exception(self, mock_apprise_class):
        mock_apprise = MagicMock()
        mock_apprise.servers = [MagicMock()]
        mock_apprise.notify.side_effect = Exception("Network error")
        mock_apprise_class.return_value = mock_apprise
        
        config = {"notifications": {"urls": ["mailto://user@example.com"]}}
        notifier = NutAlertNotifier(config)
        
        success, error_msg = notifier.notify_apprise("Test Title", "Test Message")
        
        assert success is False
        assert "Network error" in error_msg

    @patch("nutalert.notifier.apprise.Apprise")
    def test_notify_apprise_truncates_long_message(self, mock_apprise_class):
        mock_apprise = MagicMock()
        mock_apprise.servers = [MagicMock()]
        mock_apprise_class.return_value = mock_apprise
        
        config = {"notifications": {"urls": ["mailto://user@example.com"]}}
        notifier = NutAlertNotifier(config)
        
        long_message = "x" * 2500
        success, error_msg = notifier.notify_apprise("Test Title", long_message)
        
        call_args = mock_apprise.notify.call_args
        body = call_args[1]["body"]
        assert len(body) <= 1950
        assert "shortened" in body

    def test_send_all_notifications_disabled(self):
        config = {"notifications": {"enabled": False, "urls": ["test://url"]}}
        notifier = NutAlertNotifier(config)
        
        with patch.object(notifier, "notify_apprise") as mock_notify:
            notifier.send_all("Title", "Message")
            mock_notify.assert_not_called()

    @patch("nutalert.notifier.apprise.Apprise")
    def test_send_all_notifications_enabled(self, mock_apprise_class):
        mock_apprise = MagicMock()
        mock_apprise.servers = [MagicMock()]
        mock_apprise.notify.return_value = True
        mock_apprise_class.return_value = mock_apprise
        
        config = {
            "notifications": {
                "enabled": True,
                "urls": ["mailto://user@example.com"],
            }
        }
        notifier = NutAlertNotifier(config)
        
        result = notifier.send_all("Title", "Message")
        
        mock_apprise.notify.assert_called_once()
        assert result is True

    @patch("nutalert.notifier.apprise.Apprise")
    def test_notify_apprise_delivery_failure(self, mock_apprise_class):
        mock_apprise = MagicMock()
        mock_apprise.servers = [MagicMock()]
        mock_apprise.notify.return_value = False
        mock_apprise_class.return_value = mock_apprise
        
        config = {"notifications": {"urls": ["mailto://user@example.com"]}}
        notifier = NutAlertNotifier(config)
        
        success, error_msg = notifier.notify_apprise("Test Title", "Test Message")
        
        assert success is False
        assert "delivery failed" in error_msg
