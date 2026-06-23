from .slack_notifier import SlackNotifier
from .email_notifier import EmailNotifier

# Example instances (configure with your secrets)
slack_notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/XXX/YYY/ZZZ")
email_notifier = EmailNotifier(
    smtp_server="smtp.example.com",
    from_addr="bot@example.com",
    to_addr="alerts@example.com"
)

notifier_plugins = [slack_notifier, email_notifier]
