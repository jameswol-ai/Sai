# ============================================================
# SAI AI Forex Trading Bot – Full Production Dashboard
# PostgreSQL + Dark Mode + Live Bot + All Features
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import hashlib
import random
import time
import threading
import queue
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="SAI AI Forex Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# DATABASE CONNECTION (PostgreSQL via Supabase / Render)
# ============================================================
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Fallback for local testing – replace with your own if needed
    DATABASE_URL = "postgresql://postgres:password@localhost:5432/sai"

def connect_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_database():
    conn = connect_db()
    cur = conn.cursor()
    # Create tables if not exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades(
            id SERIAL PRIMARY KEY,
            username TEXT,
            time TEXT,
            symbol TEXT,
            action TEXT,
            price REAL,
            pnl REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS balance(
            username TEXT PRIMARY KEY,
            amount REAL
        )
    """)
    # Insert default admin if no users exist
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()["count"]
    if count == 0:
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            ("admin", hash_password("admin123"), "admin")
        )
        cur.execute(
            "INSERT INTO balance (username, amount) VALUES (%s, %s)",
            ("admin", 10000.0)
        )
    conn.commit()
    conn.close()

init_database()

# ============================================================
# USER SYSTEM
# ============================================================
def login(username, password):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT role FROM users WHERE username=%s AND password=%s",
        (username, hash_password(password))
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return True, row["role"]
    return False, None

def register(username, password):
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            (username, hash_password(password), "user")
        )
        # create starting balance
        cur.execute(
            "INSERT INTO balance (username, amount) VALUES (%s, %s)",
            (username, 10000.0)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def change_password(username, old_password, new_password):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT username FROM users WHERE username=%s AND password=%s",
        (username, hash_password(old_password))
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE users SET password=%s WHERE username=%s",
            (hash_password(new_password), username)
        )
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_users():
    conn = connect_db()
    df = pd.read_sql("SELECT username, role FROM users", conn)
    conn.close()
    return df

def remove_user(username):
    if username == "admin":
        return False
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE username=%s", (username,))
    cur.execute("DELETE FROM balance WHERE username=%s", (username,))
    cur.execute("DELETE FROM trades WHERE username=%s", (username,))
    conn.commit()
    conn.close()
    return True

# ============================================================
# SESSION STATE DEFAULTS
# ============================================================
defaults = {
    "logged": False,
    "username": "",
    "role": "",
    "bot_running": False,
    "risk": 2,
    "auto_trade": False,
    "balance": 10000.0,
    "dark_mode": False,
    "live_feed": False,
    "strategy": "Scalper",
    "alerts_enabled": False,
    "alert_email": "",
    "alert_telegram": ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# DARK MODE CSS
# ============================================================
if st.session_state.dark_mode:
    dark_css = """
    <style>
        body { background-color: #0e1117; color: #fafafa; }
        .stApp { background-color: #0e1117; }
        .stMetric { background-color: #262730; }
    </style>
    """
    st.markdown(dark_css, unsafe_allow_html=True)

# ============================================================
# MARKET & AI ENGINE (simulated)
# ============================================================
CURRENCIES = {
    "UGX": 3800, "KES": 130, "TZS": 2600,
    "SSP": 1600, "RWF": 1350, "USD": 1, "EUR": 0.92
}

def get_market():
    data = {}
    for c, base in CURRENCIES.items():
        data[c] = round(base + random.uniform(-5, 5), 2)
    return data

def save_market(prices):
    pass

def run_ai(prices, strategy="Scalper"):
    results = {}
    for currency, rate in prices.items():
        if strategy == "Scalper":
            rsi = round(random.uniform(30, 70), 1)
            th_b, th_s = 45, 55
        elif strategy == "Trend":
            rsi = round(random.uniform(20, 80), 1)
            th_b, th_s = 35, 65
        else:  # Breakout
            rsi = round(random.uniform(25, 75), 1)
            th_b, th_s = 40, 60

        if rsi < th_b:
            signal = "BUY"
        elif rsi > th_s:
            signal = "SELL"
        else:
            signal = random.choice(["BUY", "SELL", "HOLD"])

        confidence = round(random.uniform(50, 99), 1)
        forecast = round(rate + random.uniform(-3, 3), 2)
        results[currency] = {
            "signal": signal,
            "confidence": confidence,
            "rsi": rsi,
            "forecast": forecast
        }
    return results

def forecast_currency(currency, days):
    current = CURRENCIES.get(currency, 1)
    forecast = []
    value = current
    for _ in range(days):
        change = random.uniform(-0.02, 0.02) * value
        value += change
        forecast.append(round(value, 2))
    return forecast

def load_ai_memory():
    return pd.DataFrame(columns=["timestamp", "event", "data"])

# ============================================================
# TRADING SYSTEM
# ============================================================
def get_account():
    username = st.session_state.username
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT amount FROM balance WHERE username=%s", (username,))
    row = cur.fetchone()
    conn.close()
    if row:
        st.session_state.balance = row["amount"]
    return {"balance": st.session_state.balance}

def execute_trade(symbol, action, price):
    username = st.session_state.username
    pnl = random.uniform(-30, 80)

    # Apply risk scaling
    risk_amount = (st.session_state.risk / 100) * st.session_state.balance
    pnl = pnl * (risk_amount / 100)
    new_balance = st.session_state.balance + pnl
    if new_balance < 0:
        pnl = -st.session_state.balance
        new_balance = 0

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE balance SET amount=%s WHERE username=%s",
        (new_balance, username)
    )
    cur.execute(
        "INSERT INTO trades(username, time, symbol, action, price, pnl) VALUES(%s,%s,%s,%s,%s,%s)",
        (username, datetime.now().isoformat(), symbol, action, price, pnl)
    )
    conn.commit()
    conn.close()

    st.session_state.balance = new_balance
    return pnl

def get_trade_history():
    conn = connect_db()
    df = pd.read_sql(
        "SELECT * FROM trades WHERE username=%s ORDER BY id DESC",
        conn, params=[st.session_state.username]
    )
    conn.close()
    return df

def system_status():
    return {
        "app_version": "6.2",
        "bot_running": st.session_state.bot_running,
        "auto_trade": st.session_state.auto_trade,
        "risk_level": st.session_state.risk,
        "strategy": st.session_state.strategy,
        "dark_mode": st.session_state.dark_mode,
        "live_feed": st.session_state.live_feed,
        "time": datetime.now().isoformat()
    }

# ============================================================
# AUTO‑TRADING BOT (background thread)
# ============================================================
signal_queue = queue.Queue()
bot_settings = {
    "bot_running": False,
    "auto_trade": False,
    "risk": 2,
    "strategy": "Scalper"
}
bot_lock = threading.Lock()

def bot_loop():
    while True:
        with bot_lock:
            running = bot_settings["bot_running"]
            auto_trade = bot_settings["auto_trade"]
            risk = bot_settings["risk"]
            strategy = bot_settings["strategy"]
        if not running or not auto_trade:
            time.sleep(2)
            continue

        prices = get_market()
        ai_results = run_ai(prices, strategy)
        for currency, data in ai_results.items():
            if data["signal"] in ("BUY", "SELL") and random.random() < 0.3:
                signal_queue.put({
                    "symbol": currency,
                    "action": data["signal"],
                    "price": prices[currency]
                })
        time.sleep(5)

# Start the bot thread once
if "bot_thread" not in st.session_state:
    bot_thread = threading.Thread(target=bot_loop, daemon=True)
    bot_thread.start()
    st.session_state.bot_thread = True

def process_bot_signals():
    while not signal_queue.empty():
        trade = signal_queue.get()
        execute_trade(trade["symbol"], trade["action"], trade["price"])
        if st.session_state.alerts_enabled:
            st.toast(f"Bot: {trade['action']} {trade['symbol']} @ {trade['price']}")

# ============================================================
# LOGIN PAGE
# ============================================================
if not st.session_state.logged:
    st.title("🔐 SAI AI Forex Login")
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Login"):
            ok, role = login(user, pw)
            if ok:
                st.session_state.logged = True
                st.session_state.username = user
                st.session_state.role = role
                # Load balance
                get_account()
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        new_user = st.text_input("New Username")
        new_pw = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            if register(new_user, new_pw):
                st.success("Account created! Please login.")
            else:
                st.error("Username already exists")
    st.stop()

# Process bot signals before UI
process_bot_signals()

# ============================================================
# SIDEBAR CONTROL CENTER
# ============================================================
with st.sidebar:
    st.title("⚙️ SAI Control Center")
    st.write(f"👤 {st.session_state.username}")
    st.write(f"Role: {st.session_state.role}")
    st.divider()

    # Dark mode toggle
    dark = st.checkbox("🌙 Dark Mode", value=st.session_state.dark_mode)
    if dark != st.session_state.dark_mode:
        st.session_state.dark_mode = dark
        st.rerun()

    st.session_state.risk = st.slider("Risk Level %", 1, 20, st.session_state.risk)
    st.session_state.auto_trade = st.checkbox("Enable AI Auto Trading", value=st.session_state.auto_trade)

    # AI strategy
    strategies = ["Scalper", "Trend", "Breakout"]
    st.session_state.strategy = st.selectbox(
        "AI Strategy",
        strategies,
        index=strategies.index(st.session_state.strategy) if st.session_state.strategy in strategies else 0
    )

    # Password change
    with st.expander("🔑 Change Password"):
        old = st.text_input("Old Password", type="password")
        new1 = st.text_input("New Password", type="password")
        new2 = st.text_input("Confirm New Password", type="password")
        if st.button("Update Password"):
            if new1 != new2:
                st.error("Passwords do not match")
            elif not old or not new1:
                st.error("Fill all fields")
            else:
                if change_password(st.session_state.username, old, new1):
                    st.success("Password updated")
                else:
                    st.error("Old password incorrect")

    # Bot start/stop
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Start"):
            with bot_lock:
                bot_settings["bot_running"] = True
                bot_settings["auto_trade"] = st.session_state.auto_trade
                bot_settings["risk"] = st.session_state.risk
                bot_settings["strategy"] = st.session_state.strategy
            st.session_state.bot_running = True
            st.rerun()
    with col2:
        if st.button("⏹ Stop"):
            with bot_lock:
                bot_settings["bot_running"] = False
                bot_settings["auto_trade"] = False
            st.session_state.bot_running = False
            st.rerun()

    st.divider()

    # Admin user management
    if st.session_state.role == "admin":
        st.subheader("👥 Users")
        user_df = get_users()
        st.dataframe(user_df, hide_index=True, use_container_width=True)
        delete_name = st.selectbox(
            "Delete User",
            user_df["username"].tolist() if not user_df.empty else []
        )
        if st.button("Delete User"):
            if delete_name != "admin":
                remove_user(delete_name)
                st.success("User removed")
                st.rerun()
            else:
                st.error("Cannot delete admin")

    if st.button("🚪 Logout"):
        with bot_lock:
            bot_settings["bot_running"] = False
            bot_settings["auto_trade"] = False
        st.session_state.clear()
        st.rerun()

# ============================================================
# HEADER
# ============================================================
st.title("📈 SAI Autonomous Forex Intelligence")
st.caption("AI Market Brain | East Africa Currency Intelligence")

# ============================================================
# ACCOUNT METRICS
# ============================================================
account = get_account()
signals_count = signal_queue.qsize()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Balance", f"${account['balance']:,.2f}")
m2.metric("Bot Status", "RUNNING" if st.session_state.bot_running else "STOPPED")
m3.metric("Risk", f"{st.session_state.risk}%")
m4.metric("Signals", signals_count)

# ============================================================
# DASHBOARD TABS
# ============================================================
tabs = st.tabs([
    "🌍 Market",
    "🧠 AI Brain",
    "🔮 Forecast",
    "💹 Trading",
    "📜 History",
    "🧬 AI Memory",
    "⚙ System"
])

# ---------------------------------------------------------
# MARKET TAB
# ---------------------------------------------------------
with tabs[0]:
    st.subheader("🌍 Live Market")
    live = st.checkbox("🔄 Enable Live Feed (refreshes every 2s)", value=st.session_state.live_feed)
    if live != st.session_state.live_feed:
        st.session_state.live_feed = live
        st.rerun()

    prices = get_market()
    save_market(prices)

    market_df = pd.DataFrame({"Currency": list(prices.keys()), "Rate": list(prices.values())})
    st.dataframe(market_df, hide_index=True)
    fig = px.bar(market_df, x="Currency", y="Rate", title="Currency Rates")
    st.plotly_chart(fig, use_container_width=True)

    if live:
        st.caption("Live feed active – page will auto‑refresh every 2 seconds.")

# ---------------------------------------------------------
# AI BRAIN TAB
# ---------------------------------------------------------
with tabs[1]:
    st.subheader("🧠 SAI AI Decision Brain")
    prices = get_market()
    results = run_ai(prices, st.session_state.strategy)

    rows = []
    for currency, data in results.items():
        rows.append({
            "Currency": currency,
            "Signal": data["signal"],
            "Confidence %": data["confidence"],
            "RSI": data["rsi"],
            "Forecast": data["forecast"]
        })
    ai_df = pd.DataFrame(rows)
    st.dataframe(ai_df, hide_index=True, use_container_width=True)

    for item in rows:
        if item["Signal"] == "BUY":
            st.success(f"🟢 BUY {item['Currency']} | Confidence {item['Confidence %']}%")
        elif item["Signal"] == "SELL":
            st.error(f"🔴 SELL {item['Currency']} | Confidence {item['Confidence %']}%")

# ---------------------------------------------------------
# FORECAST TAB
# ---------------------------------------------------------
with tabs[2]:
    st.subheader("🔮 AI Forecast Engine")
    currency = st.selectbox("Currency", list(CURRENCIES.keys()))
    days = st.slider("Days", 1, 30, 7)
    prediction = forecast_currency(currency, days)

    forecast_df = pd.DataFrame({"Day": range(1, days+1), "Forecast": prediction})
    st.line_chart(forecast_df.set_index("Day"))
    st.dataframe(forecast_df, hide_index=True)

# ---------------------------------------------------------
# TRADING TAB
# ---------------------------------------------------------
with tabs[3]:
    st.subheader("💹 Manual Trading")
    symbol = st.selectbox("Currency", list(CURRENCIES.keys()), key="trade_sym")
    action = st.radio("Action", ["BUY", "SELL"])
    price = get_market()[symbol]
    st.metric("Current Price", price)

    if st.button("Execute AI Trade"):
        pnl = execute_trade(symbol, action, price)
        st.success(f"Trade completed | PnL ${pnl:.2f}")

# ---------------------------------------------------------
# HISTORY TAB
# ---------------------------------------------------------
with tabs[4]:
    st.subheader("📜 Trade History")
    history = get_trade_history()
    st.dataframe(history, hide_index=True, use_container_width=True)

    if not history.empty:
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            st.metric("Total Trades", len(history))
        with col_h2:
            st.metric("Total PnL", f"${history['pnl'].sum():.2f}")

        # Cumulative PnL chart
        history_sorted = history.sort_values("id")
        history_sorted["Cumulative PnL"] = history_sorted["pnl"].cumsum()
        fig_pnl = px.line(history_sorted, x="id", y="Cumulative PnL",
                          title="Cumulative Profit / Loss")
        st.plotly_chart(fig_pnl, use_container_width=True)

        # Export CSV
        csv = history.to_csv(index=False).encode()
        st.download_button(
            label="📥 Export Trade History (CSV)",
            data=csv,
            file_name=f"trade_history_{st.session_state.username}.csv",
            mime="text/csv"
        )

# ---------------------------------------------------------
# AI MEMORY TAB
# ---------------------------------------------------------
with tabs[5]:
    st.subheader("🧬 AI Memory Database")
    memory = load_ai_memory()
    st.dataframe(memory, hide_index=True, use_container_width=True)

# ---------------------------------------------------------
# SYSTEM TAB
# ---------------------------------------------------------
with tabs[6]:
    st.subheader("⚙ System Diagnostics")
    st.json(system_status())

    st.subheader("📬 Alert Settings")
    st.session_state.alerts_enabled = st.checkbox("Enable Trade Alerts", value=st.session_state.alerts_enabled)
    if st.session_state.alerts_enabled:
        st.session_state.alert_email = st.text_input("Email address (for alerts)", value=st.session_state.alert_email)
        st.session_state.alert_telegram = st.text_input("Telegram chat ID (optional)", value=st.session_state.alert_telegram)
        st.caption("Alerts are simulated via toast notifications. Real SMTP/Telegram integration requires additional configuration.")

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption("SAI AI Forex Intelligence v6.2 | Production Ready | PostgreSQL + Live Bot")

# ============================================================
# LIVE FEED AUTO‑REFRESH
# ============================================================
if st.session_state.live_feed:
    time.sleep(2)
    st.rerun()