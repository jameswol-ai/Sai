# ============================================================
# SAI AI Forex Trading Bot - Streamlit Control Center v3.0
# Cloud Stable Edition
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import hashlib
import random
import time
import queue
import threading
from pathlib import Path
from datetime import datetime

import plotly.graph_objects as go


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="SAI AI Forex Bot",
    page_icon="📈",
    layout="wide"
)


BASE_DIR = Path(__file__).parent

USER_DB = BASE_DIR / "sai_users.db"
TRADE_DB = BASE_DIR / "sai_trading.db"


# ============================================================
# DATABASE
# ============================================================

def connect(db):
    return sqlite3.connect(db)


def hash_password(password):
    return hashlib.sha256(
        password.encode()
    ).hexdigest()


def init_database():

    conn = connect(USER_DB)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT
    )
    """)

    count = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    if count == 0:
        conn.execute(
            """
            INSERT INTO users
            VALUES(?,?,?)
            """,
            (
                "admin",
                hash_password("admin123"),
                "admin"
            )
        )

    conn.commit()
    conn.close()


    conn = connect(TRADE_DB)

    conn.executescript("""

    CREATE TABLE IF NOT EXISTS trades(
        id INTEGER PRIMARY KEY,
        username TEXT,
        time TEXT,
        symbol TEXT,
        action TEXT,
        price REAL,
        pnl REAL
    );

    CREATE TABLE IF NOT EXISTS balance(
        username TEXT PRIMARY KEY,
        amount REAL
    );

    """)

    conn.commit()
    conn.close()



init_database()



# ============================================================
# USER SYSTEM
# ============================================================

def login(username, password):

    conn = connect(USER_DB)

    row = conn.execute(
        """
        SELECT role FROM users
        WHERE username=? AND password=?
        """,
        (
            username,
            hash_password(password)
        )
    ).fetchone()

    conn.close()

    if row:
        return True, row[0]

    return False, None



def register(username,password):

    try:

        conn = connect(USER_DB)

        conn.execute(
            """
            INSERT INTO users
            VALUES(?,?,?)
            """,
            (
                username,
                hash_password(password),
                "user"
            )
        )

        conn.commit()
        conn.close()

        return True

    except:

        return False



# ============================================================
# SESSION
# ============================================================

defaults = {

    "logged":False,
    "username":"",
    "role":"",
    "bot":False,
    "balance":10000,
    "trades":[],
    "signals":[]

}


for k,v in defaults.items():

    if k not in st.session_state:
        st.session_state[k]=v



# ============================================================
# LOGIN PAGE
# ============================================================

if not st.session_state.logged:


    st.title("🔐 SAI AI Forex Login")


    tab1,tab2 = st.tabs(
        [
            "Login",
            "Register"
        ]
    )


    with tab1:

        user = st.text_input(
            "Username"
        )

        pw = st.text_input(
            "Password",
            type="password"
        )


        if st.button("Login"):

            ok,role = login(
                user,
                pw
            )

            if ok:

                st.session_state.logged=True
                st.session_state.username=user
                st.session_state.role=role

                st.rerun()

            else:

                st.error(
                    "Invalid login"
                )



    with tab2:

        new_user = st.text_input(
            "New Username"
        )

        new_pw = st.text_input(
            "New Password",
            type="password"
        )


        if st.button("Create Account"):

            if register(
                new_user,
                new_pw
            ):

                st.success(
                    "Account created"
                )

            else:

                st.error(
                    "Username exists"
                )


    st.stop()



# ============================================================
# MARKET ENGINE
# ============================================================


CURRENCIES = [

"UGX",
"KES",
"TZS",
"SSP",
"RWF",
"USD",
"EUR"

]


def market_data():

    data={}

    ranges={

        "UGX":3800,
        "KES":130,
        "TZS":2600,
        "SSP":1600,
        "RWF":1350,
        "USD":1,
        "EUR":0.92

    }


    for c,v in ranges.items():

        data[c]=round(
            v+random.uniform(-5,5),
            2
        )


    return data



def ai_signal():

    return random.choice(
        [
            "BUY",
            "SELL",
            "HOLD"
        ]
    )



# ============================================================
# TRADING ENGINE
# ============================================================


def execute_trade(symbol,action,price):


    pnl=random.uniform(
        -50,
        100
    )


    conn=connect(
        TRADE_DB
    )


    conn.execute(
        """
        INSERT INTO trades
        VALUES(NULL,?,?,?,?,?,?)
        """,
        (
            st.session_state.username,
            datetime.now().isoformat(),
            symbol,
            action,
            price,
            pnl
        )
    )


    conn.commit()
    conn.close()



# ============================================================
# DASHBOARD
# ============================================================


st.sidebar.title(
    "⚙ SAI Control"
)


st.sidebar.write(
    f"User: {st.session_state.username}"
)


if st.sidebar.button(
    "Logout"
):

    st.session_state.clear()
    st.rerun()



risk = st.sidebar.slider(
    "Risk %",
    1,
    10,
    2
)



if st.sidebar.button(
    "Start AI Bot"
):

    st.session_state.bot=True



if st.sidebar.button(
    "Stop AI Bot"
):

    st.session_state.bot=False



st.title(
    "📈 SAI Autonomous Forex Intelligence"
)



rates=market_data()



col1,col2,col3,col4=st.columns(4)


col1.metric(
    "Balance",
    f"${st.session_state.balance:,.2f}"
)


col2.metric(
    "Bot",
    "RUNNING" if st.session_state.bot else "STOPPED"
)


signal=ai_signal()


col3.metric(
    "AI Signal",
    signal
)


col4.metric(
    "Risk",
    f"{risk}%"
)



# ============================================================
# MARKET CHART
# ============================================================


st.subheader(
    "🌍 Currency Market"
)


df=pd.DataFrame(
    {
        "Currency":list(rates.keys()),
        "Rate":list(rates.values())
    }
)


fig=go.Figure()


fig.add_trace(
    go.Bar(
        x=df.Currency,
        y=df.Rate
    )
)


st.plotly_chart(
    fig,
    use_container_width=True
)



# ============================================================
# AI DECISION
# ============================================================


st.subheader(
    "🧠 SAI Brain"
)


if st.button(
    "Generate Trade Signal"
):

    signal=ai_signal()


    price=rates["UGX"]


    st.success(
        f"{signal} signal generated"
    )


    if signal!="HOLD":

        execute_trade(
            "UGX",
            signal,
            price
        )


# ============================================================
# HISTORY
# ============================================================


st.subheader(
    "📜 Trading History"
)


conn=connect(
    TRADE_DB
)


history=pd.read_sql(
    """
    SELECT *
    FROM trades
    WHERE username=?
    ORDER BY id DESC
    """,
    conn,
    params=[
        st.session_state.username
    ]
)


conn.close()


st.dataframe(
    history,
    use_container_width=True
)


# ============================================================
# FOOTER
# ============================================================


st.caption(
    "SAI AI Trading System | Simulation Engine | Cloud Ready"
)