import pandas as pd
import numpy as np

def compute_indicators(df_cur, rsi_period=14, sma_windows=[20,50],
                       macd_fast=12, macd_slow=26, macd_signal=9,
                       bb_period=20, bb_std=2, stoch_k=14, stoch_d=3, atr_period=14):
    df = df_cur.copy().sort_values("Time_dt")
    min_len = max(rsi_period, macd_slow, bb_period, stoch_k, atr_period) + 1
    if len(df) < min_len:
        return None
    delta = df["Rate"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=rsi_period, min_periods=rsi_period).mean()
    avg_loss = loss.rolling(window=rsi_period, min_periods=rsi_period).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    for w in sma_windows:
        df[f"SMA_{w}"] = df["Rate"].rolling(window=w, min_periods=w).mean()
    ema_fast = df["Rate"].ewm(span=macd_fast, min_periods=macd_fast).mean()
    ema_slow = df["Rate"].ewm(span=macd_slow, min_periods=macd_slow).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_signal"] = df["MACD"].ewm(span=macd_signal, min_periods=macd_signal).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    df["BB_middle"] = df["Rate"].rolling(window=bb_period, min_periods=bb_period).mean()
    bb_std_dev = df["Rate"].rolling(window=bb_period, min_periods=bb_period).std()
    df["BB_upper"] = df["BB_middle"] + bb_std * bb_std_dev
    df["BB_lower"] = df["BB_middle"] - bb_std * bb_std_dev
    low_min = df["Rate"].rolling(window=stoch_k, min_periods=stoch_k).min()
    high_max = df["Rate"].rolling(window=stoch_k, min_periods=stoch_k).max()
    df["Stoch_%K"] = 100 * (df["Rate"] - low_min) / (high_max - low_min)
    df["Stoch_%D"] = df["Stoch_%K"].rolling(window=stoch_d, min_periods=stoch_d).mean()
    rng = np.random.RandomState(42)
    volume = rng.randint(500, 2000, size=len(df))
    obv = [0]
    for i in range(1, len(df)):
        if df["Rate"].iloc[i] > df["Rate"].iloc[i-1]:
            obv.append(obv[-1] + volume[i])
        elif df["Rate"].iloc[i] < df["Rate"].iloc[i-1]:
            obv.append(obv[-1] - volume[i])
        else:
            obv.append(obv[-1])
    df["OBV"] = obv
    high = df["Rate"] * (1 + rng.uniform(0, 0.001, len(df)))
    low = df["Rate"] * (1 - rng.uniform(0, 0.001, len(df)))
    prev_close = df["Rate"].shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR"] = true_range.rolling(window=atr_period, min_periods=atr_period).mean()
    return df
