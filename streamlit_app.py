# sai/streamlit_app.py
import streamlit as st
import threading
import time
import logging
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    filename="sai_app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize session state
if "bot_thread" not in st.session_state:
    st.session_state.bot_thread = None
if "bot_running" not in st.session_state:
    st.session_state.bot_running = False
if "logs" not in st.session_state:
    st.session_state.logs = []

# Helper: threaded bot runner
def start_bot():
    def bot_loop():
        logging.info("Bot started.")
        while st.session_state.bot_running:
            try:
                trade_info = run_bot()
                st.session_state.logs.append(trade_info)
                time.sleep(2)
            except Exception as e:
                logging.error(f"Bot error: {e}")
                st.session_state.logs.append(f"Error: {e}")
                break
        logging.info("Bot stopped.")

    st.session_state.bot_running = True
    st.session_state.bot_thread = threading.Thread(target=bot_loop, daemon=True)
    st.session_state.bot_thread.start()

def stop_bot():
    st.session_state.bot_running = False
    logging.info("Bot stop requested.")

# --- Streamlit UI ---
st.set_page_config(page_title="SAI Trading Bot", layout="wide")
st.title("📈 SAI Trading Bot Dashboard")

tabs = st.tabs(["Dashboard", "Strategy Config", "Logs", "Model Testing", "Debug"])

# Dashboard Tab
with tabs[0]:
    st.header("Live Trading Dashboard")
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Start Bot", disabled=st.session_state.bot_running):
            start_bot()
        if st.button("Stop Bot", disabled=not st.session_state.bot_running):
            stop_bot()

    with col2:
        st.write("Market Snapshot")
        try:
            data = get_data()
            st.json(data)
        except Exception as e:
            st.error(f"Data fetch error: {e}")

    st.write("Trade Logs (latest 10)")
    st.table(st.session_state.logs[-10:])

# Strategy Config Tab
with tabs[1]:
    st.header("Strategy Configuration")
    risk_level = st.slider("Risk Level", 1, 10, 5)
    st.write(f"Selected Risk Level: {risk_level}")
    # Extend with more strategy parameters as needed

# Logs Tab
with tabs[2]:
    st.header("Application Logs")
    try:
        with open("sai_app.log", "r") as f:
            log_lines = f.readlines()[-50:]
        st.text("".join(log_lines))
    except FileNotFoundError:
        st.info("No logs yet.")

# Model Testing Tab
with tabs[3]:
    st.header("Model Testing")
    uploaded_model = st.file_uploader("Upload model.pkl", type=["pkl"])
    if uploaded_model:
        model = load_model(uploaded_model)
        st.success("Model loaded successfully.")
        test_results = test_model(model)
        st.write("Test Results:", test_results)

        # Example visualization
        fig, ax = plt.subplots()
        ax.plot(test_results.get("predictions", []), label="Predictions")
        ax.legend()
        st.pyplot(fig)

# Debug Tab
with tabs[4]:
    st.header("Debug Information")
    st.write("Session State:", st.session_state)
