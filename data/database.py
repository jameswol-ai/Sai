import sqlite3, threading
import pandas as pd
from typing import Dict, List
from config import DB_PATH, logger

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

# --- History ---
def insert_history(rows: List[Dict]):
    with DB_LOCK:
        conn = db_connect()
        conn.executemany(
            "INSERT INTO history (time, currency, rate, forecast) VALUES (?, ?, ?, ?)",
            [(r["Time"], r["Currency"], r["Rate"], r["Forecast"]) for r in rows]
        )
        conn.commit()
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

# --- Bot logs ---
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

# --- Account, Positions, Orders ---
def save_account(balance, equity):
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

def save_positions(positions):
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

def save_orders(orders):
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
