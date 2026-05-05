import streamlit as st
import time
import random

# --- Session State Defaults ---
def init_defaults():
    if "balance" not in st.session_state:
        st.session_state.balance = 1000.0
    if "pnl" not in st.session_state:
        st.session_state.pnl = 0.0
    if "last_price" not in st.session_state:
        st.session_state.last_price = None
    if "last_action" not in st.session_state:
        st.session_state.last_action = None
    if "running" not in st.session_state:
        st.session_state.running = False

# --- Dashboard Tab ---
def dashboard_tab():
    st.subheader("Live Trading Controls")
    refresh = st.number_input("Refresh interval (s)", min_value=0.5, value=1.0, step=0.5)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start Trading"):
            st.session_state.running = True
    with col2:
        if st.button("⏹ Stop Trading"):
            st.session_state.running = False

    st.subheader("Live Metrics")
    st.metric("Last Price", st.session_state.last_price if st.session_state.last_price else "—")
    st.metric("Last Action", st.session_state.last_action if st.session_state.last_action else "—")
    st.metric("Balance", f"{st.session_state.balance:.2f}")
    st.metric("PnL", f"{st.session_state.pnl:.2f}")

    # Simulated price chart
    chart = st.empty()
    prices = []
    if st.session_state.running:
        for _ in range(10):
            price = round(random.uniform(90, 110), 2)
            st.session_state.last_price = price
            st.session_state.last_action = random.choice(["BUY", "SELL", "HOLD"])
            st.session_state.pnl += random.uniform(-1, 1)
            prices.append(price)
            chart.line_chart(prices)
            time.sleep(refresh)

# --- Strategy Tab ---
def strategy_tab():
    st.subheader("Strategy Configuration")
    st.text_input("Strategy Name", "Default Strategy")
    st.slider("Risk Level", 1, 10, 5)
    st.checkbox("Enable Stop Loss", True)

# --- Logs Tab ---
def logs_tab():
    st.subheader("Logs")
    st.text_area("Execution Logs", "No logs yet...", height=200)

# --- Debug Tab ---
def debug_tab():
    st.subheader("Debug Info")
    st.write("Session State:", dict(st.session_state))

# Add a new tab for comparison
tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Logs", "Debug", "Comparison"])

with tab4:
    st.header("📈 Strategy Comparison")

    # Run both strategies in parallel for the same price
    price = engine.broker.get_price()
    ml_plugin = StrategyPlugin("sai.strategies.ml_strategy")
    ma_plugin = StrategyPlugin("sai.strategies.ma_crossover")

    ml_signal = ml_plugin.generate_signal(price)
    ma_signal = ma_plugin.generate_signal(price)

    st.write(f"Market Price: {price:.2f}")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("ML Strategy")
        st.write("Signal:", ml_signal)
        st.write("Metrics:", engine.metrics.update(engine.broker.balance))

    with col2:
        st.subheader("MA Crossover")
        st.write("Signal:", ma_signal)
        st.write("Metrics:", engine.metrics.update(engine.broker.balance))

    # Show equity curve comparison
    st.text("Equity Curve (ASCII):")
    st.text(engine.chart.update(engine.broker.balance))

# --- Main App ---
def main():
    init_defaults()
    st.title("SAI Trading Dashboard")

    tabs = st.tabs([
        "📊 Dashboard",
        "🧠 Strategy",
        "📜 Logs",
        "🛠 Debug"
        "🇸🇸 Comparison"
    ])

    with tabs[0]:
        dashboard_tab()
    with tabs[1]:
        strategy_tab()
    with tabs[2]:
        logs_tab()
    with tabs[3]:
        debug_tab()

if __name__ == "__main__":
    main()
