# ============================================================
# SAI AI Forex Bot v4.0
# Single File Streamlit Edition
# ============================================================

import streamlit as st
import sqlite3
import hashlib
import random
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
import plotly.graph_objects as go


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="SAI AI Forex Bot",
    page_icon="📈",
    layout="wide"
)

BASE = Path(__file__).parent

USER_DB = BASE / "sai_users.db"
TRADE_DB = BASE / "sai_trading.db"


# ============================================================
# DATABASE
# ============================================================

def connect(path):
    return sqlite3.connect(path)


def hash_password(password):
    return hashlib.sha256(
        password.encode()
    ).hexdigest()


def init_db():

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
            INSERT INTO users VALUES(?,?,?)
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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        time TEXT,
        symbol TEXT,
        action TEXT,
        price REAL,
        pnl REAL
    );


    CREATE TABLE IF NOT EXISTS balances(
        username TEXT PRIMARY KEY,
        balance REAL
    );

    """)

    conn.commit()
    conn.close()


init_db()


# ============================================================
# USER SYSTEM
# ============================================================

def login(user,password):

    conn = connect(USER_DB)

    row = conn.execute(
        """
        SELECT role FROM users
        WHERE username=? AND password=?
        """,
        (
            user,
            hash_password(password)
        )
    ).fetchone()

    conn.close()

    if row:
        return True,row[0]

    return False,None



def register(user,password):

    try:

        conn=connect(USER_DB)

        conn.execute(
            """
            INSERT INTO users VALUES(?,?,?)
            """,
            (
                user,
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

defaults={

    "logged":False,
    "username":"",
    "role":"",
    "bot":False,
    "balance":10000.0

}


for k,v in defaults.items():

    if k not in st.session_state:
        st.session_state[k]=v



# ============================================================
# LOGIN PAGE
# ============================================================

if not st.session_state.logged:


    st.title("🔐 SAI AI Forex Login")


    a,b=st.tabs(
        [
            "Login",
            "Register"
        ]
    )


    with a:

        username=st.text_input(
            "Username"
        )

        password=st.text_input(
            "Password",
            type="password"
        )


        if st.button("Login"):

            ok,role=login(
                username,
                password
            )

            if ok:

                st.session_state.logged=True
                st.session_state.username=username
                st.session_state.role=role

                st.rerun()

            else:

                st.error(
                    "Wrong username or password"
                )


    with b:

        new_user=st.text_input(
            "New username"
        )

        new_pass=st.text_input(
            "New password",
            type="password"
        )


        if st.button("Register"):

            if register(
                new_user,
                new_pass
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

CURRENCIES={

    "UGX":3800,
    "KES":130,
    "TZS":2600,
    "SSP":1600,
    "RWF":1350,
    "USD":1,
    "EUR":0.92,
    "GBP":0.78

}



def get_market():

    result={}

    for c,v in CURRENCIES.items():

        result[c]=round(
            v + random.uniform(-5,5),
            2
        )

    return result



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
        120
    )


    conn=connect(TRADE_DB)

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


    st.session_state.balance += pnl



# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("⚙️ SAI Control")

    st.write(
        st.session_state.username
    )

    if st.button("Logout"):

        st.session_state.clear()
        st.rerun()


    risk=st.slider(
        "Risk Level",
        1,
        10,
        2
    )


    if st.button("Start Bot"):

        st.session_state.bot=True


    if st.button("Stop Bot"):

        st.session_state.bot=False



# ============================================================
# DASHBOARD
# ============================================================

st.title(
    "📈 SAI Autonomous Forex Intelligence"
)


rates=get_market()


signal=ai_signal()



c1,c2,c3,c4=st.columns(4)


c1.metric(
    "Balance",
    f"${st.session_state.balance:,.2f}"
)


c2.metric(
    "Bot Status",
    "RUNNING" if st.session_state.bot else "STOPPED"
)


c3.metric(
    "AI Signal",
    signal
)


c4.metric(
    "Risk",
    f"{risk}%"
)



# ============================================================
# MARKET CHART
# ============================================================

df=pd.DataFrame(
    {
        "Currency":list(rates.keys()),
        "Rate":list(rates.values())
    }
)


fig=go.Figure()


fig.add_trace(
    go.Bar(
        x=df["Currency"],
        y=df["Rate"]
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
    "Generate Trade"
):

    action=ai_signal()

    price=rates["UGX"]


    st.info(
        f"AI Decision: {action}"
    )


    if action!="HOLD":

        execute_trade(
            "UGX",
            action,
            price
        )

        st.success(
            "Trade executed"
        )



# ============================================================
# HISTORY
# ============================================================

st.subheader(
    "📜 Trading History"
)


conn=connect(TRADE_DB)


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


st.caption(
    "SAI AI Forex Bot v4 | Simulation Engine"
)