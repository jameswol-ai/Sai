# sai/db.py
import sqlite3
import threading
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = "sai_trading.db"
LOCK = threading.Lock()

def get_connection() -> sqlite3.Connection:
    """Thread‑safe connection with WAL mode for concurrency."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS history (
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

# ---------- History ----------
def insert_history(rows: List[Dict]):
    with LOCK:
        conn = get_connection()
        conn.executemany(
            "INSERT INTO history (time, currency, rate, forecast) VALUES (?, ?, ?, ?)",
            [(r["Time"], r["Currency"], r["Rate"], r["Forecast"]) for r in rows]
        )
        conn.commit()
        conn.close()
    # Trim old records (keep last 1000)
    cleanup_history()

def get_history(limit: int = 1000) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT time, currency, rate, forecast FROM history ORDER BY time DESC LIMIT ?",
        conn, params=(limit,)
    )
    conn.close()
    df = df.iloc[::-1]  # oldest first for plotting
    df.rename(columns={"time": "Time", "currency": "Currency", "rate": "Rate", "forecast": "Forecast"}, inplace=True)
    return df

def cleanup_history(keep=1000):
    with LOCK:
        conn = get_connection()
        conn.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)", (keep,))
        conn.commit()
        conn.close()

# ---------- Bot Logs ----------
def insert_bot_log(logs: List[Dict]):
    with LOCK:
        conn = get_connection()
        conn.executemany(
            "INSERT INTO bot_logs (time, trade, symbol, amount, error) VALUES (?, ?, ?, ?, ?)",
            [(l.get("time"), l.get("trade"), l.get("symbol"), l.get("amount"), l.get("error")) for l in logs]
        )
        conn.commit()
        conn.close()
    cleanup_bot_logs()

def get_bot_logs(limit=200) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM bot_logs ORDER BY id DESC LIMIT ?", conn, params=(limit,))
    conn.close()
    return df.iloc[::-1]

def cleanup_bot_logs(keep=1000):
    with LOCK:
        conn = get_connection()
        conn.execute("DELETE FROM bot_logs WHERE id NOT IN (SELECT id FROM bot_logs ORDER BY id DESC LIMIT ?)", (keep,))
        conn.commit()
        conn.close()

# ---------- Account ----------
def save_account(balance: float, equity: float):
    with LOCK:
        conn = get_connection()
        conn.execute("REPLACE INTO account (key, value) VALUES ('balance', ?), ('equity', ?)", (balance, equity))
        conn.commit()
        conn.close()

def load_account() -> Dict[str, float]:
    conn = get_connection()
    cur = conn.execute("SELECT key, value FROM account WHERE key IN ('balance', 'equity')")
    data = {"balance": 10000.0, "equity": 10000.0}
    for row in cur:
        data[row[0]] = float(row[1])
    conn.close()
    return data

# ---------- Positions & Orders ----------
def save_positions(positions: List[Dict]):
    with LOCK:
        conn = get_connection()
        conn.execute("DELETE FROM positions")
        conn.executemany(
            "INSERT INTO positions (id, time, symbol, units, type, price, stop_loss, take_profit, status, pnl) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(p["id"], p["time"], p["symbol"], p["units"], p["type"], p["price"], p.get("stop_loss"), p.get("take_profit"), p["status"], p.get("pnl")) for p in positions]
        )
        conn.commit()
        conn.close()

def load_positions() -> List[Dict]:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM positions", conn)
    conn.close()
    return df.to_dict(orient="records")

def save_orders(orders: List[Dict]):
    with LOCK:
        conn = get_connection()
        conn.execute("DELETE FROM orders")
        conn.executemany(
            "INSERT INTO orders (id, time, symbol, units, type, price, stop_loss, take_profit, status) VALUES (?,?,?,?,?,?,?,?,?)",
            [(o["id"], o["time"], o["symbol"], o["units"], o["type"], o["price"], o.get("stop_loss"), o.get("take_profit"), o["status"]) for o in orders]
        )
        conn.commit()
        conn.close()

def load_orders() -> List[Dict]:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    return df.to_dict(orient="records")
