class NotifierPlugin:
    def __init__(self, name):
        self.name = name
        self.active = False

    def update(self, active):
        self.active = active

    def test_ping(self):
        # Replace with real notifier logic
        print(f"Test ping sent to {self.name}")

# Registry of notifier plugins
notifier_plugins = [
    NotifierPlugin("Email"),
    NotifierPlugin("Slack"),
]
