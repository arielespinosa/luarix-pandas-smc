import numpy as np
import pandas as pd


def fib_expansion(
    pivot_high: pd.Series,
    pivot_low: pd.Series,
    length: int,
    ratios: tuple[float, ...] = (1.272, 1.414, 1.618),
) -> pd.DataFrame:
    """
    Automatically detect A-B-C patterns from alternating swing highs/lows
    and compute Fibonacci expansion targets (D) for each ratio.

    Bullish pattern (low -> high -> low):
        A = swing low (start of impulse)
        B = swing high (end of impulse)
        C = swing low (retracement)
        D = C + (B - A) * ratio   (projected upward)

    Bearish pattern (high -> low -> high):
        A = swing high
        B = swing low
        C = swing high (retracement)
        D = C - (A - B) * ratio   (projected downward)

    Returns a DataFrame with one row per (pattern, ratio) combination:
        a_time, a_price, b_time, b_price, c_time, c_price,
        ratio, d_price, direction (1 bullish / -1 bearish)
    """
    # Stack swing highs and lows into one sorted timeline
    rows = []
    for pos in (pivot_high.notna().to_numpy().nonzero()[0]):
        origin = pos - length
        if origin >= 0:
            rows.append({"pos": origin, "price": float(pivot_high.iloc[pos]), "type": "high"})
    for pos in (pivot_low.notna().to_numpy().nonzero()[0]):
        origin = pos - length
        if origin >= 0:
            rows.append({"pos": origin, "price": float(pivot_low.iloc[pos]), "type": "low"})

    rows.sort(key=lambda r: r["pos"])

    if len(rows) < 3:
        return pd.DataFrame(
            columns=["a_pos", "a_price", "b_pos", "b_price", "c_pos", "c_price",
                     "ratio", "d_price", "direction"]
        )

    result_rows = []
    for i in range(len(rows) - 2):
        a, b, c = rows[i], rows[i + 1], rows[i + 2]
        # Must alternate: low-high-low (bullish) or high-low-high (bearish)
        if a["type"] == "low" and b["type"] == "high" and c["type"] == "low":
            impulse = b["price"] - a["price"]
            for ratio in ratios:
                d_price = c["price"] + impulse * ratio
                result_rows.append({
                    "a_pos": a["pos"], "a_price": a["price"],
                    "b_pos": b["pos"], "b_price": b["price"],
                    "c_pos": c["pos"], "c_price": c["price"],
                    "ratio": ratio, "d_price": d_price, "direction": 1,
                })
        elif a["type"] == "high" and b["type"] == "low" and c["type"] == "high":
            impulse = a["price"] - b["price"]
            for ratio in ratios:
                d_price = c["price"] - impulse * ratio
                result_rows.append({
                    "a_pos": a["pos"], "a_price": a["price"],
                    "b_pos": b["pos"], "b_price": b["price"],
                    "c_pos": c["pos"], "c_price": c["price"],
                    "ratio": ratio, "d_price": d_price, "direction": -1,
                })

    if not result_rows:
        return pd.DataFrame(
            columns=["a_pos", "a_price", "b_pos", "b_price", "c_pos", "c_price",
                     "ratio", "d_price", "direction"]
        )

    return pd.DataFrame(result_rows)
