# ============================================================
# SAI AI Forex Intelligence v6.0
# FULL SINGLE FILE STREAMLIT EDITION
# PART 1/4
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
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import requests


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
TRADING_DB = BASE_DIR / "sai_trading.db"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger("SAI")


# ============================================================
# OPTIONAL CHARTS
# ============================================================

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True

except Exception:

    PLOTLY_AVAILABLE = False



# ============================================================
# GLOBAL THREAD SAFE QUEUE
# ============================================================

BOT_QUEUE = queue.Queue()

BOT_THREAD = None
BOT_STOP_EVENT = None



# ============================================================
# DATABASE CORE
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



# ============================================================
# DATABASE INITIALIZATION + MIGRATION
# ============================================================

def init_databases():

    # ---------------- USER DATABASE ----------------

    conn=db(USER_DB)


    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(

        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        email TEXT DEFAULT ''

    )
    """)


    columns=[
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(users)"
        ).fetchall()
    ]


    if "role" not in columns:

        conn.execute(
            "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'"
        )


    if "email" not in columns:

        conn.execute(
            "ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''"
        )



    count=conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]



    if count==0:

        conn.execute(
            """
            INSERT INTO users
            (
            username,
            password,
            role,
            email
            )
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



    # ---------------- TRADING DATABASE ----------------


    conn=db(TRADING_DB)



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


    CREATE TABLE IF NOT EXISTS account(

        username TEXT PRIMARY KEY,
        balance REAL,
        equity REAL

    );


    CREATE TABLE IF NOT EXISTS market(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        time TEXT,
        currency TEXT,
        rate REAL

    );

    """)



    conn.commit()

    conn.close()



init_databases()



# ============================================================
# USER MANAGEMENT
# ============================================================

def authenticate(username,password):

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





def register(username,password,email=""):

    try:

        conn=db(USER_DB)


        conn.execute(
            """
            INSERT INTO users
            (
            username,
            password,
            role,
            email
            )
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


    except Exception as e:

        logger.error(e)

        return False






def users():


    conn=db(USER_DB)


    try:


        df=pd.read_sql_query(
            """
            SELECT

            username,

            COALESCE(role,'user') AS role,

            COALESCE(email,'') AS email


            FROM users

            ORDER BY username

            """,
            conn
        )


    except Exception as e:


        logger.error(
            f"Users table error {e}"
        )


        df=pd.DataFrame(
            columns=[
                "username",
                "role",
                "email"
            ]
        )



    conn.close()


    return df





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


    "login":False,

    "username":"",

    "role":"",

    "balance":10000.0,

    "equity":10000.0,

    "risk":5,

    "auto_trade":False,

    "bot_running":False,

    "signals":[],

    "history":[]

}



for key,value in defaults.items():

    if key not in st.session_state:

        st.session_state[key]=value



# ============================================================
# LOGIN SCREEN
# ============================================================

