"""Tests de detección de expansiones IPDA con pivotes sintéticos.

Se construyen las Series `pivot_high`/`pivot_low` a mano (como las devolvería
`find_pivots`: no-NaN en la vela de confirmación, origen = confirm - length),
de modo que el test es autónomo y no depende del resto del `_core`.
"""
import numpy as np
import pandas as pd
import pytest

from pandas_luarix._core.fractals import detect_ipda_expansions


def _pivots(points, length, n_bars, base_close):
    """points: list de (origin_pos, price, kind[+1 high/-1 low]).
    Devuelve (pivot_high, pivot_low, close)."""
    ph = pd.Series([np.nan] * n_bars, dtype=float)
    pl = pd.Series([np.nan] * n_bars, dtype=float)
    for origin, price, kind in points:
        confirm = origin + length
        (ph if kind == 1 else pl).iloc[confirm] = price
    close = pd.Series(base_close, dtype=float)
    return ph, pl, close


def test_bullish_impulse_x12345_detected_full_compliance():
    length = 2
    points = [
        (0, 100.0, -1),   # X  low
        (2, 110.0, 1),    # 1  high
        (4, 104.0, -1),   # 2  low  (higher low)
        (6, 120.0, 1),    # 3  high (higher high)
        (8, 112.0, -1),   # 4  low  (higher low)
        (10, 130.0, 1),   # 5  high (higher high)
    ]
    close = [100.0] * 13 + [128.0] * 7  # tras el punto 5 no cierra bajo X -> no invalidado
    ph, pl, cl = _pivots(points, length, 20, close)

    res = detect_ipda_expansions(ph, pl, cl, length, mode="impulse", direction=0)
    assert len(res) == 1
    row = res.iloc[0]
    assert row["pattern"] == "impulse"
    assert row["direction"] == 1
    assert row["n_points"] == 6
    assert row["p0_price"] == 100.0 and row["p5_price"] == 130.0
    assert row["rule2_ok"] and row["rule3_ok"] and row["rule4_ok"]
    assert row["compliance"] == pytest.approx(1.0)
    assert not row["invalidated"]
    assert row["invalidation_level"] == 100.0


def test_bearish_correction_xabc_detected():
    length = 2
    points = [
        (0, 200.0, 1),    # X  high
        (2, 180.0, -1),   # A  low
        (4, 190.0, 1),    # B  high (retroceso, < X y > A)
        (6, 170.0, -1),   # C  low  (< A)
    ]
    close = [200.0] * 9 + [172.0] * 7  # no cierra por encima de X -> no invalidado
    ph, pl, cl = _pivots(points, length, 16, close)

    res = detect_ipda_expansions(ph, pl, cl, length, mode="correction", direction=-1)
    assert len(res) == 1
    row = res.iloc[0]
    assert row["pattern"] == "correction"
    assert row["direction"] == -1
    assert row["n_points"] == 4
    assert row["p0_price"] == 200.0 and row["p3_price"] == 170.0
    assert np.isnan(row["p4_price"]) and np.isnan(row["p5_price"])
    assert not row["invalidated"]


def test_structural_reject_no_higher_high():
    """Un impulso donde la onda 3 NO hace máximo mayor no debe emitirse."""
    length = 2
    points = [
        (0, 100.0, -1),
        (2, 110.0, 1),
        (4, 104.0, -1),
        (6, 108.0, 1),    # 3 < 1  -> rompe estructura alcista
        (8, 105.0, -1),
        (10, 112.0, 1),
    ]
    ph, pl, cl = _pivots(points, length, 20, [100.0] * 20)
    res = detect_ipda_expansions(ph, pl, cl, length, mode="impulse", direction=1)
    assert res.empty


def test_bullish_impulse_invalidated_when_price_breaks_x():
    length = 2
    points = [
        (0, 100.0, -1), (2, 110.0, 1), (4, 104.0, -1),
        (6, 120.0, 1), (8, 112.0, -1), (10, 130.0, 1),
    ]
    close = [110.0] * 15 + [95.0] * 5  # cierra bajo X=100 tras el punto 5
    ph, pl, cl = _pivots(points, length, 20, close)
    res = detect_ipda_expansions(ph, pl, cl, length, mode="impulse", direction=1)
    assert len(res) == 1
    assert bool(res.iloc[0]["invalidated"])


def test_empty_when_no_pivots():
    length = 2
    ph = pd.Series([np.nan] * 20, dtype=float)
    pl = pd.Series([np.nan] * 20, dtype=float)
    cl = pd.Series([100.0] * 20, dtype=float)
    res = detect_ipda_expansions(ph, pl, cl, length, mode="both", direction=0)
    assert res.empty
    # el esquema de columnas se mantiene aunque esté vacío
    assert "compliance" in res.columns and "p5_price" in res.columns


def test_compliance_below_one_when_wave3_shortest():
    """Estructura válida pero onda 3 la más corta -> se emite con compliance < 1."""
    length = 2
    points = [
        (0, 100.0, -1),
        (2, 130.0, 1),    # onda 1 larga (30)
        (4, 120.0, -1),
        (6, 132.0, 1),    # onda 3 corta (12)  <- la más corta
        (8, 125.0, -1),
        (10, 160.0, 1),   # onda 5 larga (35)
    ]
    ph, pl, cl = _pivots(points, length, 20, [100.0] * 20)
    res = detect_ipda_expansions(ph, pl, cl, length, mode="impulse", direction=1)
    assert len(res) == 1
    row = res.iloc[0]
    assert not row["rule3_ok"]          # la 3 es la más corta
    assert row["compliance"] < 1.0      # pero sigue siendo una expansión estructural



def test():
    test_bullish_impulse_x12345_detected_full_compliance()
    test_bearish_correction_xabc_detected()
    test_structural_reject_no_higher_high()
    test_bullish_impulse_invalidated_when_price_breaks_x()
    test_empty_when_no_pivots()
    test_compliance_below_one_when_wave3_shortest()


import os, sys

if __name__ == "__main__":
    project_root = r"D:\Work\DeepVision\nexora-trading-framework"
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    CSV_PATH = os.path.join(project_root, 'backtests_data/BTCUSDT/1d.csv')

    df = pd.read_csv(CSV_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)

    fractals_df = df.smc.ipda_fractal()
    fractals_df

    print(df)
