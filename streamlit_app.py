import streamlit as st
import threading
import logging
from plugins import risk_plugins, notifier_plugins, strategy_plugins

# Configure logging
logging.basicConfig(filename="trading.log", level=logging.INFO)

def render_dashboard():
    st.title("SAI Trading Dashboard")
    if st.button("Start Trading"):
        if "trading_thread" not in st.session_state or not st.session_state.trading_thread.is_alive():
            st.session_state.trading_thread = threading.Thread(target=run_trading_loop, daemon=True)
            st.session_state.trading_thread.start()
            st.success("Trading loop started.")
        else:
            st.warning("Trading loop already running.")

def render_strategy_config():
    st.title("Strategy Configuration")
    st.write("Configure your trading strategies here.")

def render_logs():
    st.title("Logs")
    with open("trading.log", "r") as f:
        logs = f.read()
    st.text_area("Log Output", logs, height=400)

def render_model_testing():
    st.title("Model Testing")
    st.write("Run backtests and model evaluations here.")

def render_debug():
    st.title("Debug Tools")
    st.write("Diagnostics and debugging utilities.")

def render_plugins_tab():
    st.title("Plugin Control Center")

    # Risk Management Plugins
    st.header("Risk Management")
    for plugin in risk_plugins:
        enabled = st.checkbox(f"Enable {plugin.name}", value=plugin.enabled, key=f"{plugin.name}_enabled")
        param = st.slider(
            f"{plugin.name} threshold",
            plugin.min_val,
            plugin.max_val,
            plugin.default,
            key=f"{plugin.name}_param"
        )
        plugin.update(enabled=enabled, param=param)

    # Strategy Switcher
    st.header("Strategy")
    strategy_choice = st.selectbox("Select Strategy", [s.name for s in strategy_plugins], key="strategy_choice")
    strategy_plugins[strategy_choice].activate()

    # Notifier Controls
    st.header("Notifications")
    for notifier in notifier_plugins:
        active = st.checkbox(f"Enable {notifier.name}", value=notifier.active, key=f"{notifier.name}_active")
        if st.button(f"Test {notifier.name}", key=f"{notifier.name}_test"):
            notifier.test_ping()
        notifier.update(active=active)

    # Audit Log
    st.header("Audit Log")
    st.write("Recent plugin actions and parameter changes will appear here.")

def main():
    st.sidebar.title("SAI Cockpit")
    tab = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Strategy Config", "Logs", "Model Testing", "Debug", "Plugins"]
    )

    if tab == "Dashboard":
        render_dashboard()
    elif tab == "Strategy Config":
        render_strategy_config()
    elif tab == "Logs":
        render_logs()
    elif tab == "Model Testing":
        render_model_testing()
    elif tab == "Debug":
        render_debug()
    elif tab == "Plugins":
        render_plugins_tab()

if __name__ == "__main__":
    main()
