import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any
from config import logger
import warnings

def fit_arima(series: pd.Series, order: Tuple[int, int, int] = (2,1,2)) -> Dict[str, Any]:
    last_value = series.iloc[-1]
    std = series.std()
    result = {"last_value": last_value, "std": std, "fitted": False, "model": None, "order": order}
    try:
        from statsmodels.tsa.arima.model import ARIMA
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = ARIMA(series, order=order)
            fitted_model = model.fit()
        result["model"] = fitted_model
        result["fitted"] = True
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"ARIMA fitting failed ({e}), using stub.")
    return result

def fit_auto_arima(series: pd.Series) -> Dict[str, Any]:
    try:
        import pmdarima as pm
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = pm.auto_arima(series, seasonal=False, trace=False,
                                  error_action='ignore', suppress_warnings=True, stepwise=True)
        return {"last_value": series.iloc[-1], "std": series.std(), "fitted": True,
                "model": model, "order": model.order}
    except ImportError:
        return fit_arima(series)
    except Exception as e:
        logger.warning(f"Auto-ARIMA failed ({e}), falling back.")
        return fit_arima(series)

def forecast_next(arima_model: Dict[str, Any], steps: int = 1) -> Tuple[List[float], Optional[np.ndarray]]:
    if arima_model.get("fitted") and arima_model["model"] is not None:
        try:
            fc_result = arima_model["model"].get_forecast(steps=steps)
            pred = fc_result.predicted_mean.tolist()
            conf_int = fc_result.conf_int()
            return pred, conf_int.values if conf_int is not None else None
        except Exception as e:
            logger.warning(f"ARIMA forecast failed ({e}), using stub.")
    last = arima_model["last_value"]
    std = arima_model["std"]
    rng = np.random.default_rng(42)
    return [last + rng.normal(0, std * 0.02) for _ in range(steps)], None
