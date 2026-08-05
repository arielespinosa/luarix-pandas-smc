import numpy as np
import pandas as pd

from pandas_luarix._core.validation import check_positive_float, check_positive_int
from pandas_luarix._core.volatility import compute_atr


def _is_mitigated_after(close: np.ndarray, level: float, after_pos: int, *, is_high: bool) -> bool:
    seg = close[after_pos + 1 :]
    if len(seg) == 0:
        return False
    return bool((seg > level).any()) if is_high else bool((seg < level).any())


def detect_equal_levels_atr_pivot(
    df: pd.DataFrame,
    pivot_series: pd.Series,
    length: int,
    *,
    atr_period: int = 200,
    equal_threshold: float = 0.1,
    is_high: bool,
) -> list[pd.DataFrame]:
    """
    Compares each confirmed pivot only to the immediately preceding pivot of
    the same type (single-slot persistent state, matches the reference).
    Tolerance = equal_threshold * ATR(atr_period) at the confirming bar.

    `mitigated` is computed PER MEMBER (each row checked against its OWN
    level/origin), not broadcast from the latest pivot to both rows -- see
    `detect_equal_levels_price_proximity` for why this matters once a group
    can have more than 2 members. For a 2-member group this is exactly
    equivalent to the previous single-value-per-group behavior whenever
    BOTH members end up mitigated or neither does, and more precise when
    only one of the two individually is.
    """
    average_true_range = compute_atr(df["high"], df["low"], df["close"], period=atr_period)
    close = df["close"].to_numpy()
    positions = np.flatnonzero(~pivot_series.isna())

    groups: list[pd.DataFrame] = []
    prev_pos = None
    prev_level = None
    for pos in positions:
        level = pivot_series.iloc[pos]
        if prev_pos is not None:
            threshold = equal_threshold * average_true_range.iloc[pos]
            if not np.isnan(threshold) and abs(level - prev_level) < threshold:
                origin_prev = prev_pos - length
                origin_curr = pos - length
                if origin_prev >= 0 and origin_curr >= 0:
                    idx = df.index[[origin_prev, origin_curr]]
                    group_df = df.loc[idx].copy()
                    group_df["mitigated"] = [
                        _is_mitigated_after(close, prev_level, origin_prev, is_high=is_high),
                        _is_mitigated_after(close, level, origin_curr, is_high=is_high),
                    ]
                    groups.append(group_df)
        prev_pos = pos
        prev_level = level
    return groups


def detect_equal_levels_price_proximity(
    df: pd.DataFrame,
    pivot_series: pd.Series,
    length: int,
    *,
    tolerance_pct: float = 0.003,
    search_window: int | None = None,
    is_high: bool,
) -> list[pd.DataFrame]:
    """
    Groups ALL confirmed pivots of one side whose price falls within
    `tolerance_pct` of each other -- not just adjacent pairs like
    `detect_equal_levels_atr_pivot`. Pivot A and pivot C group together even
    if an unrelated pivot B sits between them chronologically at a
    different price; a cluster can have 2, 3, or more members.

    `search_window`: how many of the MOST RECENT bars to draw candidate
    pivots from. `None` (default) means the entire available history --
    new candles can always surface a match against an old, still-standing
    level, so there is no reason to cap this unless the caller explicitly
    wants to.

    Sorts candidates by price first, so only ADJACENT values in that order
    ever need comparing (a cluster is a run of sorted values each within
    `tolerance_pct` of the run's first member) -- O(n log n) instead of
    comparing every pivot against every other one.

    `mitigated` is computed PER MEMBER (its own level, checked against ALL
    subsequent closes -- same convention as `smc.swing_high`/`swing_low`),
    not per group: `_equal_side`'s `include_mitigated=False` filter trims
    only the stale members of a cluster, keeping the rest as a (possibly
    smaller) still-live group.
    """
    check_positive_int("length", length)
    check_positive_float("tolerance_pct", tolerance_pct)
    if search_window is not None:
        check_positive_int("search_window", search_window)

    confirm_positions = np.flatnonzero(~pivot_series.isna())
    if search_window is not None:
        cutoff = len(df) - search_window
        confirm_positions = confirm_positions[confirm_positions >= cutoff]

    levels = pivot_series.to_numpy()[confirm_positions]
    origins = confirm_positions - length
    valid = origins >= 0
    levels, origins = levels[valid], origins[valid]
    if len(origins) < 2:
        return []

    close = df["close"].to_numpy()

    order = np.argsort(levels)
    levels, origins = levels[order], origins[order]

    groups: list[pd.DataFrame] = []
    cluster_start = 0
    n = len(levels)
    for i in range(1, n + 1):
        # El ancla es el PRIMER valor del cluster, no el anterior -- así una
        # cadena de valores que se van alejando de a poco (cada uno dentro
        # de tolerancia del previo, pero el primero y el último no) no se
        # agrupa como si fueran "iguales" entre sí.
        anchor = levels[cluster_start]
        if i < n and abs(levels[i] - anchor) <= tolerance_pct * abs(anchor):
            continue
        if i - cluster_start >= 2:
            member_levels = levels[cluster_start:i]
            member_origins = origins[cluster_start:i]
            chrono = np.argsort(member_origins)
            member_levels = member_levels[chrono]
            member_origins = member_origins[chrono]
            idx = df.index[member_origins]
            group_df = df.loc[idx].copy()
            group_df["mitigated"] = [
                _is_mitigated_after(close, lvl, origin, is_high=is_high)
                for lvl, origin in zip(member_levels, member_origins)
            ]
            groups.append(group_df)
        cluster_start = i
    return groups
