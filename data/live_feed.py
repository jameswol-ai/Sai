import streamlit as st
import time, threading, requests, random
from datetime import datetime
from config import logger, ALL_CURRENCIES, EAST_AFRICAN_CURRENCIES, HISTORY_MAX_ROWS

from data.database import insert_history

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
        import pandas as pd
        new_df = pd.DataFrame(rows)
        if not hasattr(st.session_state, "history") or st.session_state.history is None:
            st.session_state.history = new_df
        else:
            st.session_state.history = pd.concat([st.session_state.history, new_df], ignore_index=True)
            if len(st.session_state.history) > HISTORY_MAX_ROWS:
                st.session_state.history = st.session_state.history.iloc[-HISTORY_MAX_ROWS:].reset_index(drop=True)
