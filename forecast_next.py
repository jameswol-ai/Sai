def forecast_next(arima_model: dict, steps: int = 1) -> list:
    if arima_model.get("fitted"):
        # Real ARIMA model
        try:
            fc = arima_model["model"].forecast(steps=steps)
            return fc.tolist()
        except Exception as e:
            # If forecasting fails, fall back to stub
            logger.warning(f"ARIMA forecast failed, using fallback: {e}")
            # fall through to stub below
            pass

    # Stub fallback
    last = arima_model["last_value"]
    std = arima_model["std"]
    rng = np.random.default_rng(42)  # local random state
    return [last + rng.normal(0, std * 0.02) for _ in range(steps)]