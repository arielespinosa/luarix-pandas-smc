import pandas as pd

from pandas_luarix._core.pivots import find_pivots

_EVENT_COLUMNS = [
    "position",
    "prior_position",
    "divergence_type",
    "direction",
    "price",
    "prior_price",
    "indicator_value",
    "prior_indicator_value",
]


def detect_divergence(
    high: pd.Series, low: pd.Series, indicator: pd.Series, length: int = 5
) -> pd.DataFrame:
    """
    Detecta pivotes CONFIRMADOS solo de `indicator` (reusa find_pivots(indicator,
    indicator, length) — pasar la misma serie dos veces pivota una serie única,
    igual que hace `stochastic_oscillator` internamente). En cada par CONSECUTIVO
    de pivotes bajos del indicador compara `low` (precio) vs `indicator` en esas 2
    barras; en cada par consecutivo de pivotes altos compara `high` vs `indicator`.

    Clasificación:
        regular_bullish : price LL (low2 < low1)   e indicator HL (ind2 > ind1)
        hidden_bullish  : price HL (low2 > low1)   e indicator LL (ind2 < ind1)
        regular_bearish : price HH (high2 > high1) e indicator LH (ind2 < ind1)
        hidden_bearish  : price LH (high2 < high1) e indicator HH (ind2 > ind1)

    Devuelve un DataFrame (una fila por evento, `position` = posición del segundo
    pivote) con: `position`, `prior_position`, `divergence_type`, `direction`
    (1 alcista / -1 bajista), `price`, `prior_price`, `indicator_value`,
    `prior_indicator_value`.
    """
    ind_pivot_high, ind_pivot_low = find_pivots(indicator, indicator, length)

    low_origins = ind_pivot_low.notna().to_numpy().nonzero()[0] - length
    high_origins = ind_pivot_high.notna().to_numpy().nonzero()[0] - length

    low_np = low.to_numpy()
    high_np = high.to_numpy()
    indicator_np = indicator.to_numpy()

    events = []

    for p1, p2 in zip(low_origins[:-1], low_origins[1:]):
        price1, price2 = low_np[p1], low_np[p2]
        ind1, ind2 = indicator_np[p1], indicator_np[p2]
        if price2 < price1 and ind2 > ind1:
            divergence_type = "regular_bullish"
        elif price2 > price1 and ind2 < ind1:
            divergence_type = "hidden_bullish"
        else:
            continue
        events.append(
            {
                "position": p2,
                "prior_position": p1,
                "divergence_type": divergence_type,
                "direction": 1,
                "price": price2,
                "prior_price": price1,
                "indicator_value": ind2,
                "prior_indicator_value": ind1,
            }
        )

    for p1, p2 in zip(high_origins[:-1], high_origins[1:]):
        price1, price2 = high_np[p1], high_np[p2]
        ind1, ind2 = indicator_np[p1], indicator_np[p2]
        if price2 > price1 and ind2 < ind1:
            divergence_type = "regular_bearish"
        elif price2 < price1 and ind2 > ind1:
            divergence_type = "hidden_bearish"
        else:
            continue
        events.append(
            {
                "position": p2,
                "prior_position": p1,
                "divergence_type": divergence_type,
                "direction": -1,
                "price": price2,
                "prior_price": price1,
                "indicator_value": ind2,
                "prior_indicator_value": ind1,
            }
        )

    if not events:
        return pd.DataFrame(columns=_EVENT_COLUMNS)

    return pd.DataFrame(events).sort_values("position").reset_index(drop=True)