def login_screen():


    st.title(
        "🔐 SAI AI Forex Intelligence"
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


            ok,role=authenticate(
                username,
                password
            )


            if ok:


                st.session_state.login=True

                st.session_state.username=username

                st.session_state.role=role


                st.rerun()


            else:

                st.error(
                    "Invalid username/password"
                )



    with register_tab:


        new_user=st.text_input(
            "New Username"
        )


        new_pass=st.text_input(
            "New Password",
            type="password"
        )


        email=st.text_input(
            "Email"
        )



        if st.button(
            "Create Account"
        ):


            if register(
                new_user,
                new_pass,
                email
            ):

                st.success(
                    "Account created"
                )


            else:

                st.error(
                    "Username exists"
                )




if not st.session_state.login:

    login_screen()

    st.stop()

# ============================================================
# PART 2/4
# MARKET + AI ENGINE + TRADING CORE
# ============================================================


# ============================================================
# CURRENCY DATABASE
# ============================================================

CURRENCIES = {

    "UGX": 3800,
    "KES": 130,
    "TZS": 2600,
    "RWF": 1350,
    "BIF": 2900,
    "SSP": 1600,
    "ETB": 57,
    "USD": 1,
    "EUR": 0.92,
    "GBP": 0.78,
    "JPY": 145

}



# ============================================================
# MARKET ENGINE
# ============================================================

def simulated_market():

    prices={}


    for currency,value in CURRENCIES.items():


        if currency=="USD":

            prices[currency]=1


        else:

            movement=random.uniform(
                -0.01,
                0.01
            )


            prices[currency]=round(

                value+(value*movement),

                2

            )


    return prices





@st.cache_data(ttl=15)
def live_market():


    try:


        url=(

        "https://api.frankfurter.app/latest"

        "?from=USD&to=EUR,GBP,JPY"

        )


        response=requests.get(
            url,
            timeout=5
        )


        data=response.json()


        external=data.get(
            "rates",
            {}
        )


        external["USD"]=1


        local=simulated_market()


        for k,v in external.items():

            local[k]=v



        return local



    except Exception:


        return simulated_market()




# ============================================================
# MARKET DATABASE
# ============================================================

def save_market(prices):


    conn=db(TRADING_DB)



    for currency,rate in prices.items():


        conn.execute(
            """
            INSERT INTO market
            (
            username,
            time,
            currency,
            rate
            )
            VALUES(?,?,?,?)
            """,
            (

            st.session_state.username,

            datetime.now().isoformat(),

            currency,

            rate

            )
        )



    conn.commit()

    conn.close()





def load_market(currency):


    conn=db(TRADING_DB)


    df=pd.read_sql_query(

        """

        SELECT

        time,

        rate


        FROM market


        WHERE username=?

        AND currency=?


        ORDER BY id


        """,

        conn,

        params=(

            st.session_state.username,

            currency

        )

    )


    conn.close()



    if not df.empty:

        df["time"]=pd.to_datetime(
            df["time"]
        )


    return df





# ============================================================
# AI ANALYSIS FUNCTIONS
# ============================================================


def moving_average(values,period):


    if len(values)<period:

        return None


    return np.mean(
        values[-period:]
    )






def calculate_rsi(values,period=14):


    if len(values)<=period:

        return 50



    changes=np.diff(values)



    gains=np.maximum(
        changes,
        0
    )


    losses=np.maximum(
        -changes,
        0
    )



    avg_gain=np.mean(
        gains[-period:]
    )


    avg_loss=np.mean(
        losses[-period:]
    )


    if avg_loss==0:

        return 100



    rs=avg_gain/avg_loss


    return round(

        100-(100/(1+rs)),

        2

    )





def ai_predict(currency):


    history=load_market(
        currency
    )


    if history.empty:


        return {

            "signal":"HOLD",

            "confidence":0,

            "forecast":None,

            "rsi":50

        }




    prices=list(
        history.rate
    )


    current=prices[-1]



    sma20=moving_average(
        prices,
        20
    )


    sma50=moving_average(
        prices,
        50
    )


    rsi=calculate_rsi(
        prices
    )



    score=0



    if sma20 and sma50:


        if sma20>sma50:

            score+=40

        else:

            score-=40



    if rsi<30:

        score+=30



    elif rsi>70:

        score-=30




    score+=random.randint(
        -15,
        15
    )




    if score>30:

        signal="BUY"


    elif score<-30:

        signal="SELL"


    else:

        signal="HOLD"




    confidence=min(

        abs(score),

        100

    )



    forecast=current*(

        1+

        random.uniform(

            -0.01,

            0.01

        )

    )



    return {


        "signal":signal,


        "confidence":confidence,


        "forecast":round(
            forecast,
            2
        ),


        "rsi":rsi

    }






def run_ai_engine(prices):


    result={}


    for currency in prices:


        result[currency]=ai_predict(
            currency
        )


    return result





# ============================================================
# FORECAST ENGINE
# ============================================================


def forecast_currency(currency,days=7):


    history=load_market(
        currency
    )


    if history.empty:

        return []



    last=float(
        history.rate.iloc[-1]
    )



    output=[]



    for i in range(days):


        change=random.uniform(
            -0.005,
            0.005
        )


        last=last*(1+change)



        output.append(
            round(last,2)
        )



    return output





# ============================================================
# ACCOUNT ENGINE
# ============================================================


def load_account():


    conn=db(TRADING_DB)



    row=conn.execute(

        """

        SELECT

        balance,

        equity


        FROM account


        WHERE username=?

        """,

        (
            st.session_state.username,
        )

    ).fetchone()



    conn.close()



    if row:


        return {

            "balance":row[0],

            "equity":row[1]

        }




    return {


        "balance":10000.0,


        "equity":10000.0

    }







def save_account(balance,equity):


    conn=db(TRADING_DB)


    conn.execute(

        """

        INSERT OR REPLACE INTO account

        VALUES(?,?,?)

        """,

        (

            st.session_state.username,

            balance,

            equity

        )

    )


    conn.commit()

    conn.close()





# ============================================================
# TRADE EXECUTION
# ============================================================


def execute_trade(symbol,action,price):


    account=load_account()



    pnl=random.uniform(
        -100,
        200
    )



    if action=="SELL":

        pnl=-pnl




    balance=(

        account["balance"]

        +

        pnl

    )



    save_account(

        balance,

        balance

    )



    conn=db(TRADING_DB)



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



    return pnl





def trade_history():


    conn=db(TRADING_DB)



    df=pd.read_sql_query(

        """

        SELECT *

        FROM trades

        WHERE username=?

        ORDER BY id DESC


        """,

        conn,

        params=(

            st.session_state.username,

        )

    )



    conn.close()

# ============================================================
# PART 3/4
# AUTONOMOUS BOT ENGINE
# ============================================================


# ============================================================
# RISK MANAGEMENT
# ============================================================

def calculate_position_size(
    balance,
    risk_percent
):


    risk_amount=(

        balance *

        risk_percent /

        100

    )


    return round(
        risk_amount,
        2
    )





# ============================================================
# AI SIGNAL FORMATTER
# ============================================================

def create_signal(
    currency,
    data,
    price
):


    return {


        "currency":currency,


        "action":data["signal"],


        "confidence":data["confidence"],


        "price":price,


        "forecast":data["forecast"],


        "rsi":data["rsi"],


        "time":datetime.now().strftime(

            "%Y-%m-%d %H:%M:%S"

        )

    }





# ============================================================
# BOT WORKER
# ============================================================

def bot_worker(stop_event):


    logger.info(
        "SAI AI Worker Started"
    )



    while not stop_event.is_set():


        try:


            prices=live_market()



            save_market(
                prices
            )



            ai_results=run_ai_engine(
                prices
            )



            for currency,result in ai_results.items():



                if result["signal"]=="HOLD":

                    continue




                signal=create_signal(

                    currency,

                    result,

                    prices[currency]

                )



                BOT_QUEUE.put(
                    signal
                )



                # Auto trading

                if st.session_state.auto_trade:


                    execute_trade(

                        currency,

                        result["signal"],

                        prices[currency]

                    )




        except Exception as e:


            logger.error(

                f"BOT ERROR: {e}"

            )



        time.sleep(10)





# ============================================================
# BOT CONTROL
# ============================================================

def start_bot():


    global BOT_THREAD
    global BOT_STOP_EVENT



    if st.session_state.bot_running:

        return



    BOT_STOP_EVENT=threading.Event()



    BOT_THREAD=threading.Thread(

        target=bot_worker,

        args=(BOT_STOP_EVENT,),

        daemon=True

    )



    BOT_THREAD.start()



    st.session_state.bot_running=True






def stop_bot():


    global BOT_STOP_EVENT



    if BOT_STOP_EVENT:


        BOT_STOP_EVENT.set()



    st.session_state.bot_running=False






# ============================================================
# QUEUE READER
# ============================================================

def read_signals():


    signals=[]



    while not BOT_QUEUE.empty():


        signals.append(

            BOT_QUEUE.get()

        )


    return signals






# ============================================================
# INITIALIZE CURRENT ACCOUNT
# ============================================================

account=load_account()


st.session_state.balance=account["balance"]

st.session_state.equity=account["equity"]





# ============================================================
# LOAD FIRST MARKET DATA
# ============================================================

prices=live_market()


save_market(
    prices
)

# ============================================================
# PART 4/4
# COMPLETE STREAMLIT DASHBOARD UI
# ============================================================


# ============================================================
# SIDEBAR CONTROL CENTER
# ============================================================

with st.sidebar:


    st.title(
        "⚙️ SAI Control Center"
    )


    st.write(
        f"👤 {st.session_state.username}"
    )


    st.write(
        f"Role: {st.session_state.role}"
    )


    st.divider()



    st.session_state.risk = st.slider(

        "Risk Level %",

        1,

        20,

        st.session_state.risk

    )



    st.session_state.auto_trade = st.checkbox(

        "Enable AI Auto Trading",

        value=st.session_state.auto_trade

    )



    if st.button(
        "▶ Start AI Bot"
    ):

        start_bot()

        st.success(
            "AI Bot Started"
        )




    if st.button(
        "⏹ Stop AI Bot"
    ):

        stop_bot()

        st.warning(
            "AI Bot Stopped"
        )



    st.divider()



    if st.session_state.role=="admin":


        st.subheader(
            "👥 Users"
        )


        st.dataframe(

            users(),

            use_container_width=True,

            hide_index=True

        )



        delete_name=st.selectbox(

            "Delete User",

            users()["username"].tolist()

        )



        if st.button(
            "Delete User"
        ):


            if delete_name!="admin":

                delete_user(
                    delete_name
                )

                st.success(
                    "User deleted"
                )

                st.rerun()




    if st.button(
        "🚪 Logout"
    ):

        st.session_state.clear()

        st.rerun()





# ============================================================
# HEADER
# ============================================================


st.title(
    "📈 SAI Autonomous Forex Intelligence"
)


st.caption(
    "AI Market Prediction System | East Africa Edition"
)



# ============================================================
# METRIC PANEL
# ============================================================


account=load_account()


m1,m2,m3,m4=st.columns(4)



m1.metric(

    "Balance",

    f"${account['balance']:,.2f}"

)



m2.metric(

    "Bot",

    "RUNNING"

    if st.session_state.bot_running

    else

    "STOPPED"

)



m3.metric(

    "Risk",

    f"{st.session_state.risk}%"

)



m4.metric(

    "Models",

    len(CURRENCIES)

)




# ============================================================
# READ AI SIGNALS
# ============================================================

new_signals=read_signals()


if new_signals:

    st.session_state.signals.extend(
        new_signals
    )


    st.toast(
        "New AI trade signal detected"
    )





# ============================================================
# MAIN TABS
# ============================================================


tabs=st.tabs(

    [

        "🌍 Market",

        "🧠 AI Brain",

        "🔮 Forecast",

        "💹 Trading",

        "📜 History",

        "⚙ System"

    ]

)





# ============================================================
# MARKET TAB
# ============================================================

with tabs[0]:


    st.subheader(
        "🌍 Live Currency Market"
    )


    prices=live_market()


    df=pd.DataFrame(

        {

            "Currency":
            list(prices.keys()),


            "Rate":
            list(prices.values())

        }

    )



    if PLOTLY_AVAILABLE:


        fig=go.Figure()


        fig.add_trace(

            go.Bar(

                x=df.Currency,

                y=df.Rate,

                name="Exchange Rate"

            )

        )


        fig.update_layout(

            title="USD Base Currency Market"

        )


        st.plotly_chart(

            fig,

            use_container_width=True

        )



    else:


        st.bar_chart(

            df.set_index(
                "Currency"
            )

        )





    cols=st.columns(4)


    for i,(cur,value) in enumerate(prices.items()):


        with cols[i%4]:


            st.metric(

                cur,

                value

            )






# ============================================================
# AI BRAIN TAB
# ============================================================

with tabs[1]:


    st.subheader(
        "🧠 SAI AI Decision Brain"
    )


    prices=live_market()


    results=run_ai_engine(
        prices
    )


    rows=[]



    for currency,data in results.items():


        rows.append(

            {

                "Currency":currency,

                "Signal":data["signal"],

                "Confidence":
                f"{data['confidence']}%",

                "RSI":
                data["rsi"],

                "Forecast":
                data["forecast"]

            }

        )



    ai_df=pd.DataFrame(rows)



    st.dataframe(

        ai_df,

        use_container_width=True,

        hide_index=True

    )



    for item in rows:


        if item["Signal"]=="BUY":

            st.success(

                f"🟢 BUY signal: {item['Currency']}"

            )


        elif item["Signal"]=="SELL":

            st.error(

                f"🔴 SELL signal: {item['Currency']}"

            )





# ============================================================
# FORECAST TAB
# ============================================================

with tabs[2]:


    st.subheader(
        "🔮 AI Forecast Engine"
    )


    currency=st.selectbox(

        "Currency",

        list(CURRENCIES.keys())

    )


    days=st.slider(

        "Forecast Period",

        1,

        30,

        7

    )



    forecast=forecast_currency(

        currency,

        days

    )



    chart=pd.DataFrame(

        {

        "Day":
        range(1,days+1),


        "Forecast":
        forecast

        }

    )



    st.line_chart(

        chart.set_index(
            "Day"
        )

    )


    st.dataframe(

        chart,

        hide_index=True

    )





# ============================================================
# TRADING TAB
# ============================================================

with tabs[3]:


    st.subheader(
        "💹 AI Trading Terminal"
    )



    symbol=st.selectbox(

        "Currency",

        list(CURRENCIES.keys())

    )



    action=st.radio(

        "Action",

        [

            "BUY",

            "SELL"

        ]

    )



    price=live_market()[symbol]



    st.write(

        "Current Price:",

        price

    )



    if st.button(
        "Execute Trade"
    ):


        pnl=execute_trade(

            symbol,

            action,

            price

        )


        st.success(

            f"Trade completed | PnL ${pnl:.2f}"

        )






# ============================================================
# HISTORY TAB
# ============================================================

with tabs[4]:


    st.subheader(
        "📜 Trading History"
    )


    history=trade_history()



    st.dataframe(

        history,

        use_container_width=True,

        hide_index=True

    )



    if not history.empty:


        a,b=st.columns(2)



        a.metric(

            "Total Trades",

            len(history)

        )


        b.metric(

            "Total PnL",

            f"${history.pnl.sum():.2f}"

        )






# ============================================================
# SYSTEM TAB
# ============================================================

with tabs[5]:


    st.subheader(
        "⚙ System Status"
    )


    st.json(

        {

            "Version":
            "SAI AI Forex Intelligence v6.0",


            "Database":
            "SQLite",


            "Architecture":
            "Single Streamlit File",


            "AI Engine":
            "RSI + SMA + Forecast",


            "Region":
            "East Africa"


        }

    )





# ============================================================
# FOOTER
# ============================================================


st.divider()


st.caption(

    "SAI AI Forex Intelligence v6.0 | Autonomous AI Trading Simulation"

)



    return df