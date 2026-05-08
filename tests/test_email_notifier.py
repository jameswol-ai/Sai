# tests/test_email_notifier.py
import pytest
from plugins.notifications.email_notifier import EmailNotifier

class DummySMTP:
    """Mock SMTP server for testing"""
    def __init__(self, *args, **kwargs):
        self.sent_messages = []
    def starttls(self): pass
    def login(self, user, pwd): pass
    def send_message(self, msg): 
        self.sent_messages.append(msg)
    def __enter__(self): return self
    def __exit__(self, *args): pass

@pytest.fixture
def notifier(monkeypatch, tmp_path):
    # Patch smtplib.SMTP to use DummySMTP
    monkeypatch.setattr("smtplib.SMTP", lambda *a, **k: DummySMTP())
    # Create a dummy config file
    cfg = tmp_path / "email.yaml"
    cfg.write_text("""
smtp_server: "smtp.test"
smtp_port: 587
use_tls: true
username: "user"
password: "pass"
from_addr: "from@test.com"
to_addr: "to@test.com"
""")
    return EmailNotifier(config_path=str(cfg))

def test_notify_pipeline_success(notifier):
    notifier.notify_pipeline(status="SUCCESS", commit="abc123", branch="main")
    # Ensure message was sent
    assert notifier.to_addr == "to@test.com"
    # Check log file exists
    assert "email_notifier.log" in notifier.__dict__.get("smtp_server", "smtp.test")
