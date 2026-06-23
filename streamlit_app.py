import streamlit as st
import threading
import time
import csv
import os
import random
from datetime import datetime

# ---------------------------------------------------------
# Minimal TradingBot (self-contained)
# ---------------------------------------------------------
class TradingBot:
    def __init__(self):
        self.position = 0
        self.balance = 1000

    def get_price(self):
        return round(100 + random.uniform(-1, 1), 4)

    def step(self, price):
        action = random.choice(["BUY", "SELL", "HOLD"])
        trade = None

        if action == "BUY":
            self.position += 1
            self.balance -= price
            trade = price
        elif action == "SELL" and self.position > 0:
            self.position -= 1
            self.balance += price
            trade = price

        return action, trade


# ---------------------------------------------------------
# Metrics tracker (thread-safe)
# ---------------------------------------------------------
class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.prices = []
        self.actions = []
        self.trades = []
        self.balance = 1000
        self.pnl = 0

    def update(self, price, action, trade, bot):
        with self._lock:
            self.prices.append(price)
            self.actions.append(action)
            self.trades.append(trade)
            self.balance = bot.balance
            self.pnl = bot.balance - 1000

    def snapshot(self):
        with self._lock:
            return {
                "last_price": self.prices[-1] if self.prices else None,
                "last_action": self.actions[-1] if self.actions else None,
                "balance": self.balance,
                "pnl": self.pnl,
                "prices": list(self.prices),
            }


# ---------------------------------------------------------
# CSV Exporter (thread-safe)
# ---------------------------------------------------------
class CSVExporter:
    def __init__(self, filename="trades.csv"):
        self.filename = filename
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.filename):
            with open(self.filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "price", "action", "trade", "balance", "pnl"])

    def write_row(self, row):
        with self._lock:
            with open(self.filename, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    row["timestamp"],
                    row["price"],
                    row["action"],
                    row["trade"],
                    row["balance"],
                    row["pnl"],
                ])


# ---------------------------------------------------------
# Core Loop (background thread)
# ---------------------------------------------------------
class CoreLoop:
    def __init__(self, bot, metrics, csv_exporter, sleep_time=1.0):
        self.bot = bot
        self.metrics = metrics
        self.csv_exporter = csv_exporter
        self.sleep_time = sleep_time
        self.running = False

    def start(self):
        self.running = True
        while self.running:
            try:
                price = self.bot.get_price()
                action, trade = self.bot.step(price)

                self.metrics.update(price, action, trade, self.bot)

                self.csv_exporter.write_row({
                    "timestamp": datetime.utcnow().isoformat(),
                    "price": price,
                    "action": action,
                    "trade": trade,
                    "balance": self.metrics.balance,
                    "pnl": self.metrics.pnl,
                })

                time.sleep(self.sleep_time)

            except Exception as e:
                print("Loop error:", e)
                time.sleep(1)

    def stop(self):
        self.running = False


# ---------------------------------------------------------
# Streamlit UI Setup
# ---------------------------------------------------------
st.set_page_config(page_title="SAI Trading Dashboard", layout="wide")
st.title("SAI Trading Dashboard (Standalone Multi‑Tab Version)")

if "bot" not in st.session_state:
    st.session_state.bot = TradingBot()
if "metrics" not in st.session_state:
    st.session_state.metrics = Metrics()
if "csv" not in st.session_state:
    st.session_state.csv = CSVExporter()
if "loop" not in st.session_state:
    st.session_state.loop = None

def update_ui_from_metrics():
    snap = st.session_state.metrics.snapshot()
    st.session_state.last_price = snap["last_price"]
    st.session_state.last_action = snap["last_action"]
    st.session_state.balance = snap["balance"]
    st.session_state.pnl = snap["pnl"]
    st.session_state._prices_for_chart = snap["prices"]

# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------
tab_dashboard, tab_strategy, tab_logs, tab_debug = st.tabs(
    ["📊 Dashboard", "🧠 Strategy", "📜 Logs", "🛠 Debug"]
)

# ---------------------------------------------------------
# Dashboard Tab
# ---------------------------------------------------------
with tab_dashboard:
    st.subheader("Live Trading Controls")

    col1, col2, col3 = st.columns([1, 1, 1])

    if col1.button("Start Trading"):
        if st.session_state.loop is None or not st.session_state.loop.running:
            st.session_state.loop = CoreLoop(
                st.session_state.bot,
                st.session_state.metrics,
                st.session_state.csv,
                sleep_time=1.0
            )
            threading.Thread(
                target=st.session_state.loop.start,
                daemon=True
            ).start()

    if col2.button("Stop Trading"):
        if st.session_state.loop:
            st.session_state.loop.stop()

    auto_refresh = col3.checkbox("Auto-refresh UI (disabled)", value=False)
    refresh_interval = col3.number_input(
        "Refresh interval (s)", min_value=0.5, max_value=10.0, value=1.0, step=0.5
    )

    update_ui_from_metrics()

    st.subheader("Live Metrics")
    st.metric("Last Price", st.session_state.get("last_price", "—"))
    st.metric("Last Action", st.session_state.get("last_action", "—"))
    st.metric("Balance", st.session_state.get("balance", "—"))
    st.metric("PnL", st.session_state.get("pnl", "—"))

    st.subheader("Price Chart")
    prices_for_chart = st.session_state.get("_prices_for_chart", [])
    st.line_chart(prices_for_chart)

    # Manual refresh button
    if st.button("Refresh Now"):
        update_ui_from_metrics()
        st.experimental_rerun()

# ---------------------------------------------------------
# Strategy Tab
# ---------------------------------------------------------
with tab_strategy:
    st.subheader("Strategy Configuration (Placeholder)")
    st.write("This tab will later support strategy plugins, parameters, and model selection over time.")
    st.text_area("Strategy Notes", placeholder="Describe or configure your strategy here...")

# ---------------------------------------------------------
# Logs Tab
# ---------------------------------------------------------
with tab_logs:
    st.subheader("CSV Log Preview")

    if os.path.exists(st.session_state.csv.filename):
        with open(st.session_state.csv.filename, "rb") as f:
            data = f.read()
            st.download_button("Download trades.csv", data, file_name="trades.csv")

        st.write("Latest 20 rows:")
        with open(st.session_state.csv.filename, "r", newline="") as f:
            rows = list(csv.reader(f))
            header = rows[0] if rows else []
            body = rows[-20:] if len(rows) > 1 else []
            if header:
                st.table([header] + body)
            else:
                st.write("No rows yet.")
    else:
        st.write("No logs yet.")

# ---------------------------------------------------------
# Debug Tab
# ---------------------------------------------------------
with tab_debug:
    st.subheader("Debug Info")
    st.json({
        "loop_running": bool(st.session_state.loop.running) if st.session_state.loop else False,
        "last_price": st.session_state.get("last_price"),
        "last_action": st.session_state.get("last_action"),
        "balance": st.session_state.get("balance"),
        "pnl": st.session_state.get("pnl"),
        "total_prices": len(st.session_state.metrics.prices),
    })
currency_choice = st.selectbox(
    "Select Currency",
    options=list(CURRENCIES.keys()),
    index=0
)
st.session_state.bot.currency = currency_choice

st.metric("Balance (USD)", snap["balance_usd"])
st.metric(f"Balance ({snap['currency']})", f"{CURRENCIES[snap['currency']]['symbol']} {snap['balance_local']}")

