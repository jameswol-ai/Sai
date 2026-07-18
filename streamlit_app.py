# ============================================================
# SAI AI FOREX BOT v5.0
# Unified Single File Streamlit Edition
# ============================================================

import streamlit as st
import sqlite3
import hashlib
import random
import threading
import queue
import time
import logging
import warnings
import requests
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import numpy as np


try:
    import plotly.graph_objects as go
    PLOTLY = True
except Exception:
    PLOTLY = False


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="SAI AI Forex Intelligence",
    page_icon="📈",
    layout="wide"
)


BASE_DIR = Path(__file__).parent

USER_DB = BASE_DIR / "sai_users.db"
TRADE_DB = BASE_DIR / "sai_trading.db"



# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    filename="sai.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger("SAI")



# ============================================================
# DATABASE
# ============================================================

def db(path):

    return sqlite3.connect(
        path,
        check_same_thread=False
    )



def hash_password(password):

    return hashlib.sha256(
        password.encode()
    ).hexdigest()



def initialize_database():

    conn=db(USER_DB)


    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(

        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        email TEXT

    )
    """)



    count=conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]



    if count==0:

        conn.execute(
            """
            INSERT INTO users
            VALUES(?,?,?,?)
            """,
            (
                "admin",
                hash_password("admin123"),
                "admin",
                "admin@sai.ai"
            )
        )


    conn.commit()
    conn.close()



    conn=db(TRADE_DB)


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
        amount REAL

    );


    CREATE TABLE IF NOT EXISTS orders(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        time TEXT,
        symbol TEXT,
        action TEXT,
        price REAL,
        status TEXT

    );


    CREATE TABLE IF NOT EXISTS logs(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        time TEXT,
        message TEXT

    );


    """)


    conn.commit()
    conn.close()



initialize_database()



# ============================================================
# USER SYSTEM
# ============================================================

def login_user(username,password):


    conn=db(USER_DB)


    row=conn.execute(
        """
        SELECT role
        FROM users
        WHERE username=?
        AND password=?
        """,
        (
            username,
            hash_password(password)
        )
    ).fetchone()


    conn.close()


    if row:

        return True,row[0]


    return False,None




def create_user(username,password,email):


    try:

        conn=db(USER_DB)


        conn.execute(
            """
            INSERT INTO users
            VALUES(?,?,?,?)
            """,
            (
                username,
                hash_password(password),
                "user",
                email
            )
        )


        conn.commit()
        conn.close()


        return True


    except Exception:

        return False




def get_users():

    conn=db(USER_DB)


    users=pd.read_sql(
        """
        SELECT username,role,email
        FROM users
        """,
        conn
    )


    conn.close()


    return users




def remove_user(username):

    conn=db(USER_DB)

    conn.execute(
        "DELETE FROM users WHERE username=?",
        (username,)
    )

    conn.commit()
    conn.close()



# ============================================================
# SESSION STATE
# ============================================================

defaults={

    "logged":False,
    "username":"",
    "role":"",
    "balance":10000.0,
    "bot_running":False,
    "auto_trade":False,
    "risk":5,
    "signals":[],
    "logs":[],
    "queue":queue.Queue(),
    "stop":None,
    "thread":None

}



for key,value in defaults.items():

    if key not in st.session_state:

        st.session_state[key]=value



# ============================================================
# LOGIN SCREEN
# ============================================================

def login_screen():

    st.title(
        "🔐 SAI AI Forex Bot"
    )


    login_tab,register_tab=st.tabs(
        [
            "Login",
            "Register"
        ]
    )


    with login_tab:


        username=st.text_input(
            "Username"
        )


        password=st.text_input(
            "Password",
            type="password"
        )


        if st.button(
            "Login"
        ):


            ok,role=login_user(
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
                    "Invalid credentials"
                )



    with register_tab:


        username=st.text_input(
            "New Username"
        )


        password=st.text_input(
            "New Password",
            type="password"
        )


        email=st.text_input(
            "Email"
        )


        if st.button(
            "Create Account"
        ):


            if create_user(
                username,
                password,
                email
            ):

                st.success(
                    "Account created"
                )

            else:

                st.error(
                    "Username already exists"
                )



if not st.session_state.logged:

    login_screen()

    st.stop()