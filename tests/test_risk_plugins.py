import pytest
from streamlit_app import StopLossPlugin, MaxDrawdownPlugin, PositionSizePlugin, EmailNotifier

def test_stop_loss_plugin():
    plugin = StopLossPlugin(threshold=0.05)
    assert plugin.check({"action": "SELL"}, balance=1000.0) is True

def test_max_drawdown_plugin():
    plugin = MaxDrawdownPlugin(max_drawdown=0.20)
    assert plugin.check({"action": "BUY"}, balance=800.0) is True

def test_position_size_plugin():
    plugin = PositionSizePlugin(max_fraction=0.10)
    assert plugin.check({"action": "BUY"}, balance=1000.0) is True

def test_email_notifier_logs(caplog):
    notifier = EmailNotifier()
    with caplog.at_level("INFO"):
        notifier.notify_pipeline("SUCCESS", "abc123", "main")
    assert "EmailNotifier: SUCCESS abc123 main" in caplog.text
