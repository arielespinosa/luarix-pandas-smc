import pandas as pd


def detect_liquidity_sweeps(
    df: pd.DataFrame,
    levels: pd.DataFrame,
    *,
    level_price_col: str,
    origin_pos_col: str,
    level_type: str,
    is_high: bool,
    start_offset: int = 0,
    max_confirmation_bars: int = 1,
) -> pd.DataFrame:
    """
    For each level (price + the bar position it was formed at), scans up to
    `max_confirmation_bars` forward bars (starting from
    `origin_pos + start_offset + 1`) for a wick beyond the level whose
    close comes back inside it (a stop hunt / liquidity grab).
    Returns one row per sweep at the sweeping bar, columns swept_level,
    swept_level_type, direction (1 bullish sweep-of-a-low, -1 bearish
    sweep-of-a-high).
    """
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    n = len(df)

    positions = []
    swept_levels = []
    directions = []

    for level_price, origin_position in zip(levels[level_price_col], levels[origin_pos_col]):
        origin_position = int(origin_position) + start_offset
        for k in range(1, max_confirmation_bars + 1):
            position = origin_position + k
            if position >= n:
                break
            if is_high:
                wicked = high[position] > level_price
                closed_back = close[position] < level_price
            else:
                wicked = low[position] < level_price
                closed_back = close[position] > level_price
            if wicked and closed_back:
                positions.append(position)
                swept_levels.append(level_price)
                directions.append(-1 if is_high else 1)
                break

    if not positions:
        return pd.DataFrame(columns=["swept_level", "swept_level_type", "direction"])

    result = pd.DataFrame(
        {
            "swept_level": swept_levels,
            "swept_level_type": [level_type] * len(positions),
            "direction": directions,
        },
        index=df.index[positions],
    )
    return result
