# --- Weekly Forecast Tab ---
from plugins.arima_forecast import fit_arima, forecast_next
from plugins.prophet_forecast import fit_prophet, forecast_future
from utils.metrics import compute_metrics

with tabs[5]:
    st.header("Weekly Currency Forecasts")

    if not st.session_state.history.empty:
        currency = st.selectbox("Select Currency", st.session_state.history["Currency"].unique())
        df_cur = st.session_state.history[st.session_state.history["Currency"] == currency]

        if len(df_cur) > 20:
            steps = 7

            # ARIMA forecast
            try:
                arima_fit = fit_arima(df_cur["Rate"], order=(2,1,2))
                arima_pred = forecast_next(arima_fit, steps=steps)
                st.line_chart(pd.Series(arima_pred, name=f"{currency} ARIMA 7‑Day Forecast"))
            except Exception as e:
                st.error(f"ARIMA error: {e}")

            # Prophet forecast
            try:
                df_prophet = pd.DataFrame({"ds": pd.to_datetime(df_cur["Time"]), "y": df_cur["Rate"].astype(float)})
                prophet_model = fit_prophet(df_prophet)
                forecast_df = forecast_future(prophet_model, periods=steps, freq="D")
                st.line_chart(forecast_df.set_index("ds")[["yhat"]].tail(steps))
            except Exception as e:
                st.error(f"Prophet error: {e}")

            # Metrics
            if 'arima_pred' in locals() and 'forecast_df' in locals():
                actual_vals = df_cur["Rate"].values[-steps:]
                arima_metrics = compute_metrics(actual_vals, arima_pred[:len(actual_vals)])
                prophet_metrics = compute_metrics(actual_vals, forecast_df.tail(steps)["yhat"].tolist()[:len(actual_vals)])
                st.subheader("7‑Day Forecast Accuracy")
                st.table(pd.DataFrame([arima_metrics, prophet_metrics], index=["ARIMA","Prophet"]))

# --- Multi-Currency Weekly Forecast Tab ---
with tabs[6]:
    st.header("Multi-Currency 7-Day Forecasts")

    if not st.session_state.history.empty:
        currencies = st.multiselect(
            "Select currencies to forecast",
            st.session_state.history["Currency"].unique(),
            default=["USD","EUR","UGX"]
        )

        steps = 7
        results = {}

        for cur in currencies:
            df_cur = st.session_state.history[st.session_state.history["Currency"] == cur]
            if len(df_cur) > 20:
                try:
                    arima_fit = fit_arima(df_cur["Rate"], order=(2,1,2))
                    arima_pred = forecast_next(arima_fit, steps=steps)

                    df_prophet = pd.DataFrame({"ds": pd.to_datetime(df_cur["Time"]), "y": df_cur["Rate"].astype(float)})
                    prophet_model = fit_prophet(df_prophet)
                    forecast_df = forecast_future(prophet_model, periods=steps, freq="D")
                    prophet_pred = forecast_df.tail(steps)["yhat"].tolist()

                    results[cur] = {"ARIMA": arima_pred, "Prophet": prophet_pred}
                except Exception as e:
                    st.error(f"{cur} forecast error: {e}")

        # Plot all currencies together
        fig, ax = plt.subplots(figsize=(12,6))
        for cur, preds in results.items():
            ax.plot(range(steps), preds["ARIMA"], marker="o", label=f"{cur} ARIMA")
            ax.plot(range(steps), preds["Prophet"], marker="x", linestyle="--", label=f"{cur} Prophet")
        ax.set_title("7-Day Multi-Currency Forecasts")
        ax.set_xlabel("Days Ahead")
        ax.set_ylabel("Rate")
        ax.legend()
        st.pyplot(fig)

        # Metrics table
        metrics_rows = []
        for cur, preds in results.items():
            actual_vals = st.session_state.history[st.session_state.history["Currency"]==cur]["Rate"].values[-steps:]
            if len(actual_vals) >= steps:
                arima_metrics = compute_metrics(actual_vals, preds["ARIMA"][:steps])
                prophet_metrics = compute_metrics(actual_vals, preds["Prophet"][:steps])
                metrics_rows.append({"Currency":cur,"Model":"ARIMA",**arima_metrics})
                metrics_rows.append({"Currency":cur,"Model":"Prophet",**prophet_metrics})
        if metrics_rows:
            st.subheader("7-Day Forecast Accuracy (RMSE, MAPE)")
            st.table(pd.DataFrame(metrics_rows))
