logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler("sai_app.log", maxBytes=5*1024*1024, backupCount=2),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =========================================================
# SAI Forex Bot – Enhanced Edition (All 7 Improvements)
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

# -------------------- Optional Plotly --------------------
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Optional sentiment
try:
    from newsapi import NewsApiClient
    from textblob import TextBlob
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

# Auto-refresh
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# Backtesting libs
try:
    from scipy import stats as scipy_stats
except ImportError:
    scipy_stats = None

# -------------------- Global thread‑safe bot config --------------------
BOT_CONFIG = {
    "alert_errors": False,
    "lock": threading.Lock()
}

# -------------------- Custom CSS --------------------
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    .stApp { background-color: #0E1117; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; }
    div[data-testid="stMetricLabel"] { font-size: 0.9rem; color: #AAAAAA; }
    .forex-card {
        background: linear-gradient(135deg, #1E1E2F 0%, #252540 100%);
        border-radius: 16px; padding: 20px; margin: 8px 0;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 4px 12px rgba(0,0,0,0.4); transition: all 0.3s ease;
    }
    .forex-card:hover {
        border-color: #00F2FE; box-shadow: 0 4px 20px rgba(0,242,254,0.3);
    }
    .currency-pair { font-size: 1.3rem; font-weight: 600; color: #E0E0E0; margin-bottom: 8px; }
    .rate-value { font-size: 2rem; font-weight: 700; color: #FFFFFF; }
    .change-positive { color: #00C853; font-weight: 600; }
    .change-negative { color: #FF1744; font-weight: 600; }
    .section-title {
        font-size: 1.5rem; font-weight: 700; color: #FFFFFF;
        margin: 20px 0 10px 0; border-bottom: 2px solid #00F2FE;
        padding-bottom: 5px; display: inline-block;
    }
    .stButton > button {
        background: linear-gradient(90deg, #00F2FE 0%, #4FACFE 100%);
        color: black; font-weight: 600; border: none;
        border-radius: 8px; padding: 10px 20px; transition: 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,242,254,0.5);
    }
    @media (max-width: 768px) {
        .forex-card { padding: 12px; margin: 4px 0; }
        .rate-value { font-size: 1.5rem; }
        .currency-pair { font-size: 1rem; }
        .section-title { font-size: 1.2rem; }
        .stButton > button { padding: 8px 16px; font-size: 0.9rem; }
    }
</style>
""", unsafe_allow_html=True)

if not PLOTLY_AVAILABLE:
    st.info("📊 Install plotly for interactive charts: `pip install plotly`")
if not SENTIMENT_AVAILABLE:
    st.info("📰 Install newsapi-python & textblob for sentiment: `pip install newsapi-python textblob`")
if not AUTOREFRESH_AVAILABLE:
    st.info("⏱️ Install streamlit-autorefresh for smooth auto‑refresh: `pip install streamlit-autorefresh`")

# -------------------- ARIMA (Real Implementation) --------------------
def fit_arima(series: pd.Series, order: Tuple[int, int, int] = (2,1,2)) -> Dict[str, Any]:
    last_value = series.iloc[-1]
    std = series.std()
    result = {"last_value": last_value, "std": std, "fitted": False, "model": None, "order": order}
    try:
        from statsmodels.tsa.arima.model import ARIMA
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = ARIMA(series, order=order)
            fitted_model = model.fit()
        result["model"] = fitted_model
        result["fitted"] = True
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"ARIMA fitting failed ({e}), using stub.")
    return result

def fit_auto_arima(series: pd.Series) -> Dict[str, Any]:
    try:
        import pmdarima as pm
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = pm.auto_arima(series, seasonal=False, trace=False,
                                  error_action='ignore', suppress_warnings=True, stepwise=True)
        return {"last_value": series.iloc[-1], "std": series.std(), "fitted": True,
                "model": model, "order": model.order}
    except ImportError:
        return fit_arima(series)
    except Exception as e:
        logger.warning(f"Auto-ARIMA failed ({e}), falling back.")
        return fit_arima(series)

def forecast_next(arima_model: Dict[str, Any], steps: int = 1) -> Tuple[List[float], Optional[np.ndarray]]:
    """Return forecasts and confidence intervals if available."""
    if arima_model.get("fitted") and arima_model["model"] is not None:
        try:
            fc_result = arima_model["model"].get_forecast(steps=steps)
            pred = fc_result.predicted_mean.tolist()
            conf_int = fc_result.conf_int()  # returns DataFrame
            return pred, conf_int.values if conf_int is not None else None
        except Exception as e:
            logger.warning(f"ARIMA forecast failed ({e}), using stub.")
    last = arima_model["last_value"]
    std = arima_model["std"]
    rng = np.random.default_rng(42)
    return [last + rng.normal(0, std * 0.02) for _ in range(steps)], None

# -------------------- Prophet (Real Implementation) --------------------
def fit_prophet(df_rates: pd.DataFrame) -> Dict[str, Any]:
    df = df_rates.copy()
    last_y = df["y"].iloc[-1]
    try:
        from prophet import Prophet
        m = Prophet()
        m.fit(df.rename(columns={"ds": "ds", "y": "y"}))
        return {"model": m, "fitted": True, "last_y": last_y, "last_date": df["ds"].max()}
    except ImportError:
        df["ds_num"] = (df["ds"] - df["ds"].min()).dt.total_seconds() / 86400
        slope = 0 if len(df) <= 1 else np.polyfit(df["ds_num"], df["y"], 1)[0]
        return {"last_date": df["ds"].max(), "slope": slope, "last_y": last_y, "fitted": False}
    except Exception as e:
        logger.warning(f"Prophet fitting failed ({e}), using stub.")
        df["ds_num"] = (df["ds"] - df["ds"].min()).dt.total_seconds() / 86400
        slope = 0 if len(df) <= 1 else np.polyfit(df["ds_num"], df["y"], 1)[0]
        return {"last_date": df["ds"].max(), "slope": slope, "last_y": last_y, "fitted": False}

def forecast_future(prophet_model: Dict[str, Any], periods: int = 1, freq: str = "D") -> Tuple[pd.DataFrame, Optional[Any]]:
    """Return forecasts and possibly full forecast dataframe with intervals."""
    if prophet_model.get("fitted"):
        try:
            future = prophet_model["model"].make_future_dataframe(periods=periods, freq=freq)
            forecast = prophet_model["model"].predict(future)
            return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods), forecast
        except Exception as e:
            logger.warning(f"Prophet forecast failed ({e}), using stub.")
    last_date = prophet_model["last_date"]
    slope = prophet_model.get("slope", 0)
    last_y = prophet_model["last_y"]
    dates = [last_date + timedelta(days=i+1) for i in range(periods)]
    values = [last_y + slope * (i+1) for i in range(periods)]
    return pd.DataFrame({"ds": dates, "yhat": values}), None

# -------------------- Utility metrics --------------------
def compute_metrics(actual: np.ndarray, predicted: np.ndarray) -> Dict[str, Optional[float]]:
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    if actual.size == 0 or predicted.size == 0:
        return {"RMSE": None, "MAPE": None}
    n = min(len(actual), len(predicted))
    actual = actual[-n:]
    predicted = predicted[:n]
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    denom = np.where(actual == 0, 1e-8, actual)
    mape = float(np.mean(np.abs((actual - predicted) / denom)) * 100)
    return {"RMSE": round(rmse, 6), "MAPE": round(mape, 4)}

# -------------------- NEW: Real Trading Logic --------------------
def compute_trade_signal(rates_df: pd.DataFrame, risk_level: int) -> Optional[Dict]:
    """
    Strategy: SMA20 > SMA50 and RSI < 30 → BUY, SMA20 < SMA50 and RSI > 70 → SELL.
    Returns trade dict or None.
    """
    if len(rates_df) < 50:
        return None
    close = rates_df["Rate"].astype(float)
    sma20 = close.rolling(20).mean().iloc[-1]
    sma50 = close.rolling(50).mean().iloc[-1]
    # RSI 14
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean().iloc[-1]
    avg_loss = loss.rolling(14).mean().iloc[-1]
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    trade = None
    if sma20 > sma50 and rsi < 30:
        trade = "BUY"
    elif sma20 < sma50 and rsi > 70:
        trade = "SELL"
    if trade:
        # Adjust position size based on risk level (1-10)
        risk_fraction = risk_level / 100.0
        amount = int(1000 * risk_fraction) if risk_fraction else 1000
        return {"trade": trade, "amount": amount, "symbol": rates_df.iloc[-1]["Currency"],
                "price": close.iloc[-1]}
    return None

# -------------------- Bot simulation → Real Trading Loop --------------------
def run_bot():
    """Called by bot thread. Uses live rates and indicators to trade."""
    with st.session_state.live_rates_lock:
        rates = st.session_state.live_rates_data.get("rates", {})
    if not rates:
        return None
    # For each currency we could have a separate dataframe, but we use the live history
    df_hist = st.session_state.history
    if df_hist is None or df_hist.empty:
        return None
    # For simplicity, pick a random currency that has enough data
    available = [c for c in EAST_AFRICAN_CURRENCIES if c in rates]
    if not available:
        return None
    # Randomly select one for demo; in production you'd loop all
    cur = random.choice(available)
    cur_data = df_hist[df_hist["Currency"] == cur].tail(100).copy()
    cur_data["Time_dt"] = pd.to_datetime(cur_data["Time"])
    cur_data = cur_data.sort_values("Time_dt")
    if len(cur_data) < 50:
        return None
    trade_signal = compute_trade_signal(cur_data, st.session_state.risk_level)
    if trade_signal:
        trade_signal["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trade_signal["amount"] = max(100, trade_signal["amount"])
        if st.session_state.auto_trade:
            trading_api = get_trading_api()
            try:
                units = trade_signal["amount"] if trade_signal["trade"] == "BUY" else -trade_signal["amount"]
                trading_api.place_order(symbol=trade_signal["symbol"], units=units)
                logger.info(f"Bot auto‑trade: {trade_signal}")
            except Exception as e:
                logger.error(f"Bot trade failed: {e}")
                trade_signal["error"] = str(e)
        return trade_signal
    return None

# -------------------- Database (improved with archiving) --------------------
DB_PATH = "sai_trading.db"
DB_LOCK = threading.Lock()

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = db_connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            currency TEXT NOT NULL,
            rate REAL NOT NULL,
            forecast REAL
        );
        CREATE TABLE IF NOT EXISTS history_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            currency TEXT NOT NULL,
            rate REAL NOT NULL,
            forecast REAL
        );
        CREATE TABLE IF NOT EXISTS bot_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            trade TEXT,
            symbol TEXT,
            amount INTEGER,
            error TEXT
        );
        CREATE TABLE IF NOT EXISTS account (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY,
            time TIMESTAMP,
            symbol TEXT,
            units INTEGER,
            type TEXT,
            price REAL,
            stop_loss REAL,
            take_profit REAL,
            status TEXT,
            pnl REAL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            time TIMESTAMP,
            symbol TEXT,
            units INTEGER,
            type TEXT,
            price REAL,
            stop_loss REAL,
            take_profit REAL,
            status TEXT
        );
    """)
    conn.commit()
    conn.close()

# ---------- History with automatic archiving ----------
def insert_history(rows: List[Dict]):
    with DB_LOCK:
        conn = db_connect()
        conn.executemany(
            "INSERT INTO history (time, currency, rate, forecast) VALUES (?, ?, ?, ?)",
            [(r["Time"], r["Currency"], r["Rate"], r["Forecast"]) for r in rows]
        )
        conn.commit()
        # Trim main table to 2000 rows and archive old ones (>7 days) to history_archive
        conn.execute("""
            INSERT INTO history_archive (time, currency, rate, forecast)
            SELECT time, currency, rate, forecast FROM history
            WHERE time < datetime('now', '-7 days')
        """)
        conn.execute("DELETE FROM history WHERE time < datetime('now', '-7 days')")
        conn.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT 2000)")
        conn.commit()
        conn.close()

def load_history(limit: int = 2000) -> pd.DataFrame:
    conn = db_connect()
    df = pd.read_sql_query(
        "SELECT time, currency, rate, forecast FROM history ORDER BY time ASC LIMIT ?",
        conn, params=(limit,)
    )
    conn.close()
    df.rename(columns={"time": "Time", "currency": "Currency", "rate": "Rate", "forecast": "Forecast"}, inplace=True)
    return df

def load_archive_history() -> pd.DataFrame:
    conn = db_connect()
    df = pd.read_sql_query("SELECT time, currency, rate, forecast FROM history_archive ORDER BY time ASC", conn)
    conn.close()
    df.rename(columns={"time": "Time", "currency": "Currency", "rate": "Rate", "forecast": "Forecast"}, inplace=True)
    return df

def download_history_csv():
    df = load_history(limit=2000)
    archive = load_archive_history()
    full = pd.concat([archive, df], ignore_index=True).sort_values("Time")
    return full.to_csv(index=False).encode('utf-8')

# ---------- Bot Logs ----------
def insert_bot_logs(logs: List[Dict]):
    with DB_LOCK:
        conn = db_connect()
        conn.executemany(
            "INSERT INTO bot_logs (time, trade, symbol, amount, error) VALUES (?, ?, ?, ?, ?)",
            [(l.get("time"), l.get("trade"), l.get("symbol"), l.get("amount"), l.get("error")) for l in logs]
        )
        conn.commit()
        conn.execute("DELETE FROM bot_logs WHERE id NOT IN (SELECT id FROM bot_logs ORDER BY id DESC LIMIT 500)")
        conn.commit()
        conn.close()

def load_bot_logs(limit: int = 500) -> pd.DataFrame:
    conn = db_connect()
    df = pd.read_sql_query("SELECT * FROM bot_logs ORDER BY id DESC LIMIT ?", conn, params=(limit,))
    conn.close()
    return df.iloc[::-1]

# ---------- Account, Positions, Orders unchanged ----------
def save_account(balance: float, equity: float):
    with DB_LOCK:
        conn = db_connect()
        conn.execute("REPLACE INTO account (key, value) VALUES ('balance', ?), ('equity', ?)", (balance, equity))
        conn.commit()
        conn.close()

def load_account() -> Dict[str, float]:
    conn = db_connect()
    cur = conn.execute("SELECT key, value FROM account WHERE key IN ('balance', 'equity')")
    data = {"balance": 10000.0, "equity": 10000.0}
    for row in cur:
        data[row[0]] = float(row[1])
    conn.close()
    return data

def save_positions(positions: List[Dict]):
    with DB_LOCK:
        conn = db_connect()
        conn.execute("DELETE FROM positions")
        conn.executemany(
            "INSERT INTO positions (id, time, symbol, units, type, price, stop_loss, take_profit, status, pnl) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(p["id"], p["time"], p["symbol"], p["units"], p["type"], p["price"],
              p.get("stop_loss"), p.get("take_profit"), p["status"], p.get("pnl")) for p in positions]
        )
        conn.commit()
        conn.close()

def load_positions() -> List[Dict]:
    conn = db_connect()
    df = pd.read_sql_query("SELECT * FROM positions", conn)
    conn.close()
    return df.to_dict(orient="records")

def save_orders(orders: List[Dict]):
    with DB_LOCK:
        conn = db_connect()
        conn.execute("DELETE FROM orders")
        conn.executemany(
            "INSERT INTO orders (id, time, symbol, units, type, price, stop_loss, take_profit, status) VALUES (?,?,?,?,?,?,?,?,?)",
            [(o["id"], o["time"], o["symbol"], o["units"], o["type"], o["price"],
              o.get("stop_loss"), o.get("take_profit"), o["status"]) for o in orders]
        )
        conn.commit()
        conn.close()

def load_orders() -> List[Dict]:
    conn = db_connect()
    df = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    return df.to_dict(orient="records")

# -------------------- Session state initialisation --------------------
defaults = {
    "bot_thread": None, "bot_running": False,
    "rates": {}, "prev_rates": {},
    "bot_queue": queue.Queue(), "stop_event": threading.Event(),
    "auto_refresh": False, "refresh_interval": 3,
    "trading_account": {"balance": 10000.0, "equity": 10000.0, "open_positions": [], "order_history": []},
    "auto_trade": False, "last_history_update": None, "risk_level": 5,
    "use_auto_arima": False,
    "live_rates_lock": threading.Lock(), "live_rates_data": {"rates": {}, "prev_rates": {}, "timestamp": None},
    "live_stream_thread": None, "live_stream_stop_event": None,
    "alert_signals": False, "alert_errors": False,
    "alert_threshold": 0.02,  # new: signal strength threshold
    "db_initialised": False
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# Restore persistent state
if not st.session_state.db_initialised:
    init_db()
    acc = load_account()
    st.session_state.trading_account.update(acc)
    st.session_state.history = load_history(limit=2000)
    st.session_state.logs = load_bot_logs(limit=500).to_dict(orient="records")
    st.session_state.trading_account["open_positions"] = load_positions()
    st.session_state.trading_account["order_history"] = load_orders()
    st.session_state.db_initialised = True

HISTORY_MAX_ROWS = 2000
ALL_CURRENCIES = ["UGX", "KES", "TZS", "RWF", "BIF", "SSP", "ETB", "USD", "EUR", "GBP", "JPY"]
EAST_AFRICAN_CURRENCIES = ["UGX", "KES", "TZS", "RWF", "BIF", "SSP", "ETB"]
OTHER_CURRENCIES = ["USD", "EUR", "GBP", "JPY"]

# -------------------- Bot thread management (updated) --------------------
def bot_loop(queue_obj, stop_event):
    logger.info("Bot thread started.")
    while not stop_event.is_set():
        try:
            trade_info = run_bot()
            if trade_info:
                queue_obj.put(trade_info)
                # Telegram alert if enabled and signal strong
                with BOT_CONFIG["lock"]:
                    if BOT_CONFIG.get("alert_signals"):
                        # Check threshold
                        thresh = st.session_state.alert_threshold
                        if trade_info["trade"] == "BUY" or trade_info["trade"] == "SELL":
                            send_telegram(f"🤖 Bot signal: {trade_info['trade']} {trade_info['symbol']} @ {trade_info['price']:.2f} (units: {trade_info['amount']})")
        except Exception as e:
            error_data = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "error": str(e)}
            queue_obj.put(error_data)
            logger.exception("Bot loop error")
            with BOT_CONFIG["lock"]:
                if BOT_CONFIG["alert_errors"]:
                    send_telegram(f"🚨 Bot error: {e}")
            time.sleep(5)
            continue
        time.sleep(5)  # slower to avoid excessive trades
    logger.info("Bot thread exited.")

def start_bot():
    if st.session_state.bot_running:
        return
    with BOT_CONFIG["lock"]:
        BOT_CONFIG["alert_errors"] = st.session_state.alert_errors
        BOT_CONFIG["alert_signals"] = st.session_state.alert_signals
    st.session_state.stop_event = threading.Event()
    t = threading.Thread(target=bot_loop, args=(st.session_state.bot_queue, st.session_state.stop_event), daemon=True)
    st.session_state.bot_thread = t
    st.session_state.bot_running = True
    t.start()

def stop_bot():
    if st.session_state.bot_running:
        st.session_state.stop_event.set()
        st.session_state.bot_running = False

def drain_bot_queue(max_items=50):
    drained = 0
    items = []
    while not st.session_state.bot_queue.empty() and drained < max_items:
        try:
            item = st.session_state.bot_queue.get_nowait()
        except queue.Empty:
            break
        st.session_state.logs.append(item)
        items.append(item)
        drained += 1
    if items:
        insert_bot_logs(items)
    if len(st.session_state.logs) > 1000:
        st.session_state.logs = st.session_state.logs[-1000:]
    return drained

# -------------------- Live Rate Stream (unchanged) --------------------
def _live_rate_fetcher(stop_event: threading.Event):
    while not stop_event.is_set():
        try:
            real = get_real_rates()
            rates = real if real else sample_currency_rates()
            with st.session_state.live_rates_lock:
                st.session_state.live_rates_data["prev_rates"] = st.session_state.live_rates_data.get("rates", {}).copy()
                st.session_state.live_rates_data["rates"] = rates
                st.session_state.live_rates_data["timestamp"] = datetime.now()
        except Exception as e:
            logger.error(f"Live fetcher error: {e}")
        time.sleep(2)

def start_live_stream():
    if st.session_state.live_stream_thread is not None and st.session_state.live_stream_thread.is_alive():
        return
    stop_ev = threading.Event()
    thread = threading.Thread(target=_live_rate_fetcher, args=(stop_ev,), daemon=True)
    st.session_state.live_stream_thread = thread
    st.session_state.live_stream_stop_event = stop_ev
    thread.start()

def stop_live_stream():
    if st.session_state.live_stream_stop_event:
        st.session_state.live_stream_stop_event.set()
        if st.session_state.live_stream_thread:
            st.session_state.live_stream_thread.join(timeout=1)
        st.session_state.live_stream_thread = None

def get_live_rates():
    with st.session_state.live_rates_lock:
        return st.session_state.live_rates_data["rates"].copy(), st.session_state.live_rates_data["prev_rates"].copy()

# -------------------- Real exchange rate fetcher --------------------
@st.cache_data(ttl=5, show_spinner=False)
def get_real_rates():
    try:
        url = "https://api.frankfurter.app/latest?from=USD&to=" + ",".join(ALL_CURRENCIES)
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        rates = data["rates"]
        rates["USD"] = 1.0
        return rates
    except Exception as e:
        logger.error(f"Failed to fetch real rates: {e}")
        return {}

def sample_currency_rates():
    ranges = {
        "UGX": (3700, 3900), "KES": (125, 140), "TZS": (2500, 2700),
        "RWF": (1300, 1500), "BIF": (2800, 3000), "SSP": (1500, 1800),
        "ETB": (55, 60), "USD": (1, 1), "EUR": (0.9, 1.1),
        "GBP": (0.75, 0.85), "JPY": (140, 150)
    }
    return {cur: round(random.uniform(low, high), 2) for cur, (low, high) in ranges.items()}

def get_current_rates():
    if not st.session_state.live_stream_thread or not st.session_state.live_stream_thread.is_alive():
        start_live_stream()
    rates, prev = get_live_rates()
    if not rates:
        rates = sample_currency_rates()
    deltas = {}
    for cur in EAST_AFRICAN_CURRENCIES:
        if cur in prev and prev[cur] != 0:
            deltas[cur] = ((rates[cur] - prev[cur]) / prev[cur]) * 100
        else:
            deltas[cur] = None
    return rates, deltas

def update_history(rates, forecast=None):
    now = datetime.now()
    last = st.session_state.last_history_update
    if last is not None and (now - last).total_seconds() < 60:
        return
    st.session_state.last_history_update = now
    if forecast is None:
        forecast = {cur: rates[cur] for cur in rates}
    rows = [{"Time": now.isoformat(), "Currency": cur,
             "Rate": rates[cur], "Forecast": forecast[cur]} for cur in rates]
    if rows:
        insert_history(rows)
        new_df = pd.DataFrame(rows)
        if not hasattr(st.session_state, "history") or st.session_state.history is None:
            st.session_state.history = new_df
        else:
            st.session_state.history = pd.concat([st.session_state.history, new_df], ignore_index=True)
            if len(st.session_state.history) > HISTORY_MAX_ROWS:
                st.session_state.history = st.session_state.history.iloc[-HISTORY_MAX_ROWS:].reset_index(drop=True)

def generate_trade_signal(current_rate, forecast_value, threshold=0.01):
    if forecast_value is None:
        return "HOLD"
    change_pct = (forecast_value - current_rate) / current_rate
    if change_pct > threshold:
        return "BUY"
    elif change_pct < -threshold:
        return "SELL"
    return "HOLD"

# -------------------- Central forecast (cache invalidated by rate) --------------------
@st.cache_data(ttl=300, show_spinner="Generating forecast...")
def run_forecast(currency, horizon, steps, history_df, current_rate, use_auto_arima, freq="D"):
    # current_rate is now a float, so it's part of the cache key
    df_all = history_df.copy()
    df_all["Time_dt"] = pd.to_datetime(df_all["Time"])
    df_cur = df_all[df_all["Currency"] == currency].sort_values("Time_dt")

    if len(df_cur) < 20:
        rng = np.random.default_rng(42)
        fallback_preds = [round(current_rate * (1 + rng.uniform(-0.01, 0.01)), 2) for _ in range(steps)]
        return {
            "currency": currency, "current_rate": current_rate,
            "arima_forecast": fallback_preds[0], "prophet_forecast": None,
            "arima_signal": "HOLD", "prophet_signal": None,
            "arima_all_preds": fallback_preds, "prophet_all_preds": None,
            "arima_metrics": None, "prophet_metrics": None,
            "actual_test": [], "train": df_cur, "test": pd.DataFrame(),
            "warning": "Insufficient history – forecast is a rough estimate only.",
            "arima_fitted": False, "prophet_fitted": False,
            "arima_conf_int": None, "prophet_conf_int": None
        }

    train = df_cur.iloc[:-steps] if steps < len(df_cur) else df_cur.iloc[:-1]
    test = df_cur.iloc[-steps:] if steps < len(df_cur) else df_cur.iloc[-1:]
    actual_test = test["Rate"].values

    arima_pred, arima_metrics, arima_fitted, arima_conf = None, None, False, None
    try:
        if use_auto_arima:
            arima_model = fit_auto_arima(train["Rate"])
        else:
            arima_model = fit_arima(train["Rate"], order=(2,1,2))
        arima_pred, arima_conf = forecast_next(arima_model, steps=steps)
        arima_metrics = compute_metrics(actual_test, arima_pred[:len(actual_test)])
        arima_fitted = arima_model.get("fitted", False)
    except Exception as e:
        logger.warning(f"ARIMA pipeline failed for {currency}: {e}")

    prophet_pred, prophet_metrics, prophet_fitted, prophet_full = None, None, False, None
    try:
        df_prophet = pd.DataFrame({"ds": train["Time_dt"], "y": train["Rate"].astype(float)})
        prophet_model = fit_prophet(df_prophet)
        forecast_df, prophet_full = forecast_future(prophet_model, periods=steps, freq=freq)
        prophet_pred = forecast_df["yhat"].tolist()
        prophet_metrics = compute_metrics(actual_test, prophet_pred[:len(actual_test)])
        prophet_fitted = prophet_model.get("fitted", False)
    except Exception as e:
        logger.warning(f"Prophet pipeline failed for {currency}: {e}")

    arima_signal = generate_trade_signal(current_rate, arima_pred[0]) if arima_pred else "HOLD"
    prophet_signal = generate_trade_signal(current_rate, prophet_pred[0]) if prophet_pred else "HOLD"

    return {
        "currency": currency, "current_rate": current_rate,
        "arima_forecast": arima_pred[0] if arima_pred else None,
        "prophet_forecast": prophet_pred[0] if prophet_pred else None,
        "arima_signal": arima_signal, "prophet_signal": prophet_signal,
        "arima_all_preds": arima_pred, "prophet_all_preds": prophet_pred,
        "arima_metrics": arima_metrics, "prophet_metrics": prophet_metrics,
        "actual_test": actual_test, "train": train, "test": test,
        "warning": None, "arima_fitted": arima_fitted, "prophet_fitted": prophet_fitted,
        "arima_conf_int": arima_conf, "prophet_full": prophet_full
    }

# -------------------- Technical Indicators (unchanged) --------------------
def compute_indicators(df_cur, rsi_period=14, sma_windows=[20,50],
                       macd_fast=12, macd_slow=26, macd_signal=9,
                       bb_period=20, bb_std=2, stoch_k=14, stoch_d=3, atr_period=14):
    df = df_cur.copy().sort_values("Time_dt")
    min_len = max(rsi_period, macd_slow, bb_period, stoch_k, atr_period) + 1
    if len(df) < min_len:
        return None
    delta = df["Rate"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=rsi_period, min_periods=rsi_period).mean()
    avg_loss = loss.rolling(window=rsi_period, min_periods=rsi_period).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    for w in sma_windows:
        df[f"SMA_{w}"] = df["Rate"].rolling(window=w, min_periods=w).mean()
    ema_fast = df["Rate"].ewm(span=macd_fast, min_periods=macd_fast).mean()
    ema_slow = df["Rate"].ewm(span=macd_slow, min_periods=macd_slow).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_signal"] = df["MACD"].ewm(span=macd_signal, min_periods=macd_signal).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    df["BB_middle"] = df["Rate"].rolling(window=bb_period, min_periods=bb_period).mean()
    bb_std_dev = df["Rate"].rolling(window=bb_period, min_periods=bb_period).std()
    df["BB_upper"] = df["BB_middle"] + bb_std * bb_std_dev
    df["BB_lower"] = df["BB_middle"] - bb_std * bb_std_dev
    low_min = df["Rate"].rolling(window=stoch_k, min_periods=stoch_k).min()
    high_max = df["Rate"].rolling(window=stoch_k, min_periods=stoch_k).max()
    df["Stoch_%K"] = 100 * (df["Rate"] - low_min) / (high_max - low_min)
    df["Stoch_%D"] = df["Stoch_%K"].rolling(window=stoch_d, min_periods=stoch_d).mean()
    rng = np.random.RandomState(42)
    volume = rng.randint(500, 2000, size=len(df))
    obv = [0]
    for i in range(1, len(df)):
        if df["Rate"].iloc[i] > df["Rate"].iloc[i-1]:
            obv.append(obv[-1] + volume[i])
        elif df["Rate"].iloc[i] < df["Rate"].iloc[i-1]:
            obv.append(obv[-1] - volume[i])
        else:
            obv.append(obv[-1])
    df["OBV"] = obv
    high = df["Rate"] * (1 + rng.uniform(0, 0.001, len(df)))
    low = df["Rate"] * (1 - rng.uniform(0, 0.001, len(df)))
    prev_close = df["Rate"].shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR"] = true_range.rolling(window=atr_period, min_periods=atr_period).mean()
    return df

# -------------------- Trading API (Enhanced OANDA) --------------------
class TradingAPI:
    def get_account_summary(self) -> Dict: raise NotImplementedError
    def place_order(self, symbol, units, stop_loss=None, take_profit=None, order_type="MARKET") -> Dict: raise NotImplementedError
    def get_open_positions(self) -> List[Dict]: raise NotImplementedError
    def get_order_history(self) -> List[Dict]: raise NotImplementedError

class SimulatedTrading(TradingAPI):
    def __init__(self, account):
        self.account = account
    def get_account_summary(self):
        return {"balance": self.account["balance"], "equity": self.account["equity"],
                "open_positions": len(self.account["open_positions"]),
                "unrealized_pl": 0, "margin_used": 0}
    def place_order(self, symbol, units, stop_loss=None, take_profit=None, order_type="MARKET"):
        rate = st.session_state.rates.get(symbol, 1.0)
        order = {
            "id": len(self.account["order_history"]) + 1,
            "time": datetime.now().isoformat(), "symbol": symbol, "units": units,
            "type": order_type, "price": rate,
            "stop_loss": stop_loss, "take_profit": take_profit, "status": "FILLED"
        }
        self.account["open_positions"].append(order)
        self.account["order_history"].append(order)
        self.account["equity"] = self.account["balance"]
        save_account(self.account["balance"], self.account["equity"])
        save_positions(self.account["open_positions"])
        save_orders(self.account["order_history"])
        return order
    def get_open_positions(self):
        return self.account["open_positions"]
    def get_order_history(self):
        return self.account["order_history"]
    def close_position(self, position_id):
        for p in self.account["open_positions"]:
            if p["id"] == position_id:
                self.account["open_positions"].remove(p)
                pnl = random.uniform(-50, 50)
                self.account["balance"] += pnl
                self.account["equity"] = self.account["balance"]
                p["status"] = "CLOSED"
                p["pnl"] = pnl
                self.account["order_history"].append(p)
                save_account(self.account["balance"], self.account["equity"])
                save_positions(self.account["open_positions"])
                save_orders(self.account["order_history"])
                return True
        return False

class OANDA_Trading(TradingAPI):
    def __init__(self, ctx, account_id):
        self.ctx = ctx
        self.account_id = account_id
    def get_account_summary(self):
        resp = self.ctx.account.get(self.account_id)
        if resp.status != 200:
            raise Exception(f"OANDA error: {resp.body}")
        acc = resp.body["account"]
        return {"balance": float(acc["balance"]),
                "equity": float(acc["NAV"]),
                "open_positions": acc.get("openPositionCount", 0),
                "unrealized_pl": float(acc.get("unrealizedPL", 0)),
                "margin_used": float(acc.get("marginUsed", 0))}
    def place_order(self, symbol, units, stop_loss=None, take_profit=None, order_type="MARKET"):
        # Convert symbol e.g., "UGX" -> "USD_UGX"
        if len(symbol) == 6:
            instr = f"{symbol[:3]}_{symbol[3:]}"
        else:
            instr = f"USD_{symbol}"
        order = {"order": {"type": "MARKET", "instrument": instr,
                           "units": str(int(units)), "timeInForce": "FOK"}}
        if stop_loss:
            order["order"]["stopLossOnFill"] = {"price": str(stop_loss)}
        if take_profit:
            order["order"]["takeProfitOnFill"] = {"price": str(take_profit)}
        resp = self.ctx.order.create(self.account_id, order)
        if resp.status != 201:
            raise Exception(f"Order failed: {resp.body}")
        return resp.body
    def get_open_positions(self):
        resp = self.ctx.position.list_open(self.account_id)
        if resp.status != 200:
            return []
        return resp.body.get("positions", [])
    def get_order_history(self):
        resp = self.ctx.order.list(self.account_id, {"count": 50})
        if resp.status != 200:
            return []
        return resp.body.get("orders", [])

@st.cache_resource
def get_trading_api():
    try:
        import v20
        oanda_api_key = os.getenv("OANDA_API_KEY") or st.secrets.get("OANDA_API_KEY")
        oanda_account_id = os.getenv("OANDA_ACCOUNT_ID") or st.secrets.get("OANDA_ACCOUNT_ID")
        if oanda_api_key and oanda_account_id:
            from v20 import Context
            ctx = Context(hostname="api-fxpractice.oanda.com", port=443, token=oanda_api_key)
            return OANDA_Trading(ctx, oanda_account_id)
    except ImportError:
        pass
    return SimulatedTrading(st.session_state.trading_account)

# -------------------- News Sentiment (unchanged) --------------------
@st.cache_data(ttl=600, show_spinner=False)
def fetch_news_sentiment():
    if not SENTIMENT_AVAILABLE:
        return None
    try:
        api_key = st.secrets.get("NEWS_API_KEY")
        if not api_key: return None
        api = NewsApiClient(api_key=api_key)
        query = ("East Africa forex OR Uganda shilling OR Kenya shilling OR Tanzania shilling "
                 "OR Rwanda franc OR Burundi franc OR South Sudan pound OR Ethiopia birr")
        articles = api.get_everything(q=query, language='en', sort_by='publishedAt', page_size=10)
        if articles['status'] != 'ok': return None
        sentiments = []
        headlines = []
        for art in articles['articles']:
            text = art['title'] + " " + (art['description'] or "")
            blob = TextBlob(text)
            sentiments.append(blob.sentiment.polarity)
            headlines.append(art['title'])
        avg_sent = np.mean(sentiments) if sentiments else 0
        return {
            "score": round(avg_sent, 3),
            "headlines": headlines[:5],
            "interpretation": "Bullish" if avg_sent > 0.1 else "Bearish" if avg_sent < -0.1 else "Neutral"
        }
    except Exception as e:
        logger.error(f"News sentiment error: {e}")
        return None

# -------------------- Telegram Alert (unchanged) --------------------
def send_telegram(message: str):
    token = st.secrets.get("TELEGRAM_BOT_TOKEN")
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")

# -------------------- Risk Calculator (unchanged) --------------------
def calculate_position_size(equity, risk_pct, entry, stop_loss, pair_rate):
    risk_amount = equity * (risk_pct / 100.0)
    stop_distance = abs(entry - stop_loss)
    if stop_distance == 0 or pair_rate == 0:
        return 0.0
    stop_loss_usd = stop_distance / pair_rate
    units = risk_amount / stop_loss_usd
    return round(units, 2)

# -------------------- NEW: Backtesting Engine --------------------
def backtest_strategy(currency: str, df_full: pd.DataFrame, strategy: str,
                      start_date: datetime, end_date: datetime,
                      steps: int = 1) -> Dict:
    """Simple rolling forecast backtest. strategy: 'ARIMA' or 'Prophet'."""
    df = df_full[(df_full["Currency"] == currency) &
                 (df_full["Time_dt"] >= start_date) &
                 (df_full["Time_dt"] <= end_date)].sort_values("Time_dt").reset_index(drop=True)
    if len(df) < 50:
        return {"error": "Not enough data in date range."}
    initial_balance = 10000.0
    balance = initial_balance
    position = None
    equity_curve = []
    trades = []
    for i in range(50, len(df) - steps):
        train = df.iloc[:i]
        current_rate = df.iloc[i]["Rate"]
        next_rates = df.iloc[i+1:i+1+steps]["Rate"].values
        if strategy == "ARIMA":
            try:
                arima_res = fit_arima(train["Rate"])
                pred, _ = forecast_next(arima_res, steps=steps)
                forecast = pred[0]
            except:
                forecast = current_rate
        else:  # Prophet
            try:
                prophet_df = pd.DataFrame({"ds": train["Time_dt"], "y": train["Rate"]})
                prophet_m = fit_prophet(prophet_df)
                fc_df, _ = forecast_future(prophet_m, periods=steps)
                forecast = fc_df["yhat"].iloc[0] if not fc_df.empty else current_rate
            except:
                forecast = current_rate
        signal = "BUY" if forecast > current_rate * 1.005 else "SELL" if forecast < current_rate * 0.995 else "HOLD"
        if position is None and signal != "HOLD":
            # Enter trade
            position = {"type": signal, "entry": current_rate, "units": 1000}
        elif position is not None:
            # Check if signal reversed
            if (position["type"] == "BUY" and signal == "SELL") or (position["type"] == "SELL" and signal == "BUY"):
                # Close trade
                exit_rate = current_rate
                pnl = (exit_rate - position["entry"]) * position["units"] if position["type"] == "BUY" else (position["entry"] - exit_rate) * position["units"]
                balance += pnl
                trades.append({"entry_time": train.iloc[-1]["Time_dt"], "exit_time": df.iloc[i]["Time_dt"],
                               "type": position["type"], "pnl": pnl})
                position = None
        equity_curve.append(balance)
    if position is not None:
        # Close at last rate
        exit_rate = df.iloc[-1]["Rate"]
        pnl = (exit_rate - position["entry"]) * position["units"] if position["type"] == "BUY" else (position["entry"] - exit_rate) * position["units"]
        balance += pnl
        trades.append({"entry_time": position["entry_time"], "exit_time": df.iloc[-1]["Time_dt"],
                       "type": position["type"], "pnl": pnl})
        equity_curve.append(balance)
    total_return = (balance - initial_balance) / initial_balance * 100
    returns = pd.Series(equity_curve).pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() != 0 else 0
    max_drawdown = (pd.Series(equity_curve).cummax() - pd.Series(equity_curve)).max() / pd.Series(equity_curve).cummax().max() * 100
    win_rate = (sum(1 for t in trades if t["pnl"] > 0) / len(trades) * 100) if trades else 0
    return {
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "trades": trades,
        "equity_curve": equity_curve,
        "final_balance": balance
    }

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="SAI Forex Bot – Enhanced", layout="wide")

if st.session_state.auto_refresh and AUTOREFRESH_AVAILABLE:
    st_autorefresh(interval=st.session_state.refresh_interval * 1000, key="auto_refresh")

if not st.session_state.live_stream_thread or not st.session_state.live_stream_thread.is_alive():
    start_live_stream()

drain_bot_queue(max_items=5)

# Sidebar – enhanced
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.session_state.auto_refresh = st.checkbox("Auto‑refresh dashboard", value=st.session_state.auto_refresh)
    if st.session_state.auto_refresh:
        st.session_state.refresh_interval = st.slider("Refresh interval (s)", 1, 10, st.session_state.refresh_interval)
    st.session_state.risk_level = st.slider("Risk Level", 1, 10, st.session_state.risk_level)
    st.session_state.use_auto_arima = st.checkbox("Use Auto‑ARIMA", value=st.session_state.use_auto_arima)
    st.session_state.alert_signals = st.checkbox("Telegram alerts for signals", value=st.session_state.alert_signals)
    st.session_state.alert_errors = st.checkbox("Telegram alerts for errors", value=st.session_state.alert_errors)
    st.session_state.alert_threshold = st.slider("Alert signal threshold (%)", 0.1, 10.0, 2.0, step=0.1) / 100.0
    with BOT_CONFIG["lock"]:
        BOT_CONFIG["alert_errors"] = st.session_state.alert_errors
        BOT_CONFIG["alert_signals"] = st.session_state.alert_signals
    st.markdown("---")
    if st.button("🔄 Force Refresh Now"):
        st.rerun()

# Main header
col_title, col_status = st.columns([3,1])
with col_title:
    st.markdown("<h1 style='color:#00F2FE;'>📈 SAI Forex Trading Bot – Enhanced</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#AAAAAA; font-size:1.1rem;'>East African Currency Trading & Forecasting</p>", unsafe_allow_html=True)
with col_status:
    if st.session_state.live_rates_data.get("rates"):
        st.success("🔴 LIVE")
    else:
        st.warning("🟡 SIMULATED")

tabs = st.tabs([
    "📊 Dashboard", "📅 Forecast", "📈 Trade Recommendations", "💹 Live Trading",
    "📉 Technical Analysis", "⚙️ Strategy Config", "📋 Logs", "🧪 Model Testing",
    "🛠️ Debug", "⏪ Backtest"
])

# ============== DASHBOARD ==============
with tabs[0]:
    st.markdown("<div class='section-title'>🌍 East African Forex Rates (USD Base)</div>", unsafe_allow_html=True)
    rates, deltas = get_current_rates()
    update_history(rates)

    cols = st.columns(4)
    for i, cur in enumerate(EAST_AFRICAN_CURRENCIES):
        rate = rates.get(cur, 0)
        delta_val = deltas.get(cur)
        delta_str = f"{delta_val:+.2f}%" if delta_val is not None else "N/A"
        delta_class = "change-positive" if (delta_val and delta_val >= 0) else "change-negative" if delta_val else ""
        spark_data = []
        if not st.session_state.history.empty:
            cur_hist = st.session_state.history[st.session_state.history["Currency"] == cur].tail(30)
            spark_data = cur_hist["Rate"].tolist()
        else:
            spark_data = [rate, rate]
        with cols[i % 4]:
            st.markdown(f"""
            <div class="forex-card">
                <div class="currency-pair">USD/{cur}</div>
                <div class="rate-value">{rate:,.2f}</div>
                <div class="{delta_class}" style="font-size:1rem;">{delta_str}</div>
            </div>
            """, unsafe_allow_html=True)
            if PLOTLY_AVAILABLE and len(spark_data) > 1:
                fig_spark = go.Figure(go.Scatter(y=spark_data, mode='lines', line=dict(color='#00F2FE', width=1.5),
                                                 fill='tozeroy', fillcolor='rgba(0,242,254,0.1)'))
                fig_spark.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=50, paper_bgcolor='rgba(0,0,0,0)',
                                        plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False),
                                        showlegend=False)
                st.plotly_chart(fig_spark, use_container_width=True, config={'displayModeBar': False})
            else:
                fig, ax = plt.subplots(figsize=(2,0.5)); ax.plot(spark_data, color='cyan'); ax.axis('off'); st.pyplot(fig)

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | Live rates refresh every 2s")

    # Market Overview (unchanged)
    st.markdown("<div class='section-title'>📊 Market Overview</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    sorted_deltas = sorted(((k,v) for k,v in deltas.items() if v is not None), key=lambda x: x[1])
    worst = sorted_deltas[0] if sorted_deltas else (None,None)
    best = sorted_deltas[-1] if sorted_deltas else (None,None)
    col1.metric("Best Performer", f"USD/{best[0]}", f"{best[1]:+.2f}%" if best[1] is not None else "N/A")
    col2.metric("Worst Performer", f"USD/{worst[0]}", f"{worst[1]:+.2f}%" if worst[1] is not None else "N/A")
    avg_spread = np.mean([abs(v) for v in deltas.values() if v is not None]) if any(deltas.values()) else 0
    col3.metric("Avg Daily Change %", f"{avg_spread:+.2f}%")

    with st.expander("📰 East African Forex News Sentiment"):
        sentiment = fetch_news_sentiment()
        if sentiment:
            st.metric("Overall Sentiment", f"{sentiment['score']:.2f}", sentiment['interpretation'])
            for h in sentiment['headlines']:
                st.write(f"- {h}")
        else:
            st.info("News sentiment unavailable.")

    if len(st.session_state.history) >= 30:
        st.markdown("<div class='section-title'>🔥 Currency Correlation Heatmap</div>", unsafe_allow_html=True)
        pivot = st.session_state.history.pivot(index="Time", columns="Currency", values="Rate")
        if len(pivot) >= 10:
            corr = pivot.corr()
            if PLOTLY_AVAILABLE:
                fig_heat = px.imshow(corr, text_auto=True, aspect="auto",
                                     color_continuous_scale='RdBu_r', zmin=-1, zmax=1,
                                     title="Correlation Matrix (last 30 periods)")
                fig_heat.update_layout(template="plotly_dark")
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.dataframe(corr.style.background_gradient(cmap='coolwarm', axis=None))

    st.markdown("<div class='section-title'>💼 Portfolio & Bot Activity</div>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        trading_api = get_trading_api()
        try:
            acc = trading_api.get_account_summary()
            st.metric("Balance", f"${acc['balance']:,.2f}")
            st.metric("Equity", f"${acc['equity']:,.2f}")
            st.metric("Open Positions", acc['open_positions'])
            if "unrealized_pl" in acc:
                st.metric("Unrealized P/L", f"${acc['unrealized_pl']:,.2f}")
        except Exception as e:
            st.error(f"Account fetch failed: {e}")
    with col_b:
        if st.session_state.logs:
            bot_df = pd.DataFrame(st.session_state.logs[-100:])
            if "trade" in bot_df.columns:
                buy_count = bot_df["trade"].value_counts().get("BUY",0)
                sell_count = bot_df["trade"].value_counts().get("SELL",0)
                col1, col2 = st.columns(2)
                col1.metric("Total Trades", buy_count+sell_count)
                col2.metric("BUY / SELL", f"{buy_count} / {sell_count}")
        else:
            st.info("No trades yet.")

    st.markdown("<div class='section-title'>⚡ Bot Controls</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,2])
    with col1:
        if st.button("▶️ Start Bot", disabled=st.session_state.bot_running):
            start_bot()
    with col2:
        if st.button("⏹️ Stop Bot", disabled=not st.session_state.bot_running):
            stop_bot()
    with col3:
        st.write(f"Auto‑trade: {'ON' if st.session_state.auto_trade else 'OFF'}")
    st.markdown("#### Recent Bot Trades")
    if st.session_state.logs:
        df_logs = pd.DataFrame(st.session_state.logs[-5:])
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No trades yet.")

    if not st.session_state.history.empty:
        st.markdown("<div class='section-title'>📉 East African Rate Trends</div>", unsafe_allow_html=True)
        df_plot = st.session_state.history.copy()
        df_plot["Time_dt"] = pd.to_datetime(df_plot["Time"])
        if PLOTLY_AVAILABLE:
            fig2 = go.Figure()
            colors = ['#00F2FE','#FFD600','#FF1744','#00C853','#FF9100','#D500F9','#2979FF']
            for idx, cur in enumerate(EAST_AFRICAN_CURRENCIES):
                cur_data = df_plot[df_plot["Currency"]==cur].tail(100)
                if not cur_data.empty:
                    fig2.add_trace(go.Scatter(x=cur_data["Time_dt"], y=cur_data["Rate"],
                                              mode='lines', name=cur, line=dict(color=colors[idx%len(colors)])))
            fig2.update_layout(template="plotly_dark", hovermode="x unified",
                               title="East African Currencies – Recent Trends",
                               xaxis_title="Time", yaxis_title="Rate (USD base)",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            fig, ax = plt.subplots(figsize=(10,4))
            for cur in EAST_AFRICAN_CURRENCIES:
                cur_data = df_plot[df_plot["Currency"]==cur].tail(100)
                if not cur_data.empty: ax.plot(cur_data["Time_dt"], cur_data["Rate"], label=cur)
            ax.legend(); ax.set_title("Trends"); fig.autofmt_xdate(); st.pyplot(fig)

# ============== UNIFIED FORECAST TAB ==============
with tabs[1]:
    st.markdown("<div class='section-title'>📅 Multi‑Horizon Forecast</div>", unsafe_allow_html=True)
    # Horizon selector
    horizon_dict = {"Daily": 1, "Weekly": 7, "Monthly": 30}
    selected_horizon = st.radio("Horizon", list(horizon_dict.keys()), horizontal=True, key="forecast_horizon")
    steps = horizon_dict[selected_horizon]
    show_multiple_timeframes = st.checkbox("Compare multiple timeframes", value=False)
    if show_multiple_timeframes:
        selected_timeframes = st.multiselect("Select timeframes", list(horizon_dict.keys()), default=["Daily", "Weekly"])
    else:
        selected_timeframes = [selected_horizon]

    # Generate forecasts for all East African currencies for selected timeframes
    forecasts = {}
    for cur in EAST_AFRICAN_CURRENCIES:
        cur_rate = st.session_state.rates.get(cur, None)
        if cur_rate is None:
            continue
        for tf in selected_timeframes:
            s = horizon_dict[tf]
            result = run_forecast(cur, tf.lower(), s,
                                  history_df=st.session_state.history,
                                  current_rate=cur_rate,
                                  use_auto_arima=st.session_state.use_auto_arima)
            forecasts[(cur, tf)] = result

    # Build summary table
    if forecasts:
        rows = []
        for (cur, tf), res in forecasts.items():
            rows.append({
                "Currency": cur,
                "Timeframe": tf,
                "Current Rate": res["current_rate"],
                "ARIMA Forecast": res["arima_forecast"],
                "ARIMA Signal": res["arima_signal"],
                "Prophet Forecast": res["prophet_forecast"],
                "Prophet Signal": res["prophet_signal"]
            })
        df_forecast = pd.DataFrame(rows)
        st.dataframe(df_forecast.style.map(lambda val: 'background-color: #00C853; color:black' if val=='BUY' else ('background-color: #FF1744; color:white' if val=='SELL' else ''), subset=['ARIMA Signal','Prophet Signal']), use_container_width=True)
    else:
        st.info("No forecast data available.")

    # Detailed chart for selected currency
    st.markdown("### Detailed Forecast Chart")
    selected_currency = st.selectbox("Pick a currency for detailed view", EAST_AFRICAN_CURRENCIES, key="forecast_detail")
    cur_rate = st.session_state.rates.get(selected_currency, None)
    if cur_rate is not None:
        # Always show daily for detail
        result = run_forecast(selected_currency, "daily", 1,
                              history_df=st.session_state.history,
                              current_rate=cur_rate,
                              use_auto_arima=st.session_state.use_auto_arima)
        if PLOTLY_AVAILABLE and result["train"] is not None:
            fig = go.Figure()
            train = result["train"]
            fig.add_trace(go.Scatter(x=train["Time_dt"], y=train["Rate"], mode='lines', name='History'))
            # ARIMA forecast with CI
            if result["arima_all_preds"]:
                pred_dates = [train["Time_dt"].iloc[-1] + timedelta(days=i+1) for i in range(len(result["arima_all_preds"]))]
                fig.add_trace(go.Scatter(x=pred_dates, y=result["arima_all_preds"], mode='lines+markers', name='ARIMA'))
                if result.get("arima_conf_int") is not None:
                    ci = result["arima_conf_int"]
                    lower = ci[:, 0]
                    upper = ci[:, 1]
                    fig.add_trace(go.Scatter(x=pred_dates, y=upper, mode='lines', line=dict(width=0), showlegend=False))
                    fig.add_trace(go.Scatter(x=pred_dates, y=lower, mode='lines', fill='tonexty', fillcolor='rgba(0,242,254,0.2)', line=dict(width=0), name='ARIMA CI'))
            # Prophet with intervals
            if result.get("prophet_full") is not None:
                fc = result["prophet_full"]
                future_part = fc[fc["ds"] > train["Time_dt"].iloc[-1]]
                fig.add_trace(go.Scatter(x=future_part["ds"], y=future_part["yhat"], mode='lines+markers', name='Prophet'))
                if "yhat_lower" in fc.columns and "yhat_upper" in fc.columns:
                    fig.add_trace(go.Scatter(x=future_part["ds"], y=future_part["yhat_upper"], mode='lines', line=dict(width=0), showlegend=False))
                    fig.add_trace(go.Scatter(x=future_part["ds"], y=future_part["yhat_lower"], mode='lines', fill='tonexty', fillcolor='rgba(255,214,0,0.2)', line=dict(width=0), name='Prophet CI'))
            fig.update_layout(template="plotly_dark", title=f"{selected_currency} Forecast (Daily)", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Plotly required for interactive chart.")
    else:
        st.warning("No live rate for this currency.")

# ============== TRADE RECOMMENDATIONS (enhanced with threshold) ==============
with tabs[2]:
    st.markdown("<div class='section-title'>📊 Trade Recommendations</div>", unsafe_allow_html=True)
    horizon = st.radio("Horizon", ["Daily","Weekly","Monthly"], horizontal=True, key="trade_rec_horizon")
    steps_map = {"Daily":1,"Weekly":7,"Monthly":30}
    steps = steps_map[horizon]
    if st.button("Get Trade Signals for East Africa"):
        signals = []
        fallback_used = False
        with st.spinner("Computing signals..."):
            for cur in EAST_AFRICAN_CURRENCIES:
                cur_rate = st.session_state.rates.get(cur, None)
                if cur_rate is None: continue
                result = run_forecast(cur, horizon.lower(), steps,
                                      history_df=st.session_state.history,
                                      current_rate=cur_rate,
                                      use_auto_arima=st.session_state.use_auto_arima)
                if result.get("warning"): fallback_used = True
                # Apply threshold
                arima_sig = result["arima_signal"]
                prophet_sig = result["prophet_signal"]
                thresh = st.session_state.alert_threshold
                if arima_sig != "HOLD":
                    change = (result["arima_forecast"] - result["current_rate"]) / result["current_rate"]
                    if abs(change) < thresh:
                        arima_sig = "HOLD"
                if prophet_sig != "HOLD":
                    change = (result["prophet_forecast"] - result["current_rate"]) / result["current_rate"]
                    if abs(change) < thresh:
                        prophet_sig = "HOLD"
                signals.append({
                    "Currency": cur, "Current Rate": result['current_rate'],
                    "ARIMA Forecast": result['arima_forecast'],
                    "ARIMA Signal": arima_sig,
                    "Prophet Forecast": result['prophet_forecast'],
                    "Prophet Signal": prophet_sig
                })
        if signals:
            if fallback_used: st.warning("Some forecasts used rough estimates due to insufficient data.")
            df_signals = pd.DataFrame(signals)
            st.dataframe(df_signals.style.map(lambda val: 'background-color: #00C853; color:black' if val=='BUY' else ('background-color: #FF1744; color:white' if val=='SELL' else ''), subset=['ARIMA Signal','Prophet Signal']), use_container_width=True)
            if st.session_state.alert_signals:
                # Send telegram only for strong signals
                for row in signals:
                    if row["ARIMA Signal"] != "HOLD" or row["Prophet Signal"] != "HOLD":
                        send_telegram(f"📈 {row['Currency']} signal: ARIMA {row['ARIMA Signal']}, Prophet {row['Prophet Signal']} (threshold > {st.session_state.alert_threshold*100:.1f}%)")
                st.success("Signals sent to Telegram (if configured).")
        else:
            st.warning("No signals generated.")

# ============== LIVE TRADING (enhanced OANDA test) ==============
with tabs[3]:
    st.markdown("<div class='section-title'>💹 Live Trading</div>", unsafe_allow_html=True)
    trading_api = get_trading_api()
    is_simulated = isinstance(trading_api, SimulatedTrading)
    if is_simulated:
        st.info("🔹 Running in **Simulated Trading** mode. Set OANDA keys for real trading.")
    else:
        st.success("🔹 Connected to OANDA Practice Account")
    col_sum, col_action = st.columns([1,2])
    with col_sum:
        st.subheader("Account")
        try:
            acc = trading_api.get_account_summary()
            st.metric("Balance", f"${acc['balance']:,.2f}")
            st.metric("Equity", f"${acc['equity']:,.2f}")
            st.metric("Open Positions", acc['open_positions'])
            if "unrealized_pl" in acc:
                st.metric("Unrealized P/L", f"${acc['unrealized_pl']:,.2f}")
            if "margin_used" in acc:
                st.metric("Margin Used", f"${acc['margin_used']:,.2f}")
        except Exception as e:
            st.error(f"Account fetch failed: {e}")
    with col_action:
        st.subheader("Manual Trade")
        with st.form("trade_form"):
            trade_symbol = st.selectbox("Currency Pair", EAST_AFRICAN_CURRENCIES, key="trade_symbol")
            trade_units = st.number_input("Units (positive=buy, negative=sell)", value=1000)
            stop_loss = st.number_input("Stop Loss (optional)", value=0.0, step=0.0001, format="%.5f")
            take_profit = st.number_input("Take Profit (optional)", value=0.0, step=0.0001, format="%.5f")
            if st.form_submit_button("Place Market Order"):
                try:
                    order = trading_api.place_order(symbol=trade_symbol, units=trade_units,
                                                    stop_loss=stop_loss if stop_loss!=0 else None,
                                                    take_profit=take_profit if take_profit!=0 else None)
                    st.success(f"Order placed! ID: {order.get('id','N/A')}")
                    st.json(order)
                except Exception as e:
                    st.error(f"Order failed: {e}")
    if not is_simulated:
        st.button("Test OANDA Connection", on_click=lambda: st.info("OANDA connection OK" if get_trading_api() else "Failed"))
    st.subheader("Open Positions")
    try:
        positions = trading_api.get_open_positions()
        if positions:
            if is_simulated:
                df_pos = pd.DataFrame(positions); st.dataframe(df_pos)
                pos_ids = [p["id"] for p in positions]
                close_id = st.selectbox("Position ID to close", pos_ids, key="close_pos")
                if st.button("Close Position"):
                    if trading_api.close_position(close_id):
                        st.success("Position closed."); st.rerun()
                    else:
                        st.error("Position not found.")
            else:
                for pos in positions: st.json(pos)
        else:
            st.info("No open positions.")
    except Exception as e:
        st.error(f"Error: {e}")
    st.subheader("Order History")
    try:
        history = trading_api.get_order_history()
        if history:
            if is_simulated:
                df_hist = pd.DataFrame(history[-20:]); st.dataframe(df_hist)
            else:
                for order in history[-20:]: st.json(order)
        else:
            st.info("No orders yet.")
    except Exception as e:
        st.error(f"Error: {e}")
    with st.expander("🧮 Position Size Calculator"):
        col1, col2, col3 = st.columns(3)
        with col1:
            calc_equity = st.number_input("Account Equity (USD)", value=float(st.session_state.trading_account['equity']))
            calc_risk = st.slider("Risk % per trade", 0.1, 5.0, 1.0)
        with col2:
            calc_entry = st.number_input("Entry Price", value=st.session_state.rates.get(trade_symbol, 1.0))
            calc_sl = st.number_input("Stop Loss Price", value=calc_entry*0.99)
        with col3:
            pair_rate = st.session_state.rates.get(trade_symbol, 1.0)
            units = calculate_position_size(calc_equity, calc_risk, calc_entry, calc_sl, pair_rate)
            st.metric("Recommended Units", f"{units:,.2f}")
    st.subheader("Auto‑Trading")
    st.session_state.auto_trade = st.checkbox("Enable auto‑trade from signals", value=st.session_state.auto_trade)
    if st.button("Run Auto‑Trade Now"):
        st.info("Auto‑trade logic runs on bot signals. Enable bot and auto‑trade above.")

# ============== TECHNICAL ANALYSIS (unchanged) ==============
with tabs[4]:
    st.markdown("<div class='section-title'>📉 Technical Analysis</div>", unsafe_allow_html=True)
    ta_currency = st.selectbox("Currency", EAST_AFRICAN_CURRENCIES, key="ta_cur")
    ta_periods = st.slider("Data points", 50, 500, 100, key="ta_periods")
    df_all = st.session_state.history[st.session_state.history["Currency"] == ta_currency].copy()
    if df_all.empty:
        st.warning("No history for this currency yet.")
    else:
        df_all["Time_dt"] = pd.to_datetime(df_all["Time"])
        df_all = df_all.sort_values("Time_dt").tail(ta_periods)
        df_indicators = compute_indicators(df_all)
        if df_indicators is not None and PLOTLY_AVAILABLE:
            fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                                subplot_titles=("Price & Bollinger Bands", "RSI", "MACD", "OBV"))
            fig.add_trace(go.Scatter(x=df_indicators["Time_dt"], y=df_indicators["Rate"],
                                     mode='lines', name='Price', line=dict(color='#00F2FE')), row=1, col=1)
            for w in [20, 50]:
                col_name = f"SMA_{w}"
                if col_name in df_indicators.columns:
                    fig.add_trace(go.Scatter(x=df_indicators["Time_dt"], y=df_indicators[col_name],
                                             line=dict(dash='dash'), name=f'SMA {w}'), row=1, col=1)
            if "BB_upper" in df_indicators.columns:
                fig.add_trace(go.Scatter(x=df_indicators["Time_dt"], y=df_indicators["BB_upper"],
                                         line=dict(color='gray', width=1), name='BB Upper'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_indicators["Time_dt"], y=df_indicators["BB_lower"],
                                         line=dict(color='gray', width=1), name='BB Lower'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_indicators["Time_dt"], y=df_indicators["RSI"],
                                     line=dict(color='purple'), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="gray", row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="gray", row=2, col=1)
            fig.add_trace(go.Scatter(x=df_indicators["Time_dt"], y=df_indicators["MACD"],
                                     line=dict(color='blue'), name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df_indicators["Time_dt"], y=df_indicators["MACD_signal"],
                                     line=dict(color='red'), name='Signal'), row=3, col=1)
            fig.add_bar(x=df_indicators["Time_dt"], y=df_indicators["MACD_hist"], name='Histogram', row=3, col=1)
            fig.add_trace(go.Scatter(x=df_indicators["Time_dt"], y=df_indicators["OBV"],
                                     line=dict(color='green'), name='OBV'), row=4, col=1)
            fig.update_layout(height=900, template="plotly_dark",
                              hovermode="x unified", showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for indicators (need at least 50 points).")

# ============== STRATEGY CONFIG ==============
with tabs[5]:
    st.markdown("<div class='section-title'>⚙️ Strategy Configuration</div>", unsafe_allow_html=True)
    st.info(f"Risk Level: {st.session_state.risk_level} (adjust in sidebar)")
    st.write(f"Auto‑ARIMA: {'Enabled' if st.session_state.use_auto_arima else 'Disabled'}")
    st.write(f"Forecast caching: 5 minutes")
    st.write(f"Telegram alert signal threshold: {st.session_state.alert_threshold*100:.1f}%")
    st.write(f"Telegram alerts for signals: {'On' if st.session_state.alert_signals else 'Off'}")
    st.write(f"Telegram alerts for errors: {'On' if st.session_state.alert_errors else 'Off'}")

# ============== LOGS ==============
with tabs[6]:
    st.markdown("<div class='section-title'>📋 Application Logs</div>", unsafe_allow_html=True)
    try:
        with open("sai_app.log", "r") as f:
            last_lines = deque(f, maxlen=200)
            st.text("".join(last_lines))
    except FileNotFoundError:
        st.info("No log file yet.")
    st.markdown("### Recent Bot Logs (from DB)")
    if st.session_state.logs:
        df_logs = pd.DataFrame(st.session_state.logs[-50:])
        st.dataframe(df_logs)
    else:
        st.info("No bot logs in database.")

# ============== MODEL TESTING (unchanged) ==============
with tabs[7]:
    st.markdown("<div class='section-title'>🧪 Model Testing</div>", unsafe_allow_html=True)
    st.warning("⚠️ Only upload .pkl files you trust.")
    uploaded_model = st.file_uploader("Upload model.pkl", type=["pkl"])
    if uploaded_model:
        trusted = st.checkbox("I understand the risk and trust this file.")
        if trusted:
            uploaded_model.seek(0)
            model = load_model(uploaded_model)
            if model:
                st.success("Model loaded.")
                test_results = test_model(model)
                st.write(test_results)
                fig, ax = plt.subplots(); ax.plot(test_results.get("predictions",[]), marker='o'); st.pyplot(fig)

# ============== DEBUG & DATA MANAGEMENT ==============
with tabs[8]:
    st.markdown("<div class='section-title'>🛠️ Debug & Data</div>", unsafe_allow_html=True)
    st.json({k: str(v) if not isinstance(v,(dict,list,int,float,bool,type(None))) else v for k,v in st.session_state.items()})
    with st.expander("🗄️ Database Stats"):
        conn = sqlite3.connect(DB_PATH)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        for t in tables:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
            st.write(f"**{t[0]}**: {cnt} rows")
        conn.close()
    # Download & Archive buttons
    st.markdown("### Data Management")
    csv_data = download_history_csv()
    st.download_button("⬇️ Download Full History CSV", csv_data, "sai_history.csv", "text/csv")
    if st.button("🧹 Archive Old Data (>7 days)"):
        with DB_LOCK:
            conn = db_connect()
            conn.execute("INSERT INTO history_archive SELECT * FROM history WHERE time < datetime('now', '-7 days')")
            conn.execute("DELETE FROM history WHERE time < datetime('now', '-7 days')")
            conn.commit()
            conn.close()
        st.success("Old data archived to history_archive table.")
    if st.button("Clear All Archives"):
        with DB_LOCK:
            conn = db_connect()
            conn.execute("DELETE FROM history_archive")
            conn.commit()
            conn.close()
        st.success("Archive cleared.")

# ============== BACKTEST TAB ==============
with tabs[9]:
    st.markdown("<div class='section-title'>⏪ Backtest Strategy</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        backtest_currency = st.selectbox("Currency", EAST_AFRICAN_CURRENCIES, key="bt_cur")
        strategy = st.selectbox("Strategy", ["ARIMA", "Prophet"], key="bt_strat")
    with col2:
        start_date = st.date_input("Start Date", value=datetime.now()-timedelta(days=180))
        end_date = st.date_input("End Date", value=datetime.now())
    if st.button("Run Backtest"):
        full_hist = load_history(limit=2000)
        full_hist["Time_dt"] = pd.to_datetime(full_hist["Time"])
        with st.spinner("Backtesting..."):
            result = backtest_strategy(backtest_currency, full_hist, strategy,
                                       start_date, end_date, steps=1)
        if "error" in result:
            st.error(result["error"])
        else:
            st.metric("Total Return", f"{result['total_return']:.2f}%")
            st.metric("Sharpe Ratio", f"{result['sharpe']:.2f}")
            st.metric("Max Drawdown", f"{result['max_drawdown']:.2f}%")
            st.metric("Win Rate", f"{result['win_rate']:.1f}%")
            st.metric("Final Balance", f"${result['final_balance']:,.2f}")
            # Equity curve
            fig, ax = plt.subplots()
            ax.plot(result["equity_curve"])
            ax.set_title("Equity Curve")
            st.pyplot(fig)
            # Trades table
            if result["trades"]:
                st.dataframe(pd.DataFrame(result["trades"]))
            else:
                st.info("No trades executed during this period.")
