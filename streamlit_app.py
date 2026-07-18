# ============================================================
# SAI AI Forex Bot v4.0
# Unified Cloud Stable Edition
# Part 1: Core System + Database + Authentication
# ============================================================

import streamlit as st
import sqlite3
import hashlib
import os
import logging
import threading
import queue
import time
import random
import json

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import pandas as pd
import numpy as np


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SAI AI Forex Intelligence",
    page_icon="📈",
    layout="wide"
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).parent

USER_DB = BASE_DIR / "sai_users.db"
TRADE_DB = BASE_DIR / "sai_trading.db"
MEMORY_FILE = BASE_DIR / "sai_memory.json"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("SAI")


# ============================================================
# PASSWORD SECURITY
# ============================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(
        password.encode()
    ).hexdigest()



# ============================================================
# DATABASE ENGINE
# ============================================================

def db_connect(path):

    conn = sqlite3.connect(
        path,
        check_same_thread=False
    )

    return conn



def init_database():

    # -------------------------
    # USER DATABASE
    # -------------------------

    conn = db_connect(USER_DB)

    conn.executescript("""

    CREATE TABLE IF NOT EXISTS users(

        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        email TEXT DEFAULT ''

    );


    """)


    existing = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]


    if existing == 0:

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



    # -------------------------
    # TRADING DATABASE
    # -------------------------

    conn = db_connect(TRADE_DB)


    conn.executescript("""

    CREATE TABLE IF NOT EXISTS trades(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT,

        timestamp TEXT,

        symbol TEXT,

        action TEXT,

        price REAL,

        units REAL,

        pnl REAL

    );


    CREATE TABLE IF NOT EXISTS accounts(

        username TEXT PRIMARY KEY,

        balance REAL DEFAULT 10000,

        equity REAL DEFAULT 10000

    );


    CREATE TABLE IF NOT EXISTS positions(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT,

        symbol TEXT,

        direction TEXT,

        entry REAL,

        units REAL,

        status TEXT

    );


    CREATE TABLE IF NOT EXISTS bot_logs(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT,

        timestamp TEXT,

        message TEXT

    );


    """)


    conn.commit()
    conn.close()



init_database()



# ============================================================
# USER MANAGEMENT
# ============================================================

def authenticate_user(
        username:str,
        password:str
):

    conn = db_connect(USER_DB)


    result = conn.execute(
        """
        SELECT role
        FROM users
        WHERE username=?
        AND password_hash=?
        """,
        (
            username,
            hash_password(password)
        )
    ).fetchone()


    conn.close()


    if result:

        return True, result[0]


    return False, None




def create_user(
        username,
        password,
        email=""
):

    try:

        conn = db_connect(USER_DB)

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


    except sqlite3.IntegrityError:

        return False




def get_users():

    conn = db_connect(USER_DB)

    data = conn.execute(
        """
        SELECT username,role,email
        FROM users
        """
    ).fetchall()

    conn.close()

    return data




def delete_user(username):

    conn = db_connect(USER_DB)

    conn.execute(
        """
        DELETE FROM users
        WHERE username=?
        """,
        (username,)
    )

    conn.commit()
    conn.close()



# ============================================================
# SESSION MEMORY
# ============================================================

SESSION_DEFAULTS = {

    "authenticated":False,

    "username":None,

    "role":None,

    "bot_running":False,

    "auto_trade":False,

    "risk_level":5,

    "balance":10000,

    "trade_queue":queue.Queue(),

    "logs":[],

    "market_history":[]

}



for key,value in SESSION_DEFAULTS.items():

    if key not in st.session_state:

        st.session_state[key]=value



# ============================================================
# LOGIN / REGISTER UI
# ============================================================


def login_screen():


    st.markdown(
        """
        <h1 style='text-align:center'>
        🔐 SAI AI Forex Intelligence
        </h1>
        """,
        unsafe_allow_html=True
    )


    login_tab, register_tab = st.tabs(
        [
            "Login",
            "Create Account"
        ]
    )



    with login_tab:

        username = st.text_input(
            "Username"
        )

        password = st.text_input(
            "Password",
            type="password"
        )


        if st.button(
            "Login",
            key="login"
        ):


            ok,role = authenticate_user(
                username,
                password
            )


            if ok:

                st.session_state.authenticated=True

                st.session_state.username=username

                st.session_state.role=role

                st.rerun()


            else:

                st.error(
                    "Invalid username or password"
                )



    with register_tab:


        username = st.text_input(
            "New username"
        )

        password = st.text_input(
            "New password",
            type="password"
        )

        email = st.text_input(
            "Email"
        )


        if st.button(
            "Register",
            key="register"
        ):


            if create_user(
                username,
                password,
                email
            ):

                st.success(
                    "Account created. Login now."
                )

            else:

                st.error(
                    "Username already exists"
                )



if not st.session_state.authenticated:

    login_screen()

    st.stop()



# ============================================================
# CURRENT USER HELPER
# ============================================================

def current_user():

    return st.session_state.username



logger.info(
    f"User logged in: {current_user()}"
)