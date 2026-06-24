import streamlit as st
import threading
import logging
import time
from collections import deque

# Import plugin registries
from plugins import risk_plugins, notifier_plugins, strategy_plugins

# Configure logging
logging.basicConfig(filename="trading_logs.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# --- Trading Loop ---
def run_trading_loop():
    while st.session_state.get("trading_active", True):
        logging.info("Trade executed")
        time.sleep(2)  # prevent busy loop

def start_trading_loop():
    if "trading_thread" not in st.session_state or not st.session_state.trading_thread.is_alive():
        st.session_state.trading_active = True
        st.session_state.trading_thread = threading.Thread(target=run_trading_loop, daemon=True)
        st.session_state.trading_thread.start()
        st.success("Trading loop started.")

def stop_trading_loop():
    st.session_state.trading_active = False
    st.success("Trading loop stopped.")
    logging.info("Trading loop stopped.")

# --- Tabs ---
def render_dashboard():
    st.title("Dashboard")
    if st.button("Start Trading"):
        start_trading_loop()
    if st.button("Stop Trading"):
        stop_trading_loop()
    st.write("Charts, metrics, and live trading status here.")

def render_strategy_config():
    st.title("Strategy Config")
    st.write("Configure strategy parameters here.")

def render_logs():
    st.title("Logs")
    try:
        with open("trading_logs.log") as f:
            # Stream last 50 lines for responsiveness
            lines = deque(f, maxlen=50)
            st.text("".join(lines))
    except FileNotFoundError:
        st.warning("No logs found yet. Start trading to generate logs.")

def render_model_testing():
    st.title("Model Testing")
    st.write("Backtest and model evaluation here.")

def render_plugins_tab():
    st.title("Plugin Control Center")

    # Risk Management Plugins
    st.header("Risk Management")
    for plugin in risk_plugins:
        enabled = st.checkbox(f"Enable {plugin.name}", value=getattr(plugin, "enabled", False), key=f"{plugin.name}_enabled")
        param = st.slider(
            f"{plugin.name} threshold",
            getattr(plugin, "min_val", 0),
            getattr(plugin, "max_val", 100),
            getattr(plugin, "default", 50),
            key=f"{plugin.name}_param"
        )
        try:
            plugin.update(enabled=enabled, param=param)
            logging.info(f"Risk plugin {plugin.name} updated: enabled={enabled}, param={param}")
            st.success(f"{plugin.name} updated successfully.")
        except Exception as e:
            st.error(f"Error updating {plugin.name}: {e}")

    # Strategy Switcher
    st.header("Strategy")
    strategy_choice = st.selectbox("Select Strategy", list(strategy_plugins.keys()), key="strategy_choice")
    try:
        strategy_plugins[strategy_choice].activate()
        logging.info(f"Strategy switched to {strategy_choice}")
        st.success(f"Strategy switched to {strategy_choice}")
    except Exception as e:
        st.error(f"Error switching strategy: {e}")

    # Notifier Controls
    st.header("Notifications")
    for notifier in notifier_plugins:
        active = st.checkbox(f"Enable {notifier.name}", value=getattr(notifier, "active", False), key=f"{notifier.name}_active")
        if st.button(f"Test {notifier.name}", key=f"{notifier.name}_test"):
            try:
                notifier.test_ping()
                logging.info(f"Notifier {notifier.name} test ping sent")
                st.success(f"{notifier.name} test ping sent")
            except Exception as e:
                st.error(f"Error testing {notifier.name}: {e}")
        try:
            notifier.update(active=active)
            logging.info(f"Notifier {notifier.name} updated: active={active}")
        except Exception as e:
            st.error(f"Error updating notifier {notifier.name}: {e}")

    # Audit Log
    st.header("Audit Log")
    try:
        with open("trading_logs.log") as f:
            lines = deque(f, maxlen=50)
            st.text("".join(lines))
    except FileNotFoundError:
        st.warning("No audit log yet. Actions will appear here once plugins are used.")

# --- Main ---
def main():
    st.sidebar.title("SAI Cockpit")
    tab = st.sidebar.radio("Navigate", ["Dashboard", "Strategy Config", "Logs", "Model Testing", "Plugins"])

    if tab == "Dashboard":
        render_dashboard()
    elif tab == "Strategy Config":
        render_strategy_config()
    elif tab == "Logs":
        render_logs()
    elif tab == "Model Testing":
        render_model_testing()
    elif tab == "Plugins":
        render_plugins_tab()

if __name__ == "__main__":
    # Initialize session state defaults
    if "trading_active" not in st.session_state:
        st.session_state.trading_active = False
    main()
