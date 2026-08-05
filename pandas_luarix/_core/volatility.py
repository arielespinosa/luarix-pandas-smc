import numpy as np
import pandas as pd

from pandas_luarix._core.enums import VolatilityMethod


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    ranges = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    )
    tr = ranges.max(axis=1)
    tr.iloc[0] = (high.iloc[0] - low.iloc[0])
    return tr


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 200) -> pd.Series:
    """
    Wilder ATR, seeded with the SMA of the first `period` true ranges before
    the recursive smoothing kicks in (not a plain `.ewm()` cold-start) —
    matches the reference indicator bit-for-bit; a naive `.ewm(adjust=False)`
    from bar 0 diverges from this by ~10% for hundreds of bars.
    """
    tr = true_range(high, low, close)
    n = len(tr)
    atr = pd.Series(np.nan, index=tr.index)
    if n < period:
        return atr

    seed = tr.iloc[:period].mean()
    tail = tr.iloc[period:]
    combined = pd.concat([pd.Series([seed]), tail], ignore_index=True)
    smoothed = combined.ewm(alpha=1.0 / period, adjust=False).mean()
    atr.iloc[period - 1 :] = smoothed.to_numpy()
    return atr


def compute_cumulative_mean_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    return true_range(high, low, close).expanding().mean()


def expansion_bars(
    high: pd.Series, low: pd.Series, close: pd.Series, *, atr_period: int = 200, multiplier: float = 2.0
) -> pd.Series:
    """
    Boolean mask, True at bar i if THIS bar's range (high-low) is >=
    `multiplier` times the Wilder ATR of `atr_period` -- a genuine
    volatility/range expansion bar. Reuses the exact same comparison
    `parsed_high_low` already validates internally for Order Block filtering
    (`high_vol_bar`), just exposed here as its own standalone concept.
    """
    vol = compute_atr(high, low, close, period=atr_period)
    return ((high - low) >= (multiplier * vol)).fillna(False)


def consolidation_windows(
    high: pd.Series, low: pd.Series, close: pd.Series, *, window: int = 10, atr_period: int = 200,
    multiplier: float = 1.0,
) -> pd.Series:
    """
    Boolean mask, True at bar i if the total price excursion over the last
    `window` bars (rolling max(high) - rolling min(low)) is <= `multiplier`
    times the Wilder ATR of `atr_period` -- price stayed CONTAINED over that
    stretch instead of trending. Same ATR baseline as `expansion_bars`, just
    measured over a window instead of a single bar -- the two are meant to
    be read as complementary regimes, not independent indicators.
    """
    vol = compute_atr(high, low, close, period=atr_period)
    window_range = high.rolling(window).max() - low.rolling(window).min()
    return (window_range <= (multiplier * vol)).fillna(False)


def parsed_high_low(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    *,
    atr_period: int = 200,
    high_vol_multiplier: float = 2.0,
    volatility_method: VolatilityMethod = VolatilityMethod.ATR,
) -> tuple[pd.Series, pd.Series]:
    volatility_method = VolatilityMethod(volatility_method)
    if volatility_method is VolatilityMethod.ATR:
        vol = compute_atr(high, low, close, period=atr_period)
    else:
        vol = compute_cumulative_mean_range(high, low, close)

    high_vol_bar = (high - low) >= (high_vol_multiplier * vol)
    high_vol_bar = high_vol_bar.fillna(False)

    parsed_high = pd.Series(np.where(high_vol_bar, low, high), index=high.index)
    parsed_low = pd.Series(np.where(high_vol_bar, high, low), index=low.index)
    return parsed_high, parsed_low
