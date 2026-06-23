import streamlit as st
import threading
import time
import csv
import os
import random
import requests
from datetime import datetime

# ---------------------------------------------------------
# Currency Map (East Africa + USD)
# ---------------------------------------------------------
CURRENCIES = {
    "USD": {"symbol": "$"},
    "SSP": {"symbol": "£"},
    "UGX": {"symbol": "USh"},
    "KES": {"symbol": "KSh"},
    "TZS": {"symbol": "TSh"},
    "RWF": {"symbol": "FRw"},
}

def get_fx_rate(base="USD", target="SSP"):
    try:
        url = f"https://api.exchangerate.host/latest?base={base}&symbols={target}"
        resp = requests.get(url).json()
        return resp["rates"][target]
    except Exception:
        return None

# ---------------------------------------------------------
# TradingBot
# ---------------------------------------------------------
class TradingBot:
    def __init__(self, currency="USD"):
        self.currency = currency
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

    def convert_balance(self, fx_rates):
        rate = fx_rates.get(self.currency, 1.0)
        return round(self.balance * rate, 2)

# ---------------------------------------------------------
# Metrics
# ---------------------------------------------------------
class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.prices, self.actions, self.trades = [], [], []
        self.balance, self.pnl = 1000, 0
        self.balance_local, self.pnl_local = 1000, 0

    def update(self, price, action, trade, bot, fx_rates):
        with self._lock:
            self.prices.append(price)
            self.actions.append(action)
            self.trades.append(trade)
            self.balance = bot.balance
            self.pnl = bot.balance - 1000
            self.balance_local = bot.convert_balance(fx_rates)
            self.pnl_local = self.balance_local - (1000 * fx_rates.get(bot.currency, 1.0))

    def snapshot(self, bot):
        with self._lock:
            return {
                "last_price": self.prices[-1] if self.prices else None,
                "last_action": self.actions[-1] if self.actions else None,
                "balance_usd": self.balance,
                "balance_local": getattr(self, "balance_local", bot.convert_balance(st.session_state.fx_rates)),
                "currency": bot.currency,
                "pnl_usd": self.pnl,
                "pnl_local": getattr(self, "pnl_local", 0),
                "prices": list(self.prices),
            }

# ---------------------------------------------------------
# CSV Exporter
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
                writer.writerow([
                    "timestamp","price","action","trade",
                    "balance_usd","balance_local","currency",
                    "pnl_usd","pnl_local"
                ])

    def write_row(self, row):
        with self._lock:
            with open(self.filename, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    row["timestamp"], row["price"], row["action"], row["trade"],
                    row["balance_usd"], row["balance_local"], row["currency"],
                    row["pnl_usd"], row["pnl_local"]
                ])

# ---------------------------------------------------------
# Risk Plugin
# ---------------------------------------------------------
class RiskPlugin:
    def __init__(self, max_exposure_usd=5000):
        self.max_exposure_usd = max_exposure_usd

    def check(self, bot):
        if bot.balance > self.max_exposure_usd:
            return False, "Exposure limit exceeded"
        return True, None

# ---------------------------------------------------------
# Core Loop
# ---------------------------------------------------------
class CoreLoop:
    def __init__(self, bot, metrics, csv_exporter, risk_plugin, sleep_time=1.0):
        self.bot, self.metrics, self.csv_exporter, self.risk_plugin = bot, metrics, csv_exporter, risk_plugin
        self.sleep_time, self.running = sleep_time, False

    def start(self):
        self.running = True
        while self.running:
            try:
                price = self.bot.get_price()
                ok, msg = self.risk_plugin.check(self.bot)
                if not ok:
                    print("Risk blocked trade:", msg)
                    time.sleep(self.sleep_time)
                    continue

                action, trade = self.bot.step(price)
                self.metrics.update(price, action, trade, self.bot, st.session_state.fx_rates)

                snap = self.metrics.snapshot(self.bot)
                self.csv_exporter.write_row({
                    "timestamp": datetime.utcnow().isoformat(),
                    "price": price,
                    "action": action,
                    "trade": trade,
                    "balance_usd": snap["balance_usd"],
                    "balance_local": snap["balance_local"],
                    "currency": snap["currency"],
                    "pnl_usd": snap["pnl_usd"],
                    "pnl_local": snap["pnl_local"],
                })
                time.sleep(self.sleep_time)
            except Exception as e:
                print("Loop error:", e)
                time.sleep(1)

    def stop(self):
        self.running = False

# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------
st.set_page_config(page_title="SAI Trading Dashboard", layout="wide")
st.title("SAI Trading Dashboard (Multi‑Currency)")

if "bot" not in st.session_state:
    st.session_state.bot = TradingBot()
if "metrics" not in st.session_state:
    st.session_state.metrics = Metrics()
if "csv" not in st.session_state:
    st.session_state.csv = CSVExporter()
if "risk_plugin" not in st.session_state:
    st.session_state.risk_plugin = RiskPlugin()
if "fx_rates" not in st.session_state:
    st.session_state.fx_rates = {c: 1.0 for c in CURRENCIES.keys()}
if "loop" not in st.session_state:
    st.session_state.loop = None

# Tabs
tab_dashboard, tab_strategy, tab_logs, tab_debug = st.tabs(
    ["📊 Dashboard", "🧠 Strategy", "📜 Logs", "🛠 Debug"]
)

# Dashboard
with tab_dashboard:
    st.subheader("Live Trading Controls")
    col1, col2, col3 = st.columns([1,1,1])

    if col1.button("Start Trading"):
        if st.session_state.loop is None or not st.session_state.loop.running:
            st.session_state.loop = CoreLoop(
                st.session_state.bot,
                st.session_state.metrics,
                st.session_state.csv,
                st.session_state.risk_plugin,
                sleep_time=1.0
            )
            threading.Thread(target=st.session_state.loop.start, daemon=True).start()

    if col2.button("Stop Trading"):
        if st.session_state.loop:
            st.session_state.loop.stop()

    currency_choice = col3.selectbox("Select Currency", list(CURRENCIES.keys()))
    st.session_state.bot.currency = currency_choice

    if col3.button("Update FX Rates"):
        st.session_state.fx_rates = {
            c: get_fx_rate("USD", c) or 1.0 for c in CURRENCIES.keys()
        }

    snap = st.session_state.metrics.snapshot(st.session_state.bot)
    st.subheader("Live Metrics")
    st.metric("Last Price", snap["last_price"])
    st.metric("Last Action", snap["last_action"])
    st.metric("Balance (USD)", snap["balance_usd"])
    st.metric(f"Balance ({snap['currency']})", f"{CURRENCIES[snap['currency']]['symbol']} {snap['balance_local']}")
    st.metric("PnL (USD)", snap["pnl_usd"])
    st.metric(f"PnL ({snap['currency']})", f"{CURRENCIES[snap['currency']]['symbol']} {snap['pnl_local']}")

    st.subheader("Price Chart")
    st.line_chart(snap["prices"])

# Strategy
with tab_strategy:
    st.subheader("Strategy Configuration (Placeholder)")
    st.text_area("Strategy Notes", placeholder="Describe or configure your strategy here...")

# Logs
with tab_logs:
    st.subheader("CSV Log Preview")
    if os.path.exists(st.session_state.csv.filename):
        with open(st.session_state.csv.filename, "rb") as f:
            data = f.read()
            st.download_button(
                label="Download trades.csv",
                data=data,
                file_name="trades.csv",
                mime="text/csv"
            )

        with open(st.session_state.csv.filename, "r", newline="") as f:
            rows = list(csv
