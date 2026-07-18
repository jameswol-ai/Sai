# ============================================================
# SAI AI Forex Bot v4.0
# Single File Streamlit Cloud Edition
# ============================================================

import streamlit as st
import sqlite3
import hashlib
import random
import time
import os
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
import plotly.graph_objects as go


# ============================================================
# STREAMLIT CONFIG
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
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger("SAI")


# ============================================================
# DATABASE CORE
# ============================================================

def db(path):
    return sqlite3.connect(path)



def password_hash(password):

    return hashlib.sha256(
        password.encode()
    ).hexdigest()



def initialize_database():

    conn = db(USER_DB)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT
    )
    """)


    exists = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]


    if exists == 0:

        conn.execute(
            """
            INSERT INTO users
            VALUES(?,?,?)
            """,
            (
                "admin",
                password_hash("admin123"),
                "admin"
            )
        )


    conn.commit()
    conn.close()



    conn = db(TRADE_DB)


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


    CREATE TABLE IF NOT EXISTS balance(

        username TEXT PRIMARY KEY,

        amount REAL

    );


    """)


    conn.commit()
    conn.close()



initialize_database()



# ============================================================
# USER SYSTEM
# ============================================================

def authenticate(username,password):

    conn=db(USER_DB)

    result=conn.execute(
        """
        SELECT role
        FROM users
        WHERE username=? AND password=?
        """,
        (
            username,
            password_hash(password)
        )
    ).fetchone()


    conn.close()


    if result:

        return True,result[0]


    return False,None



def create_user(username,password):

    try:

        conn=db(USER_DB)

        conn.execute(
            """
            INSERT INTO users
            VALUES(?,?,?)
            """,
            (
                username,
                password_hash(password),
                "user"
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
        SELECT username,role
        FROM users
        """,
        conn
    )

    conn.close()

    return users



def delete_user(username):

    conn=db(USER_DB)

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
# SESSION STATE
# ============================================================

defaults={

    "logged":False,

    "username":"",

    "role":"",

    "bot_running":False,

    "balance":10000.0,

    "trades":[],

    "signals":[]

}



for key,value in defaults.items():

    if key not in st.session_state:

        st.session_state[key]=value



# ============================================================
# LOGIN UI
# ============================================================

if not st.session_state.logged:


    st.title("🔐 SAI AI Forex Bot Login")


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


        if st.button("Login"):


            ok,role=authenticate(
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
                    "Invalid login"
                )



    with register_tab:


        new_user=st.text_input(
            "New username"
        )


        new_password=st.text_input(
            "New password",
            type="password"
        )


        if st.button("Create Account"):


            if create_user(
                new_user,
                new_password
            ):

                st.success(
                    "Account created"
                )

            else:

                st.error(
                    "Username already exists"
                )


    st.stop()