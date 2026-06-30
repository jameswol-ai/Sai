# =========================================================
# RANDOM + SAI FUSION SYSTEM
# Autonomous Architecture OS + Forex Intelligence Engine
# Single-File Streamlit Mega App
# =========================================================

import streamlit as st
import threading
import time
import logging
import sqlite3
import json
import uuid
import random
import queue
import os
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from datetime import datetime, timedelta
from pathlib import Path
from collections import deque

# =========================================================
# OPTIONAL MODULES
# =========================================================

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY = True
except:
    PLOTLY = False

try:
    from statsmodels.tsa.arima.model import ARIMA
    ARIMA_OK = True
except:
    ARIMA_OK = False

# =========================================================
# APP CONFIG
# =========================================================

st.set_page_config(page_title="RANDOM × SAI Fusion OS", layout="wide")

st.markdown("""
<style>
body {background-color:#0E1117;}
.section {font-size:20px;color:#00F2FE;font-weight:700;margin-top:20px;}
.card {
    background:#1E1E2F;padding:15px;border-radius:12px;margin:10px 0;
    border:1px solid rgba(255,255,255,0.08);
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# GLOBAL MEMORY
# =========================================================

DB = "fusion.db"

def db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS forex(time TEXT, symbol TEXT, rate REAL);
    CREATE TABLE IF NOT EXISTS logs(time TEXT, msg TEXT);
    """)
    c.commit()
    c.close()

init_db()

# =========================================================
# RANDOM CORE ENGINE (SIMPLIFIED)
# =========================================================

def random_architecture_generator():
    return {
        "id": str(uuid.uuid4())[:8],
        "nodes": random.randint(5, 20),
        "complexity": random.choice(["low", "medium", "high"]),
        "structure": random.choice(["mesh", "tree", "hybrid"]),
        "score": round(random.uniform(0, 1), 3)
    }

# =========================================================
# SAI FOREX ENGINE (CORE SIMPLIFIED)
# =========================================================

CURRENCIES = ["UGX","KES","TZS","RWF","BIF","SSP","ETB","USD","EUR","GBP","JPY"]

def fake_rates():
    base = {
        "UGX": random.uniform(3700, 3900),
        "KES": random.uniform(125, 140),
        "TZS": random.uniform(2500, 2700),
        "USD": 1,
        "EUR": random.uniform(0.9, 1.1),
        "GBP": random.uniform(0.75, 0.85)
    }
    return base

def store_rates(rates):
    c = db()
    for k,v in rates.items():
        c.execute("INSERT INTO forex VALUES (?,?,?)",
                  (datetime.now().isoformat(), k, float(v)))
    c.commit()
    c.close()

def load_history(symbol):
    conn = db()
    df = pd.read_sql("SELECT * FROM forex WHERE symbol=? ORDER BY time ASC", conn, params=(symbol,))
    conn.close()
    return df

# =========================================================
# FORECAST (LIGHTWEIGHT)
# =========================================================

def forecast(series, steps=5):
    if len(series) < 5:
        return [series[-1] if len(series)>0 else 1]*steps
    trend = np.polyfit(range(len(series)), series, 1)[0]
    last = series[-1]
    return [last + trend*(i+1) for i in range(steps)]

# =========================================================
# BOT LOOP
# =========================================================

bot_queue = queue.Queue()
stop_event = threading.Event()

def bot_loop():
    while not stop_event.is_set():
        try:
            rates = fake_rates()
            store_rates(rates)
            bot_queue.put({"time":datetime.now().isoformat(),"rates":rates})
        except Exception as e:
            bot_queue.put({"error":str(e)})
        time.sleep(2)

def start_bot():
    if "thread" not in st.session_state:
        t = threading.Thread(target=bot_loop, daemon=True)
        st.session_state.thread = t
        t.start()

def stop_bot():
    stop_event.set()

# =========================================================
# UI CORE
# =========================================================

st.title("🧬 RANDOM × 📈 SAI Fusion Intelligence System")

tabs = st.tabs(["🌐 Dashboard","🧠 Random Core","📈 Forex Engine","📊 Forecast","⚙️ Logs"])

# =========================================================
# DASHBOARD
# =========================================================

with tabs[0]:
    st.markdown("<div class='section'>Live System Status</div>", unsafe_allow_html=True)

    col1,col2,col3 = st.columns(3)

    col1.metric("System Mode", "FUSION ACTIVE")
    col2.metric("Bot Queue Size", bot_queue.qsize())
    col3.metric("Threads", threading.active_count())

    if st.button("Start Engine"):
        start_bot()
        st.success("Engine started")

    if st.button("Stop Engine"):
        stop_bot()
        st.warning("Stopping engine...")

    st.markdown("### Live Feed")
    items = []
    while not bot_queue.empty():
        items.append(bot_queue.get())

    st.json(items[-5:])

# =========================================================
# RANDOM CORE
# =========================================================

with tabs[1]:
    st.markdown("<div class='section'>Random Architecture Generator</div>", unsafe_allow_html=True)

    if st.button("Generate Architecture"):
        arch = random_architecture_generator()
        st.json(arch)

# =========================================================
# FOREX ENGINE
# =========================================================

with tabs[2]:
    st.markdown("<div class='section'>Forex Engine</div>", unsafe_allow_html=True)

    rates = fake_rates()

    for k,v in rates.items():
        st.markdown(f"""
        <div class='card'>
        <b>{k}</b> : {v:.4f}
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# FORECAST ENGINE
# =========================================================

with tabs[3]:
    st.markdown("<div class='section'>Forecast Engine</div>", unsafe_allow_html=True)

    sym = st.selectbox("Currency", CURRENCIES)

    hist = load_history(sym)
    if len(hist) > 0:
        series = hist["rate"].tolist()
        preds = forecast(series, steps=5)

        st.write("Prediction:", preds)

        if PLOTLY:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=series, name="History"))
            fig.add_trace(go.Scatter(y=preds, name="Forecast"))
            st.plotly_chart(fig)
        else:
            plt.plot(series)
            plt.plot(range(len(series), len(series)+len(preds)), preds)
            st.pyplot(plt)

# =========================================================
# LOGS
# =========================================================

with tabs[4]:
    st.markdown("<div class='section'>System Logs</div>", unsafe_allow_html=True)

    conn = db()
    logs = conn.execute("SELECT * FROM logs ORDER BY time DESC LIMIT 50").fetchall()
    conn.close()

    st.write(logs)