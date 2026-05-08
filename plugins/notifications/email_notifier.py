# plugins/notifications/email_notifier.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import yaml

class EmailNotifier:
    def __init__(self, config_path="plugins/notifications/configs/email.yaml"):
        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        self.smtp_server = cfg["smtp_server"]
        self.smtp_port = cfg["smtp_port"]
        self.use_tls = cfg.get("use_tls", True)
        self.username = cfg["username"]
        self.password = cfg["password"]
        self.from_addr = cfg["from_addr"]
        self.to_addr = cfg["to_addr"]

        logging.basicConfig(
            filename=cfg.get("log_file", "logs/email_notifier.log"),
            level=getattr(logging, cfg.get("log_level", "INFO"))
        )

    def _send(self, subject: str, body: str):
        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            logging.info(f"Email sent: {subject}")
        except Exception as e:
            logging.error(f"Failed to send email: {e}")

    def notify_pipeline(self, status: str, commit: str, branch: str):
        subject = f"SAI CI/CD Pipeline - {status}"
        body = f"""
        Pipeline Status: {status}
        Commit: {commit}
        Branch: {branch}
        """
        self._send(subject, body)
