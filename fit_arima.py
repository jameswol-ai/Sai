import warnings
import numpy as np
import pandas as pd

def fit_arima(series: pd.Series, order: tuple = (2,1,2)) -> dict:
    """
    Fit an ARIMA model to a time series.
    Returns a dict with the fitted model object (if available)
    plus fallback statistics for the stub.
    """
    last_value = series.iloc[-1]
    std = series.std()
    
    try:
        from statsmodels.tsa.arima.model import ARIMA
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = ARIMA(series, order=order)
            fitted = model.fit()
        return {
            "model": fitted,
            "last_value": last_value,
            "std": std,
            "fitted": True   # flag indicating we have a real model
        }
    except ImportError:
        # statsmodels not installed – fallback to stub behavior
        return {"last_value": last_value, "std": std, "fitted": False}