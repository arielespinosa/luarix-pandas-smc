import numpy as np
import pandas as pd


def compute_leg(high: pd.Series, low: pd.Series, length: int) -> pd.Series:
    """
    Vectorized leg/trend-direction primitive: at each bar, determine whether
    the bar `length` positions back was a confirmed local high (leg turns
    bearish, 0) or a confirmed local low (leg turns bullish, 1), given the
    `length` bars that followed it. Persists (ffill) between flips.
    """
    pivot_bar_high = high.shift(length)
    window_high = high.rolling(length).max()
    pivot_bar_low = low.shift(length)
    window_low = low.rolling(length).min()

    new_leg_high = pivot_bar_high > window_high
    new_leg_low = pivot_bar_low < window_low

    raw = pd.Series(np.nan, index=high.index)
    raw[new_leg_low] = 1
    raw[new_leg_high] = 0
    leg = raw.ffill().fillna(0).astype("int8")
    return leg


def find_pivots(high: pd.Series, low: pd.Series, length: int) -> tuple[pd.Series, pd.Series]:
    """
    Returns (pivot_high, pivot_low): float Series aligned to the input index,
    NaN everywhere except at the bar where a pivot is CONFIRMED (bar i), with
    the pivot price itself belonging to bar i-length.
    """
    leg = compute_leg(high, low, length)
    prev_leg = leg.shift(1)
    new_pivot = leg != prev_leg
    leg_delta = leg.astype("int64") - prev_leg.astype("float64")

    is_pivot_low = new_pivot & (leg_delta == 1)
    is_pivot_high = new_pivot & (leg_delta == -1)

    pivot_low = pd.Series(np.nan, index=low.index)
    pivot_low[is_pivot_low] = low.shift(length)[is_pivot_low]

    pivot_high = pd.Series(np.nan, index=high.index)
    pivot_high[is_pivot_high] = high.shift(length)[is_pivot_high]

    return pivot_high, pivot_low
