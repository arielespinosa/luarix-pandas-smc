import numpy as np
import pandas as pd

from pandas_luarix._core.volatility import compute_atr


def detect_fair_value_gaps(
    df: pd.DataFrame,
    *,
    min_gap_atr_multiple: float = 0.0,
    atr_period: int = 200,
) -> pd.DataFrame:
    """
    Classic 3-candle gap, fully vectorized. Returns one row per detected gap
    at the confirming (3rd) bar, columns top/bottom/direction.

    The middle candle must ALSO be directionally biased on its own terms
    (`close[-1] > open[-1]` for bullish, `close[-1] < open[-1]` for
    bearish) -- not just leave a technical gap. Verified against the
    reference LuxAlgo implementation (`app/tradingview/smc_indicator.py::
    _detect_fair_value_gaps`, `bar_delta > threshold` with the optional
    size-threshold feature off, i.e. `threshold=0`): a middle candle that
    gaps up hugely at the open but closes back down (bearish on its own
    body) while still closing above `high[-2]` used to count here as a
    bullish gap and does NOT in the reference -- real, demonstrated
    divergence, not a design choice.
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    open_ = df["open"]
    high2 = high.shift(2)
    low2 = low.shift(2)
    close1 = close.shift(1)
    open1 = open_.shift(1)

    bullish = (low > high2) & (close1 > high2) & (close1 > open1)
    bearish = (high < low2) & (close1 < low2) & (close1 < open1)

    top = pd.Series(np.where(bullish, low, np.where(bearish, low2, np.nan)), index=df.index)
    bottom = pd.Series(np.where(bullish, high2, np.where(bearish, high, np.nan)), index=df.index)
    direction = np.where(bullish, 1, np.where(bearish, -1, 0))
    mask = bullish | bearish

    if min_gap_atr_multiple > 0:
        atr = compute_atr(high, low, close, period=atr_period)
        gap_size = (top - bottom).abs()
        mask = mask & (gap_size >= (min_gap_atr_multiple * atr)).fillna(False)

    result = pd.DataFrame(
        {
            "top": top[mask],
            "bottom": bottom[mask],
            "direction": pd.Series(direction, index=df.index)[mask].astype(int),
        }
    )
    return result


def mark_filled_fvgs(df: pd.DataFrame, fvgs: pd.DataFrame) -> pd.DataFrame:
    """Adds `filled` bool column; never drops rows (filled FVGs are retained)."""
    if fvgs.empty:
        result = fvgs.copy()
        result["filled"] = pd.Series(dtype=bool)
        return result

    low = df["low"].to_numpy()
    high = df["high"].to_numpy()
    positions = df.index.get_indexer(fvgs.index)

    filled = []
    for pos, top, bottom, direction in zip(positions, fvgs["top"], fvgs["bottom"], fvgs["direction"]):
        if direction == 1:
            seg_low = low[pos + 1 :]
            filled.append(bool((seg_low < bottom).any()) if len(seg_low) else False)
        else:
            seg_high = high[pos + 1 :]
            filled.append(bool((seg_high > top).any()) if len(seg_high) else False)

    result = fvgs.copy()
    result["filled"] = filled
    return result
