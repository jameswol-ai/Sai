# Cache the forecast for a short period to avoid repeated heavy fitting
@st.cache_data(ttl=300, show_spinner=False)
def run_forecast(currency: str, horizon: str, steps: int, freq: str = "D") -> Dict[str, Any]:
    """Generate forecasts for a single currency. Cached for 5 minutes."""
    df_all = st.session_state.history.copy()
    df_all["Time_dt"] = pd.to_datetime(df_all["Time"])
    df_cur = df_all[df_all["Currency"] == currency].sort_values("Time_dt")

    # -------------------------------------------------------------------
    # Fallback for insufficient data
    # -------------------------------------------------------------------
    if len(df_cur) < 20:
        current_rate = st.session_state.rates.get(currency, 1.0)
        rng = np.random.default_rng(42)
        fallback_preds = [round(current_rate * (1 + rng.uniform(-0.01, 0.01)), 2)
                          for _ in range(steps)]
        return {
            "currency": currency,
            "current_rate": current_rate,
            "arima_forecast": fallback_preds[0],
            "prophet_forecast": None,
            "arima_signal": "HOLD",
            "prophet_signal": None,
            "arima_all_preds": fallback_preds,
            "prophet_all_preds": None,
            "arima_metrics": None,
            "prophet_metrics": None,
            "actual_test": [],
            "train": df_cur,
            "test": pd.DataFrame(),
            "warning": "Insufficient history – forecast is a rough estimate only.",
            "arima_fitted": False
        }

    # -------------------------------------------------------------------
    # Train / test split
    # -------------------------------------------------------------------
    train = df_cur.iloc[:-steps] if steps < len(df_cur) else df_cur.iloc[:-1]
    test = df_cur.iloc[-steps:] if steps < len(df_cur) else df_cur.iloc[-1:]
    actual_test = test["Rate"].values

    # -------------------------------------------------------------------
    # ARIMA
    # -------------------------------------------------------------------
    arima_pred = None
    arima_metrics = None
    arima_fitted = False
    try:
        arima_model = fit_arima(train["Rate"], order=(2, 1, 2))
        arima_pred = forecast_next(arima_model, steps=steps)
        arima_metrics = compute_metrics(actual_test, arima_pred[:len(actual_test)])
        arima_fitted = arima_model.get("fitted", False)
    except Exception as e:
        logger.warning(f"ARIMA pipeline failed: {e}")

    # -------------------------------------------------------------------
    # Prophet (stub, unchanged – see note below)
    # -------------------------------------------------------------------
    prophet_pred = None
    prophet_metrics = None
    try:
        df_prophet = pd.DataFrame({
            "ds": train["Time_dt"],
            "y": train["Rate"].astype(float)
        })
        prophet_model = fit_prophet(df_prophet)
        forecast_df = forecast_future(prophet_model, periods=steps, freq=freq)
        prophet_pred = forecast_df["yhat"].tolist()
        prophet_metrics = compute_metrics(actual_test, prophet_pred[:len(actual_test)])
    except Exception:
        pass

    # -------------------------------------------------------------------
    # Signals
    # -------------------------------------------------------------------
    current_rate = df_cur["Rate"].iloc[-1]
    arima_signal = generate_trade_signal(current_rate, arima_pred[0]) if arima_pred else "HOLD"
    prophet_signal = generate_trade_signal(current_rate, prophet_pred[0]) if prophet_pred else "HOLD"

    return {
        "currency": currency,
        "current_rate": current_rate,
        "arima_forecast": arima_pred[0] if arima_pred else None,
        "prophet_forecast": prophet_pred[0] if prophet_pred else None,
        "arima_signal": arima_signal,
        "prophet_signal": prophet_signal,
        "arima_all_preds": arima_pred,
        "prophet_all_preds": prophet_pred,
        "arima_metrics": arima_metrics,
        "prophet_metrics": prophet_metrics,
        "actual_test": actual_test,
        "train": train,
        "test": test,
        "warning": None,
        "arima_fitted": arima_fitted
    }