import threading
import time
from datetime import datetime
import streamlit as st
from sai.streamlit_app import get_real_rates, sample_currency_rates, logger  # adjust import path

def _live_rate_fetcher(stop_event: threading.Event):
    """Fetches rates every 2s and updates st.session_state safely."""
    while not stop_event.is_set():
        try:
            real = get_real_rates()
            rates = real if real else sample_currency_rates()
            with st.session_state.live_rates_lock:
                # Keep previous for delta calculation
                if "rates" in st.session_state.live_rates_data:
                    st.session_state.live_rates_data["prev_rates"] = st.session_state.live_rates_data["rates"].copy()
                st.session_state.live_rates_data["rates"] = rates
                st.session_state.live_rates_data["timestamp"] = datetime.now()
        except Exception as e:
            logger.error(f"Live fetcher error: {e}")
        time.sleep(2)

def start_live_stream():
    """Start the background thread if not already running."""
    if "live_stream_thread" not in st.session_state:
        st.session_state.live_stream_thread = None
    if st.session_state.live_stream_thread is not None and st.session_state.live_stream_thread.is_alive():
        return
    stop_event = threading.Event()
    thread = threading.Thread(target=_live_rate_fetcher, args=(stop_event,), daemon=True)
    st.session_state.live_stream_thread = thread
    st.session_state.live_stream_stop_event = stop_event
    thread.start()

def stop_live_stream():
    if "live_stream_stop_event" in st.session_state:
        st.session_state.live_stream_stop_event.set()
        if st.session_state.live_stream_thread:
            st.session_state.live_stream_thread.join(timeout=1)
        st.session_state.live_stream_thread = None

def get_live_rates():
    """Thread-safe retrieval of latest rates."""
    with st.session_state.live_rates_lock:
        data = st.session_state.live_rates_data.copy()
    return data.get("rates", {}), data.get("prev_rates", {})
