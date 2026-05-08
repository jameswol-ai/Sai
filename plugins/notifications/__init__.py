# plugins/notifications/__init__.py
"""
Notifications Package
---------------------
Provides modular notification integrations for:
- Email
- SMS
- Slack
- Telegram
- Webhooks
- Mock (for testing)

Usage:
    from plugins.notifications import email_notifier, slack_notifier
    email_notifier.send_message("Trade executed successfully")
"""

from . import base_notifier
from . import email_notifier
from . import sms_notifier
from . import slack_notifier
from . import telegram_notifier
from . import webhook_notifier
from . import mock_notifier
from . import utils

__all__ = [
    "base_notifier",
    "email_notifier",
    "sms_notifier",
    "slack_notifier",
    "telegram_notifier",
    "webhook_notifier",
    "mock_notifier",
    "utils",
]
