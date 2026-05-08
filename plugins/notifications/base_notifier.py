# plugins/notifications/base_notifier.py
"""
Base Notifier
-------------
Defines the abstract interface for all notification plugins.
Each notifier (Email, SMS, Slack, Telegram, Webhook, Mock) must implement
these methods to ensure consistency across channels.
"""

from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    """
    Abstract base class for notification plugins.
    """

    @abstractmethod
    def send_message(self, message: str) -> None:
        """
        Send a generic message.
        Args:
            message (str): The message content to send.
        """
        pass

    @abstractmethod
    def send_alert(self, message: str) -> None:
        """
        Send an alert (e.g., trade execution, risk warning).
        Args:
            message (str): The alert content to send.
        """
        pass

    @abstractmethod
    def send_error(self, message: str) -> None:
        """
        Send an error notification.
        Args:
            message (str): The error details to send.
        """
        pass
