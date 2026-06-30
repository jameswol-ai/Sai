# =========================================================
# SAI Forex Bot – Clean Architecture (Fixed Version)
# =========================================================

import streamlit as st
import threading
import time
import logging
from logging.handlers import RotatingFileHandler
import matplotlib.pyplot as plt
import pandas as pd
import random
import pickle
from datetime import datetime, timedelta
from collections import deque
import queue
import numpy as np
import requests
import os
import warnings
import sqlite3
from typing import Dict, List, Optional, Any, Tuple

# =========================================================
# PAGE CONFIG (MUST BE FIRST STREAMLIT CALL)
# =========================================================
st.set_page_config(page_title="SAI Forex Bot", layout="wide")

# =========================================================
# OPTIONAL LIBRARIES
# =========================================================
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from newsapi import NewsApiClient
    from textblob import TextBlob
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# =========================================================
# GLOBAL CONFIG
# =========================================================
BOT_CONFIG = {
    "alert_errors": False,
    "lock": threading.Lock()
}

# =========================================================
# LOGGING
# =========================================================
logger = logging.getLogger("sai_app")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("sai_app.log", maxBytes=2_000_000, backupCount=3)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)

# =========================================================
# SESSION STATE DEFAULTS
# =========================================================
defaults = {
    "bot_running": False,
    "bot_queue": queue.Queue(),
    "stop_event": threading.Event(),
    "logs": [],
    "history": pd.DataFrame(),
    "rates": {},
    "alert_errors": False,
    "alert_signals": False,
    "use_auto_arima": False,
    "auto_refresh": False,
    "refresh_interval": 3,
    "risk_level": 5,
    "db_initialised": False
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================================================
# DATABASE
# =========================================================
DB_PATH = "sai_trading.db"
DB_LOCK = threading.Lock()

def db_connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = db_connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bot_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            trade TEXT,
            symbol TEXT,
            amount REAL,
            error TEXT
        );
    """)
    conn.commit()
    conn.close()

if not st.session_state.db_initialised:
    init_db()
    st.session_state.db_initialised = True

# =========================================================
# MARKET DATA (SIMULATED)
# =========================================================
CURRENCIES = ["UGX","KES","TZS","RWF","BIF","SSP","ETB","USD","EUR","GBP","JPY"]

def sample_rates():
    ranges = {
        "UGX": (3700,3900), "KES": (125,140), "TZS": (2500,2700),
        "RWF": (1300,1500), "BIF": (2800,3000), "SSP": (1500,1800),
        "ETB": (55,60), "USD": (1,1), "EUR": (0.9,1.1),
        "GBP": (0.75,0.85), "JPY": (140,150)
    }
    return {k: round(random.uniform(*v),2) for k,v in ranges.items()}

# =========================================================
# BOT ENGINE
# =========================================================
def run_bot():
    return {
        "time": datetime.now().isoformat(),
        "trade": random.choice(["BUY","SELL"]),
        "symbol": random.choice(CURRENCIES),
        "amount": random.randint(100,5000)
    }

def bot_loop(q, stop_event):
    while not stop_event.is_set():
        try:
            q.put(run_bot())
        except Exception as e:
            logger.error(e)
        time.sleep(2)

def start_bot():
    if st.session_state.bot_running:
        return
    st.session_state.stop_event = threading.Event()
    t = threading.Thread(
        target=bot_loop,
        args=(st.session_state.bot_queue, st.session_state.stop_event),
        daemon=True
    )
    st.session_state.bot_running = True
    t.start()

def stop_bot():
    st.session_state.stop_event.set()
    st.session_state.bot_running = False

def drain_queue():
    while not st.session_state.bot_queue.empty():
        item = st.session_state.bot_queue.get()
        st.session_state.logs.append(item)

# =========================================================
# NEWS SENTIMENT (FIXED)
# =========================================================
def fetch_news_sentiment():
    if not SENTIMENT_AVAILABLE:
        return None
    try:
        api_key = st.secrets.get("NEWS_API_KEY", None)
        if not api_key:
            return None

        api = NewsApiClient(api_key=api_key)
        data = api.get_everything(q="forex Africa", language="en", page_size=5)

        scores = []
        for a in data["articles"]:
            text = (a["title"] or "") + (a["description"] or "")
            scores.append(TextBlob(text).sentiment.polarity)

        return {
            "score": float(np.mean(scores)) if scores else 0,
            "interpretation": "Bullish" if np.mean(scores) > 0 else "Bearish"
        }
    except Exception as e:
        logger.error(e)
        return None

# =========================================================
# UI
# =========================================================
st.title("📊 SAI Forex Bot")

st.markdown("### Intelligence Panel")

col1, col2 = st.columns(2)

with col1:
    st.metric("Market Status", "Bullish 🟢")

with col2:
    st.metric("Confidence", "87%")

# =========================================================
# LIVE DATA
# =========================================================
rates = sample_rates()
st.session_state.rates = rates

st.markdown("### Rates")

for k,v in rates.items():
    st.write(f"{k}: {v}")

# =========================================================
# BOT CONTROLS
# =========================================================
st.markdown("### Bot Controls")

c1, c2 = st.columns(2)

with c1:
    if st.button("Start Bot"):
        start_bot()

with c2:
    if st.button("Stop Bot"):
        stop_bot()

drain_queue()

st.markdown("### Logs")
st.write(st.session_state.logs[-10:])

# =========================================================
# NEWS PANEL (SAFE CALL)
# =========================================================
st.markdown("### News Sentiment")

sent = fetch_news_sentiment()
if sent:
    st.metric("Sentiment Score", round(sent["score"], 3))
    st.write(sent["interpretation"])
else:
    st.info("Sentiment unavailable")