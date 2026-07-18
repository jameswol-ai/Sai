import streamlit as st
import pandas as pd
import numpy as np
import subprocess
import os
import time
from datetime import datetime


st.set_page_config(
    page_title="SAI AI Trading Bot",
    page_icon="📈",
    layout="wide"
)


# -------------------------
# SESSION MEMORY
# -------------------------

if "bot_process" not in st.session_state:
    st.session_state.bot_process = None

if "logs" not in st.session_state:
    st.session_state.logs = []


# -------------------------
# HEADER
# -------------------------

st.title("📈 SAI AI Trading Bot Control Center")

st.caption(
    "Autonomous market intelligence and execution dashboard"
)



# -------------------------
# SIDEBAR
# -------------------------

st.sidebar.header("⚙ Configuration")


exchange = st.sidebar.selectbox(
    "Exchange",
    [
        "Binance",
        "Bybit",
        "Demo Mode"
    ]
)


pair = st.sidebar.selectbox(
    "Trading Pair",
    [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT"
    ]
)


timeframe = st.sidebar.selectbox(
    "Timeframe",
    [
        "1m",
        "5m",
        "15m",
        "1h",
        "4h"
    ]
)


risk = st.sidebar.slider(
    "Risk %",
    1,
    10,
    2
)


# -------------------------
# STATUS PANEL
# -------------------------


c1,c2,c3 = st.columns(3)


with c1:

    if st.session_state.bot_process:

        st.metric(
            "SAI Status",
            "ONLINE"
        )

    else:

        st.metric(
            "SAI Status",
            "OFFLINE"
        )


with c2:

    st.metric(
        "Trading Pair",
        pair
    )


with c3:

    st.metric(
        "Risk Level",
        f"{risk}%"
    )



# -------------------------
# MARKET ENGINE
# -------------------------


st.subheader("Market Intelligence")


price = pd.DataFrame(
    {
        "Price":
        np.cumsum(
            np.random.randn(50)
        ) + 100,

        "SMA":
        np.linspace(
            98,
            105,
            50
        )
    }
)


st.line_chart(price)



# -------------------------
# AI DECISION
# -------------------------


st.subheader("🤖 SAI Brain")


confidence = np.random.randint(
    60,
    95
)


signal = np.random.choice(
    [
        "BUY",
        "SELL",
        "WAIT"
    ]
)


col1,col2 = st.columns(2)


with col1:

    st.metric(
        "AI Signal",
        signal
    )


with col2:

    st.metric(
        "Confidence",
        f"{confidence}%"
    )



# -------------------------
# BOT CONTROL
# -------------------------


st.subheader("🚀 Bot Execution")


possible_files = [
    "main.py",
    "bot.py",
    "engine.py"
]


entry = None


for f in possible_files:

    if os.path.exists(f):
        entry = f
        break



start,stop = st.columns(2)



with start:

    if st.button(
        "▶ Start SAI"
    ):


        if entry is None:

            st.error(
                "No bot engine found"
            )

        elif st.session_state.bot_process is None:


            st.session_state.bot_process = subprocess.Popen(
                [
                    "python",
                    entry
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )


            st.success(
                "SAI started"
            )



with stop:

    if st.button(
        "⛔ Stop SAI"
    ):


        if st.session_state.bot_process:


            st.session_state.bot_process.terminate()

            st.session_state.bot_process=None


            st.warning(
                "SAI stopped"
            )



# -------------------------
# LIVE LOGS
# -------------------------


st.subheader("📜 Live System Logs")


if st.session_state.bot_process:


    line = (
        st.session_state
        .bot_process
        .stdout
        .readline()
    )


    if line:

        st.session_state.logs.append(
            line
        )


else:

    st.session_state.logs.append(
        f"{datetime.now()} SAI offline"
    )


st.text(
    "\n".join(
        st.session_state.logs[-20:]
    )
)