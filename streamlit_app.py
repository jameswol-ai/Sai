import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px

# Example synthetic trade data
np.random.seed(42)
trades = pd.DataFrame({
    "timestamp": pd.date_range("2026-01-01", periods=100, freq="H"),
    "pnl": np.random.normal(0, 50, 100),
    "trade_size": np.random.randint(1, 10, 100),
    "volatility": np.random.uniform(0.1, 2.0, 100),
    "model_accuracy": np.random.uniform(0.5, 1.0, 100)
})

st.title("📊 Advanced Visualizations Cockpit")

# Tabs for modular visualization
tab1, tab2, tab3, tab4 = st.tabs([
    "Heatmap", "Correlation", "Timeline", "PnL Trends"
])

with tab1:
    st.subheader("Trade Outcome Heatmap")
    trades["hour"] = trades["timestamp"].dt.hour
    trades["day"] = trades["timestamp"].dt.day
    heatmap_data = trades.pivot_table(values="pnl", index="day", columns="hour", aggfunc="mean")

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(heatmap_data, cmap="RdYlGn", center=0, ax=ax)
    st.pyplot(fig)

with tab2:
    st.subheader("Correlation Matrix")
    corr = trades[["pnl", "trade_size", "volatility", "model_accuracy"]].corr()
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax)
    st.pyplot(fig)

with tab3:
    st.subheader("Unified Timeline Overlay")
    fig = px.line(
        trades,
        x="timestamp",
        y=["pnl", "volatility", "model_accuracy"],
        labels={"value": "Metric Value", "timestamp": "Time"},
        title="Trades, Volatility & Model Accuracy Over Time"
    )
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("PnL & Trade Size Trends")
    fig = px.line(
        trades,
        x="timestamp",
        y=["pnl", "trade_size"],
        labels={"value": "Metric Value", "timestamp": "Time"},
        title="PnL & Trade Size Over Time"
    )
    st.plotly_chart(fig, use_container_width=True)
