# -------------------- ARIMA (Real Implementation) --------------------
import warnings
import numpy as np
import pandas as pd
from typing import Dict, Any, List

def fit_arima(series: pd.Series, order: tuple = (2,1,2)) -> Dict[str, Any]:
    """
    Fit an ARIMA model to a time series.
    Uses statsmodels if available, otherwise falls back to a naive stub.
    """
    last_value = series.iloc[-1]
    std = series.std()
    result = {
        "last_value": last_value,
        "std": std,
        "fitted": False,           # True if a real model was successfully fitted
        "model": None,
        "order": order
    }

    try:
        from statsmodels.tsa.arima.model import ARIMA
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = ARIMA(series, order=order)
            fitted_model = model.fit()
        result["model"] = fitted_model
        result["fitted"] = True
        return result
    except ImportError:
        # statsmodels not installed – fallback stub
        return result
    except Exception as e:
        logger.warning(f"ARIMA fitting failed ({e}), using stub.")
        return result


def forecast_next(arima_model: Dict[str, Any], steps: int = 1) -> List[float]:
    """
    Produce forecasted values from the fitted model.
    If the model is a stub, returns random perturbations around the last value.
    """
    if arima_model.get("fitted") and arima_model["model"] is not None:
        try:
            fc = arima_model["model"].forecast(steps=steps)
            return fc.tolist()
        except Exception as e:
            logger.warning(f"ARIMA forecast call failed ({e}), falling back to stub.")
            # Fall through to stub

    # Stub fallback
    last = arima_model["last_value"]
    std = arima_model["std"]
    rng = np.random.default_rng(42)   # local, isolated seed
    return [last + rng.normal(0, std * 0.02) for _ in range(steps)]

def fit_auto_arima(series: pd.Series) -> Dict[str, Any]:
    """
    Auto-ARIMA using pmdarima. Falls back to fit_arima if not installed.
    """
    try:
        import pmdarima as pm
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = pm.auto_arima(
                series, seasonal=False, trace=False,
                error_action='ignore', suppress_warnings=True,
                stepwise=True
            )
        return {
            "last_value": series.iloc[-1],
            "std": series.std(),
            "fitted": True,
            "model": model,
            "order": model.order
        }
    except ImportError:
        return fit_arima(series)   # fixed-order fallback
    except Exception as e:
        logger.warning(f"Auto-ARIMA failed ({e}), using fixed order fallback.")
        return fit_arima(series)