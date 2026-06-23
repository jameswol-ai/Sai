# streamlit_app.py
import streamlit as st
import threading
import time
import pandas as pd
import logging
from sai.trading import LiveTrader
from sai.backtest import run_backtest
from sai.plugins.risk import MaxDrawdownRisk, VolatilityRisk
from prometheus_client import Gauge, start_http_server

# --- Prometheus metrics ---
live_return = Gauge("sai_live_return", "Live trading total return")
live_drawdown = Gauge("sai_live_drawdown", "Live trading max drawdown")
backtest_return = Gauge("sai_backtest_return", "Backtest total return")
backtest_drawdown = Gauge("sai_backtest_drawdown", "Backtest max drawdown")
qa_tests_passed = Gauge("sai_tests_passed", "Number of QA tests passed")
qa_tests_failed = Gauge("sai_tests_failed", "Number of QA tests failed")

# --- Logging setup ---
logging.basicConfig(filename="sai.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

# --- Live trading loop ---
def trading_loop(trader: LiveTrader):
    while st.session_state.get("trading_active", False):
        trade = trader.execute_trade()
        logging.info(f"Executed trade: {trade}")
        # Update Prometheus metrics
        live_return.set(trader.total_return)
        live_drawdown.set(trader.max_drawdown)
        time.sleep(1)

# --- Tabs ---
def dashboard_tab():
    st.header("Dashboard")
    if st.button("Start Trading"):
        st.session_state.trading_active = True
        trader = LiveTrader()
        threading.Thread(target=trading_loop, args=(trader,), daemon=True).start()
        st.success("Trading loop started.")
    if st.button("Stop Trading"):
        st.session_state.trading_active = False
        st.warning("Trading loop stopped.")

def strategy_config_tab():
    st.header("Strategy Config")
    st.text_input("Parameter A", key="param_a")
    st.text_input("Parameter B", key="param_b")
    st.write("Parameters saved to session state.")

def logs_tab():
    st.header("Logs")
    with open("sai.log") as f:
        st.text(f.read())

def model_testing_tab():
    st.header("Model Testing")
    st.write("Placeholder for ML model testing.")

def debug_tab():
    st.header("Debug")
    st.json(st.session_state)

def backtest_tab():
    st.header("Backtest Engine")
    strategy = st.selectbox("Select Strategy", ["Mean Reversion", "Momentum", "Custom"])
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")

    if st.button("Run Backtest"):
        results = run_backtest(strategy, start_date, end_date)
        st.success("Backtest completed!")

        # Risk plugin evaluation
        md_risk = MaxDrawdownRisk(threshold=0.1)
        vol_risk = VolatilityRisk(threshold=0.05)
        st.write("Risk Checks:")
        st.write("Max Drawdown Triggered:", md_risk.evaluate(results["trades"]))
        st.write("Volatility Triggered:", vol_risk.evaluate(results["prices"]))

        # Metrics
        st.metric("Total Return", f"{results['total_return']:.2%}")
        st.metric("Max Drawdown", f"{results['max_drawdown']:.2%}")
        st.metric("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")

        # Prometheus exporters
        backtest_return.set(results["total_return"])
        backtest_drawdown.set(results["max_drawdown"])

        # Equity curve
        st.line_chart(pd.DataFrame(results["equity_curve"], columns=["Equity"]))

# --- Main ---
def main():
    st.title("SAI Trading Cockpit")
    tabs = st.tabs(["Dashboard", "Strategy Config", "Logs", "Model Testing", "Debug", "Backtest"])
    with tabs[0]: dashboard_tab()
    with tabs[1]: strategy_config_tab()
    with tabs[2]: logs_tab()
    with tabs[3]: model_testing_tab()
    with tabs[4]: debug_tab()
    with tabs[5]: backtest_tab()

if __name__ == "__main__":
    start_http_server(8000)  # Prometheus metrics endpoint
    if "trading_active" not in st.session_state:
        st.session_state.trading_active = False
    main()
