import numpy as np
import pandas as pd

from pandas_luarix._core.enums import ObMitigation

_EMPTY_COLUMNS = ["ob_bar_index", "confirmed_bar_index", "top", "bottom", "direction"]


def build_order_blocks(
    df: pd.DataFrame,
    events: pd.DataFrame,
    parsed_high: pd.Series,
    parsed_low: pd.Series,
) -> pd.DataFrame:
    """
    For each structure event (BOS/CHoCH), finds the order-block origin bar:
    the extremum of parsed_low (bullish) or parsed_high (bearish) between the
    pivot's origin bar and the bar that broke it.
    """
    if events.empty:
        return pd.DataFrame(columns=_EMPTY_COLUMNS)

    ph = parsed_high.to_numpy()
    pl = parsed_low.to_numpy()

    rows = []
    for pivot_pos, broken_pos, direction in zip(
        events["pivot_bar_index"].to_numpy(),
        events["broken_bar_index"].to_numpy(),
        events["direction"].to_numpy(),
    ):
        pivot_pos = int(pivot_pos)
        broken_pos = int(broken_pos)
        direction = int(direction)
        if broken_pos <= pivot_pos:
            continue
        if direction == 1:
            segment = pl[pivot_pos:broken_pos]
            local_idx = int(np.argmin(segment))
        else:
            segment = ph[pivot_pos:broken_pos]
            local_idx = int(np.argmax(segment))
        ob_pos = pivot_pos + local_idx
        rows.append((ob_pos, broken_pos, ph[ob_pos], pl[ob_pos], direction))

    if not rows:
        return pd.DataFrame(columns=_EMPTY_COLUMNS)
    return pd.DataFrame(rows, columns=_EMPTY_COLUMNS)


def mitigate_order_blocks(
    df: pd.DataFrame,
    order_blocks: pd.DataFrame,
    *,
    mitigation: ObMitigation = ObMitigation.HIGH_LOW,
) -> pd.DataFrame:
    """Adds a `mitigated` bool column; never drops rows (mitigated OBs are retained)."""
    mitigation = ObMitigation(mitigation)
    if order_blocks.empty:
        result = order_blocks.copy()
        result["mitigated"] = pd.Series(dtype=bool)
        return result

    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    source_bear = close if mitigation is ObMitigation.CLOSE else high
    source_bull = close if mitigation is ObMitigation.CLOSE else low

    mitigated = []
    for confirmed_pos, top, bottom, direction in zip(
        order_blocks["confirmed_bar_index"].to_numpy(),
        order_blocks["top"].to_numpy(),
        order_blocks["bottom"].to_numpy(),
        order_blocks["direction"].to_numpy(),
    ):
        start = int(confirmed_pos) + 1
        if direction == -1:
            seg = source_bear[start:]
            mit = bool((seg > top).any()) if len(seg) else False
        else:
            seg = source_bull[start:]
            mit = bool((seg < bottom).any()) if len(seg) else False
        mitigated.append(mit)

    result = order_blocks.copy()
    result["mitigated"] = mitigated
    return result
