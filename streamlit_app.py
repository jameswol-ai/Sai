# streamlit_app.py (final patched version)
import streamlit as st
import threading
import time
import pandas as pd
import logging
import random
from prometheus_client import Gauge, CollectorRegistry, make_wsgi_app
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler
import threading

# --- Safe Prometheus metrics server ---
class ReusableWSGIServer(WSGIServer):
    allow_reuse_address = True

def start_metrics_server(port=8000, registry=None):
    if "metrics_server_started" not in st.session_state:
        app = make_wsgi_app(registry=registry)
        httpd = ReusableWSGIServer(("", port), WSGIRequestHandler)
        httpd.set_app(app)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        st.session_state["metrics_server_started"] = True

# --- Prometheus registry ---
if "prom_registry" not in st.session_state:
    st.session_state.prom_registry = CollectorRegistry()
    st.session_state.live_return = Gauge("sai_live_return", "Live trading total return", registry=st.session_state.prom_registry)
    st.session_state.live_drawdown = Gauge("sai_live_drawdown", "Live trading max drawdown", registry=st.session_state.prom_registry)
    st.session_state.backtest_return = Gauge("sai_backtest_return", "Backtest total return", registry=st.session_state.prom_registry)
    st.session_state.backtest_drawdown = Gauge("sai_backtest_drawdown", "Backtest max drawdown", registry=st.session_state.prom_registry)

# Aliases
live_return = st.session_state.live_return
live_drawdown = st.session_state.live_drawdown
backtest_return = st.session_state.backtest_return
backtest_drawdown = st.session_state.backtest_drawdown

# --- Logging setup ---
logging.basicConfig(filename="sai.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

# --- Dummy trading class ---
class LiveTrader:
    def __init__(self):
        self.total_return = 0.0
        self.max_drawdown = 0.0
        self.equity = 100.0

    def execute_trade(self):
        change = random.uniform(-1, 1)
        self.equity += change
        self.total_return = (self.equity - 100.0) / 100.0
        self.max_drawdown = min(self.max_drawdown, self.total_return)
        return {"price": self.equity, "pnl": change}

# --- Dummy backtest function ---
def run_backtest(strategy, start_date, end_date):
    equity_curve = [100]
    trades = []
    for _ in range(50):
        change = random.uniform(-2, 2)
        equity_curve.append(equity_curve[-1] + change)
        trades.append({"price": equity_curve[-1], "pnl": change})
    total_return = (equity_curve[-1] - 100) / 100
    max_drawdown = min((eq - 100) / 100 for eq in equity_curve)
    sharpe_ratio = total_return / (pd.Series(equity_curve).std() or 1)
    return {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "equity_curve": equity_curve,
        "trades": trades,
        "prices": [t["price"] for t in trades],
    }

# --- Risk plugins ---
class MaxDrawdownRisk:
    def __init__(self, threshold=0.1):
        self.threshold = threshold
    def evaluate(self, trades):
        min_pnl = min(t["pnl"] for t in trades)
        return min_pnl < -self.threshold

class VolatilityRisk:
    def __init__(self, threshold=0.05):
        self.threshold = threshold
    def evaluate(self, prices):
        return pd.Series(prices).pct_change().std() > self.threshold

# --- Live trading loop ---
def trading_loop(trader: LiveTrader):
    while st.session_state.get("trading_active", False):
        trade = trader.execute_trade()
        logging.info(f"Executed trade: {trade}")
        live_return.set(trader.total_return)
        live_drawdown.set(trader.max_drawdown)
        time.sleep(1)

# --- Tabs ---
def dashboard_tab():
    st.header("Dashboard")
    if st.button("Start Trading"):
        if not st.session_state.get("trading_active", False):
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

def logs_tab():
    st.header("Logs")
    try:
        with open("sai.log") as f:
            st.text(f.read())
    except FileNotFoundError:
        st.info("No logs yet.")

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

        md_risk = MaxDrawdownRisk(threshold=0.1)
        vol_risk = VolatilityRisk(threshold=0.05)
        drawdown_triggered = md_risk.evaluate(results["trades"])
        volatility_triggered = vol_risk.evaluate(results["prices"])

        st.subheader("Risk Checks")
        if drawdown_triggered:
            st.error("⚠️ Max Drawdown Risk Triggered!")
        else:
            st.success("✅ Max Drawdown within safe limits.")

        if volatility_triggered:
            st.error("⚠️ Volatility Risk Triggered!")
        else:
            st.success("✅ Volatility within safe limits.")

        st.metric("Total Return", f"{results['total_return']:.2%}")
        st.metric("Max Drawdown", f"{results['max_drawdown']:.2%}")
        st.metric("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")

        backtest_return.set(results["total_return"])
        backtest_drawdown.set(results["max_drawdown"])

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
    start_metrics_server(port=8000, registry=st.session_state.prom_registry)
    if "trading_active" not in st.session_state:
        st.session_state.trading_active = False
    main()
