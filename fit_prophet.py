def fit_prophet(df_rates):
    try:
        from prophet import Prophet
        m = Prophet()
        m.fit(df_rates.rename(columns={"ds": "ds", "y": "y"}))
        return {"model": m, "fitted": True, ...}
    except ImportError:
        # fallback to linear stub
        ...