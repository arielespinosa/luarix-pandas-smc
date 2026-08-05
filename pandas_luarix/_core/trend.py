import numpy as np
import pandas as pd

BOS = "BOS"
CHOCH = "CHOCH"


def track_structure_events(
    df: pd.DataFrame,
    pivot_high: pd.Series,
    pivot_low: pd.Series,
    length: int,
    *,
    confluence_filter: bool = False,
) -> pd.DataFrame:
    """
    Stateful scan (not vectorizable — trend state and "currently tracked,
    not-yet-crossed pivot" persist across bars): whenever price closes
    beyond the currently tracked, unbroken pivot high/low, that's a BOS
    (trend continues or was unset) or a CHoCH (trend reverses).

    Returns a DataFrame indexed by position with columns:
      pivot_bar_index (int, position of the pivot's origin bar),
      broken_bar_index (int, position of the bar where the break/cross fired),
      pivot_level (float), direction (1 bullish / -1 bearish),
      structure_type ('BOS' | 'CHOCH').
    """
    n = len(df)
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    open_ = df["open"].to_numpy()
    ph = pivot_high.to_numpy()
    pl = pivot_low.to_numpy()

    tracked_high = None  # (level, origin_pos, crossed)
    tracked_low = None
    trend = 0

    rows = []

    for i in range(n):
        if not np.isnan(ph[i]):
            origin_pos = i - length
            if origin_pos >= 0:
                tracked_high = [ph[i], origin_pos, False]
        if not np.isnan(pl[i]):
            origin_pos = i - length
            if origin_pos >= 0:
                tracked_low = [pl[i], origin_pos, False]

        if i == 0:
            continue
        prev_close = close[i - 1]

        if tracked_high is not None and not tracked_high[2]:
            level = tracked_high[0]
            crossed_up = prev_close < level <= close[i]
            if crossed_up and confluence_filter:
                body_top = max(open_[i], close[i])
                body_bottom = min(open_[i], close[i])
                bullish_bar = (high[i] - body_top) > (body_bottom - low[i])
                crossed_up = crossed_up and bullish_bar
            if crossed_up:
                tracked_high[2] = True
                structure_type = CHOCH if trend == -1 else BOS
                trend = 1
                rows.append((tracked_high[1], i, level, 1, structure_type))

        if tracked_low is not None and not tracked_low[2]:
            level = tracked_low[0]
            crossed_down = prev_close > level >= close[i]
            if crossed_down and confluence_filter:
                body_top = max(open_[i], close[i])
                body_bottom = min(open_[i], close[i])
                bearish_bar = (body_bottom - low[i]) > (high[i] - body_top)
                crossed_down = crossed_down and bearish_bar
            if crossed_down:
                tracked_low[2] = True
                structure_type = CHOCH if trend == 1 else BOS
                trend = -1
                rows.append((tracked_low[1], i, level, -1, structure_type))

    if not rows:
        return pd.DataFrame(
            columns=["pivot_bar_index", "broken_bar_index", "pivot_level", "direction", "structure_type"]
        )

    rows.sort(key=lambda r: r[1])
    result = pd.DataFrame(
        rows, columns=["pivot_bar_index", "broken_bar_index", "pivot_level", "direction", "structure_type"]
    )
    result.index = df.index[result["broken_bar_index"].to_numpy()]
    return result
