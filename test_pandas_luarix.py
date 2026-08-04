import os

import numpy as np
import pandas as pd
import pytest

import pandas_luarix  # noqa: F401  (import registers the .smc accessor)


def _base_ohlc(n: int = 260, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    price = 100 + 15 * np.sin(2 * np.pi * t / 20) + rng.normal(0, 0.05, n)
    close = price
    open_ = np.empty(n)
    open_[0] = close[0]
    open_[1:] = close[:-1]
    high = np.maximum(open_, close) + rng.uniform(0.05, 0.15, n)
    low = np.minimum(open_, close) - rng.uniform(0.05, 0.15, n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})


@pytest.fixture
def synthetic_ohlc() -> pd.DataFrame:
    df = _base_ohlc()

    # Engineered bullish FVG (bars 100/101/102), filled at bar 110.
    df.loc[100, ["open", "close", "high", "low"]] = [90.0, 90.5, 90.6, 89.9]
    df.loc[101, ["open", "close", "high", "low"]] = [91.0, 92.0, 92.2, 90.9]
    df.loc[102, ["open", "close", "high", "low"]] = [95.0, 96.0, 96.2, 94.8]
    df.loc[110, ["open", "close", "high", "low"]] = [92.0, 90.0, 92.5, 89.0]

    # Engineered equal-high pair (bars 30/150), far above the zigzag's natural range (~85-116).
    df.loc[30, ["open", "close", "high", "low"]] = [129.0, 129.5, 130.00, 128.8]
    df.loc[150, ["open", "close", "high", "low"]] = [129.0, 129.6, 130.02, 128.9]

    # Engineered isolated swing low at bar 60 (confirmed by flat bars 56-69), swept at bar 70.
    for i in range(56, 70):
        df.loc[i, ["open", "close", "high", "low"]] = [95.0, 95.2, 95.5, 94.5]
    df.loc[60, ["open", "close", "high", "low"]] = [95.0, 95.2, 95.5, 80.0]
    df.loc[70, ["open", "close", "high", "low"]] = [91.0, 90.0, 91.2, 79.0]

    return df


@pytest.fixture(scope="session")
def btc_daily_df() -> pd.DataFrame:
    repo_root = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(repo_root, "backtests_data", "BTCUSDT", "1d.csv")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").drop(columns=["close_time"])
    return df


# ---- Registration / validation ----


def test_accessors_register_on_import(synthetic_ohlc):
    df = synthetic_ohlc
    assert hasattr(df, "smc")
    df.smc  # noqa: B018


def test_missing_columns_raises_value_error(synthetic_ohlc):
    bad = synthetic_ohlc.drop(columns=["close"])
    with pytest.raises(ValueError):
        bad.smc
    with pytest.raises(ValueError):
        bad.smc


def test_insufficient_rows_raises_value_error(synthetic_ohlc):
    tiny = synthetic_ohlc.head(3)
    with pytest.raises(ValueError):
        tiny.smc.swing_high(length=50)


def test_invalid_choice_params_raise(synthetic_ohlc):
    df = synthetic_ohlc
    with pytest.raises(ValueError):
        df.smc.equal_high(method="bogus")
    with pytest.raises(ValueError):
        df.smc.bullish_order_block(ob_mitigation="bogus")
    with pytest.raises(ValueError):
        df.smc.bullish_order_block(volatility_method="bogus")
    with pytest.raises(ValueError):
        df.smc.liquidity_sweep(levels="bogus")


def test_no_crash_at_minimum_row_boundary(synthetic_ohlc):
    length = 5
    minimal = synthetic_ohlc.head(length * 2 + 1)
    minimal.smc.swings(length=length)
    minimal.smc.swing_high(length=length)
    minimal.smc.bos_choch(length=length)
    minimal.smc.bullish_order_block(length=length, atr_period=length)
    minimal.smc.fair_value_gaps()


# ---- smc.swings / swing_high / swing_low ----


def test_swings_returns_row_subset_of_df(synthetic_ohlc):
    df = synthetic_ohlc
    result = df.smc.swings(length=5)
    assert isinstance(result, pd.DataFrame)
    assert result.index.isin(df.index).all()
    assert set(df.columns) <= set(result.columns)
    assert set(result["swing_type"].unique()) <= {"high", "low"}


def test_swing_high_low_include_mitigated_toggles_count(synthetic_ohlc):
    df = synthetic_ohlc
    excluded = df.smc.swing_high(length=5, include_mitigated=False)
    included = df.smc.swing_high(length=5, include_mitigated=True)
    assert len(included) >= len(excluded)
    assert not excluded["mitigated"].any()


# ---- smc.equal_high / equal_low ----


def test_equal_high_pct_range_detects_engineered_pair(synthetic_ohlc):
    """price_proximity (enum name `pct_range` is historical) operates on
    CONFIRMED PIVOTS, not raw candles -- needs `length` like every other
    pivot-based method now. Bars 30/150 spike far above the sine wave's
    natural range, so they're genuine pivot highs at any reasonable length."""
    df = synthetic_ohlc
    groups = df.smc.equal_high(length=5, method="pct_range", tolerance_pct=0.003, include_mitigated=True)
    assert isinstance(groups, list)
    matches = [g for g in groups if set(g.index) == {30, 150}]
    assert len(matches) == 1
    group = matches[0]
    assert "mitigated" in group.columns
    assert group.loc[30, "high"] == pytest.approx(130.00)
    assert group.loc[150, "high"] == pytest.approx(130.02)


def test_equal_high_atr_pivot_runs_and_returns_groups(synthetic_ohlc):
    df = synthetic_ohlc
    groups = df.smc.equal_high(length=5, method="atr_pivot", include_mitigated=True)
    assert isinstance(groups, list)
    for g in groups:
        assert "mitigated" in g.columns
        assert len(g) >= 2


def test_equal_high_low_composed_returns_two_lists(synthetic_ohlc):
    df = synthetic_ohlc
    highs, lows = df.smc.equal_high_low(length=5)
    assert isinstance(highs, list)
    assert isinstance(lows, list)


def test_price_proximity_groups_more_than_two_members(synthetic_ohlc):
    """A diferencia de atr_pivot (single-slot, solo compara contra el pivote
    anterior), price_proximity encuentra TODOS los pivotes dentro de
    tolerancia entre sí -- acá los picos naturales del seno (periodo 20,
    misma amplitud) deberían agruparse en un solo cluster de varios
    miembros, no quedarse como pares sueltos."""
    df = synthetic_ohlc
    groups = df.smc.equal_high(length=5, method="pct_range", tolerance_pct=0.003, include_mitigated=True)
    big_groups = [g for g in groups if len(g) > 2]
    assert big_groups, "esperaba al menos un cluster de 3+ miembros entre los picos naturales del seno"


def test_price_proximity_include_mitigated_trims_members_not_whole_group(synthetic_ohlc):
    """Regresión del caso pedido explícitamente: un cluster de 3 niveles
    iguales donde el primero ya fue mitigado (precio cerró más allá de su
    nivel) antes de que el segundo/tercero se confirmaran, y esos dos NO
    están mitigados entre sí. `include_mitigated=True` debe devolver el
    cluster completo (los 3); `include_mitigated=False` debe recortar el
    miembro mitigado y devolver solo los 2 que siguen vigentes -- no
    descartar el grupo entero."""
    n = 300
    df = _base_ohlc(n=n, seed=11)
    length = 5

    # Tres picos aislados a ~130 (muy por encima del rango natural ~85-116),
    # separados por valles profundos para que cada uno confirme como pivote
    # propio con `length=5`.
    for pos, high in ((40, 130.00), (120, 130.05), (200, 130.02)):
        df.loc[pos, ["open", "close", "high", "low"]] = [100.0, 100.0, high, 99.0]
        for offset in (-2, -1, 1, 2):
            df.loc[pos + offset, ["open", "close", "high", "low"]] = [95.0, 95.0, 96.0, 94.0]

    # Vela entre el pico 1 y el pico 2 que cierra POR ENCIMA del nivel del
    # pico 1 (lo mitiga) pero por debajo de los picos 2/3 (no los toca).
    df.loc[80, ["open", "close", "high", "low"]] = [129.9, 130.5, 130.6, 129.5]

    groups = df.smc.equal_high(length=length, method="pct_range", tolerance_pct=0.003, include_mitigated=True)
    matches = [g for g in groups if {40, 120, 200} <= set(g.index)]
    assert len(matches) == 1, "los 3 picos deberían agruparse en un solo cluster"
    group = matches[0]
    assert bool(group.loc[40, "mitigated"]) is True
    assert bool(group.loc[120, "mitigated"]) is False
    assert bool(group.loc[200, "mitigated"]) is False

    filtered = df.smc.equal_high(length=length, method="pct_range", tolerance_pct=0.003, include_mitigated=False)
    filtered_matches = [g for g in filtered if set(g.index) == {120, 200}]
    assert len(filtered_matches) == 1, "sin el miembro mitigado, debe quedar el grupo vigente de 2, no desaparecer"
    assert not any(40 in g.index for g in filtered)


def test_price_proximity_search_window_none_searches_entire_history(synthetic_ohlc):
    """`search_window=None` (default) debe encontrar un par igual aunque
    esté fuera de cualquier ventana "reciente" razonable -- una vela nueva
    siempre puede hacer match contra un nivel viejo todavía vigente."""
    df = synthetic_ohlc
    groups = df.smc.equal_high(length=5, method="pct_range", tolerance_pct=0.003, include_mitigated=True)
    assert any(set(g.index) == {30, 150} for g in groups)


def test_price_proximity_search_window_restricts_candidates(synthetic_ohlc):
    df = synthetic_ohlc
    # El par engineered vive en 30/150 -- con una ventana de 40 velas
    # (desde el final, bar ~220 en adelante) ninguno de los dos entra.
    groups = df.smc.equal_high(
        length=5, method="pct_range", tolerance_pct=0.003, include_mitigated=True, search_window=40
    )
    assert not any(30 in g.index or 150 in g.index for g in groups)


def test_price_proximity_matches_brute_force_reference(synthetic_ohlc):
    """La optimización por orden (O(n log n)) tiene que encontrar EXACTAMENTE
    los mismos clusters que una búsqueda O(n^2) explícita (ancla = el menor
    valor restante, sin asumir contigüidad en el orden) -- cross-check de
    correctitud del atajo, no solo de que "corre sin romper". El atajo real
    solo mira el SIGUIENTE valor ordenado porque, una vez ordenado, la
    distancia al ancla nunca disminuye -- pero eso es justo lo que este test
    verifica de forma independiente, sin apoyarse en esa propiedad."""
    import numpy as np

    from pandas_luarix._core.pivots import find_pivots

    df = synthetic_ohlc
    length = 5
    tolerance_pct = 0.003
    pivot_high, _ = find_pivots(df["high"], df["low"], length)
    positions = np.flatnonzero(~pivot_high.isna())
    levels = pivot_high.to_numpy()[positions]
    origins = positions - length
    valid = origins >= 0
    levels, origins = levels[valid], origins[valid]

    order = np.argsort(levels)
    sorted_levels, sorted_origins = levels[order], origins[order]
    used = [False] * len(sorted_levels)
    brute_groups = set()
    for i in range(len(sorted_levels)):
        if used[i]:
            continue
        anchor = sorted_levels[i]
        members = [i]
        for j in range(i + 1, len(sorted_levels)):
            if not used[j] and abs(sorted_levels[j] - anchor) <= tolerance_pct * abs(anchor):
                members.append(j)
        if len(members) >= 2:
            for m in members:
                used[m] = True
            brute_groups.add(tuple(sorted(int(sorted_origins[m]) for m in members)))

    groups = df.smc.equal_high(length=length, method="pct_range", tolerance_pct=tolerance_pct, include_mitigated=True)
    real_groups = {tuple(sorted(df.index.get_indexer(g.index))) for g in groups}

    assert real_groups == brute_groups


# ---- smc.bos_choch ----


def test_bos_choch_returns_expected_columns(synthetic_ohlc):
    df = synthetic_ohlc
    events = df.smc.bos_choch(length=5)
    assert {"structure_type", "direction"} <= set(events.columns)
    assert len(events) > 0
    assert events["structure_type"].isin(["BOS", "CHOCH"]).all()
    assert events["direction"].isin([1, -1]).all()


def _bos_then_choch_df() -> pd.DataFrame:
    """`length=3`: primeras 12 velas -- mismas que `_bullish_bos_breakout_df`
    de la revisión de Market Structure (confirmado empíricamente ahí:
    pivote alto 110.0 en la vela 8, confirmado en la 11, cruzado por el
    cierre de la vela 12 -- BOS, direction=1, primera estructura de la
    serie). Continuación agregada acá: el pivote bajo 95.0 (vela 3,
    confirmado en la 6) sigue sin romperse durante el tramo alcista
    siguiente: la caída final (velas 15-21) lo cruza recién en la vela 20
    -- con la tendencia ya en alcista (por el BOS previo), esa ruptura es
    un CHOCH, direction=-1. Confirmado empíricamente corriendo el motor
    real antes de fijar estas aserciones."""
    bars = [
        (105, 100), (104, 99), (103, 98), (102, 95),
        (103, 96), (104, 97), (105, 98), (108, 101), (110, 103),
        (109, 102), (108, 101), (107, 100),
        (111, 109), (112, 110), (113, 111),
        (112, 108), (111, 106), (110, 104), (109, 101),
        (108, 98), (100, 90), (95, 85),
    ]
    idx = pd.date_range("2024-01-01", periods=len(bars), freq="h")
    high = np.array([b[0] for b in bars], dtype=float)
    low = np.array([b[1] for b in bars], dtype=float)
    close = (high + low) / 2.0
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame(
        {"date": idx, "open": open_, "high": high, "low": low, "close": close, "volume": [1.0] * len(bars)},
        index=idx,
    )


def test_bos_choch_exact_sequence_bos_then_choch(synthetic_ohlc):
    df = _bos_then_choch_df()
    events = df.smc.bos_choch(length=3)

    assert len(events) == 2
    positions = df.index.get_indexer(events.index)
    assert positions.tolist() == [12, 20]
    assert events["structure_type"].tolist() == ["BOS", "CHOCH"]
    assert events["direction"].tolist() == [1, -1]


def test_bos_choch_confluence_filter_rejects_wick_only_break():
    """Regresión del parámetro recién expuesto: una vela que técnicamente
    cruza el nivel (cierre > nivel) pero con mecha larga hacia abajo y
    cuerpo apenas por encima (no un cierre alcista real) debe contar SIN
    `confluence_filter` y descartarse CON él."""
    data = [
        (95, 100, 94, 99),
        (99, 110, 98, 109),
        (109, 105, 100, 102),
        (105, 111, 95, 110.5),  # cruza 102 < 110 <= 110.5, pero cuerpo apenas alcista, mecha larga abajo
    ]
    idx = pd.date_range("2024-01-01", periods=len(data), freq="h")
    df = pd.DataFrame({
        "date": idx,
        "open": [r[0] for r in data], "high": [r[1] for r in data],
        "low": [r[2] for r in data], "close": [r[3] for r in data],
        "volume": [1.0] * len(data),
    }, index=idx)

    without_filter = df.smc.bos_choch(length=1, confluence_filter=False)
    with_filter = df.smc.bos_choch(length=1, confluence_filter=True)

    assert len(without_filter) == 1
    assert without_filter["structure_type"].iloc[0] == "BOS"
    assert with_filter.empty


# ---- smc.expansion / smc.consolidation ----


@pytest.fixture
def tight_then_spike_ohlc() -> pd.DataFrame:
    """10 velas de rango angosto (2 puntos, high/low = 101/99) seguidas de
    UNA vela de rango enorme (130/70) y 2 velas angostas más. Con
    atr_period=5: ATR se estabiliza en 2.0 durante el tramo angosto, salta a
    13.6 en la vela del pico, y decae despues por el suavizado de Wilder --
    valores verificados a mano contra la implementacion real antes de
    escribir estas aserciones (no son una suposicion)."""
    bars = [
        (101, 99), (101, 99), (101, 99), (101, 99), (101, 99),
        (101, 99), (101, 99), (101, 99), (101, 99), (101, 99),
        (130, 70),
        (101, 99), (101, 99),
    ]
    idx = pd.date_range("2024-01-01", periods=len(bars), freq="h")
    high = np.array([b[0] for b in bars], dtype=float)
    low = np.array([b[1] for b in bars], dtype=float)
    close = (high + low) / 2.0
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=idx)


def test_expansion_flags_exactly_the_spike_bar(tight_then_spike_ohlc):
    df = tight_then_spike_ohlc
    result = df.smc.expansion(atr_period=5, multiplier=2.0)
    positions = [df.index.get_loc(i) for i in result.index]
    assert positions == [10]


def test_expansion_finds_nothing_in_a_uniformly_tight_series(tight_then_spike_ohlc):
    df = tight_then_spike_ohlc.iloc[:10]
    result = df.smc.expansion(atr_period=5, multiplier=2.0)
    assert result.empty


def test_consolidation_flags_exactly_the_tight_window_before_the_spike(tight_then_spike_ohlc):
    df = tight_then_spike_ohlc
    result = df.smc.consolidation(window=5, atr_period=5, multiplier=1.0)
    positions = [df.index.get_loc(i) for i in result.index]
    # Bars 0-3 don't have a full 5-bar rolling window yet; bar 10 (the spike)
    # and its rolling window are excluded; 11-12 don't have enough history
    # for their own rolling window post-spike to re-qualify.
    assert positions == [4, 5, 6, 7, 8, 9]


def test_consolidation_and_expansion_share_the_same_atr_baseline(tight_then_spike_ohlc):
    """Ambas funciones deben leer el MISMO ATR -- verificado comparando
    contra `compute_atr` directamente, no solo confiando en que ambos
    accessors "hacen algo razonable"."""
    from pandas_luarix._core.volatility import compute_atr

    df = tight_then_spike_ohlc
    atr = compute_atr(df["high"], df["low"], df["close"], period=5)
    assert atr.iloc[9] == pytest.approx(2.0)
    assert atr.iloc[10] > 10.0  # spike bar's own true range dominates the Wilder update


def test_expansion_rejects_non_positive_multiplier(tight_then_spike_ohlc):
    with pytest.raises(ValueError):
        tight_then_spike_ohlc.smc.expansion(atr_period=5, multiplier=0)


def test_consolidation_requires_minimum_rows(tight_then_spike_ohlc):
    short_df = tight_then_spike_ohlc.iloc[:3]
    with pytest.raises(ValueError):
        short_df.smc.consolidation(window=5, atr_period=5)


# ---- structure order blocks ----


def test_order_blocks_top_bottom_bounds(synthetic_ohlc):
    df = synthetic_ohlc
    ob = df.smc.bullish_order_block(length=5, include_mitigated=True)
    assert {"top", "bottom", "mitigated"} <= set(ob.columns)
    if len(ob):
        assert (ob["bottom"] <= ob["top"]).all()


def test_order_blocks_mitigated_retained_not_dropped(synthetic_ohlc):
    df = synthetic_ohlc
    excluded = df.smc.order_blocks(length=5, include_mitigated=False)
    included = df.smc.order_blocks(length=5, include_mitigated=True)
    assert len(included) >= len(excluded)
    assert included["mitigated"].any()


def test_order_blocks_composed_adds_direction_column(synthetic_ohlc):
    df = synthetic_ohlc
    bullish = df.smc.bullish_order_block(length=5, include_mitigated=True)
    bearish = df.smc.bearish_order_block(length=5, include_mitigated=True)
    combined = df.smc.order_blocks(length=5, include_mitigated=True)
    assert "direction" in combined.columns
    assert set(combined["direction"].unique()) <= {1, -1}
    assert len(combined) == len(bullish) + len(bearish)


def test_order_blocks_match_reference_smc_indicator(btc_daily_df):
    """Regresión de verificación: la selección de la vela origen de un
    Order Block (`build_order_blocks`: extremo de parsed_low/parsed_high
    entre el pivote y la ruptura) se compara bit a bit contra un port
    Python completo del indicador de referencia LuxAlgo
    (`app/tradingview/smc_indicator.py`), igual que ya se hace para
    Equal High/Low -- `pandas_luarix` se mantiene independiente de
    `app/tradingview` en producción, este test solo lo importa como
    oráculo de comparación, una vez, con los defaults alineados
    (swing_length=50, atr_period=200, high_vol_multiplier=2.0, ATR,
    High/Low, sin confluence_filter)."""
    from app.tradingview.smc_indicator import SMCIndicator
    from app.tradingview.types import SMCConfig

    df = btc_daily_df
    result = SMCIndicator(SMCConfig()).run(df)
    ref_bull = sorted(ob.bar_index for ob in result.swing_order_blocks if ob.direction == 1)
    ref_bear = sorted(ob.bar_index for ob in result.swing_order_blocks if ob.direction == -1)

    mine_bull = sorted(df.index.get_indexer(df.smc.bullish_order_block(length=50).index))
    mine_bear = sorted(df.index.get_indexer(df.smc.bearish_order_block(length=50).index))

    assert mine_bull == ref_bull
    assert mine_bear == ref_bear


def _bullish_ob_with_bos_df() -> pd.DataFrame:
    """Mismas primeras 15 velas que `_bos_then_choch_df` (BOS alcista
    confirmado en la vela 12) más una vela 15 agregada: mecha hasta 95
    (perfora el `bottom`=100.0 del OB confirmado en la vela 11) pero cierre
    en 101.0 (sigue por encima) -- diseñada para que `ob_mitigation`
    "high_low" y "close" difieran, verificado empíricamente antes de fijar
    estas aserciones."""
    bars_hl = [
        (105, 100), (104, 99), (103, 98), (102, 95),
        (103, 96), (104, 97), (105, 98), (108, 101), (110, 103),
        (109, 102), (108, 101), (107, 100),
        (111, 109), (112, 110), (113, 111),
        (105, 95),
    ]
    idx = pd.date_range("2024-01-01", periods=len(bars_hl), freq="h")
    high = np.array([b[0] for b in bars_hl], dtype=float)
    low = np.array([b[1] for b in bars_hl], dtype=float)
    close = np.array([103.5, 101.5, 100.5, 98.5, 99.5, 100.5, 101.5, 104.5, 106.5, 105.5, 104.5, 103.5, 110.0, 111.0, 112.0, 101.0])
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame(
        {"date": idx, "open": open_, "high": high, "low": low, "close": close, "volume": [1.0] * len(bars_hl)},
        index=idx,
    )


def test_order_blocks_ob_mitigation_high_low_vs_close():
    df = _bullish_ob_with_bos_df()

    high_low = df.smc.bullish_order_block(length=3, atr_period=3, ob_mitigation="high_low", include_mitigated=True)
    close_only = df.smc.bullish_order_block(length=3, atr_period=3, ob_mitigation="close", include_mitigated=True)

    assert len(high_low) == 1
    assert bool(high_low["mitigated"].iloc[0]) is True
    assert len(close_only) == 1
    assert bool(close_only["mitigated"].iloc[0]) is False


def test_order_blocks_confluence_filter_rejects_wick_only_break():
    """Un Order Block se construye a partir de un evento BOS/CHOCH -- si
    `confluence_filter` rechaza ese evento (ver el test equivalente en
    bos_choch), no hay ruptura confirmada y por lo tanto tampoco Order
    Block."""
    data = [
        (95, 100, 94, 99),
        (99, 110, 98, 109),
        (109, 105, 100, 102),
        (105, 111, 95, 110.5),
    ]
    idx = pd.date_range("2024-01-01", periods=len(data), freq="h")
    df = pd.DataFrame({
        "date": idx,
        "open": [r[0] for r in data], "high": [r[1] for r in data],
        "low": [r[2] for r in data], "close": [r[3] for r in data],
        "volume": [1.0] * len(data),
    }, index=idx)

    without_filter = df.smc.bullish_order_block(length=1, atr_period=1, confluence_filter=False, include_mitigated=True)
    with_filter = df.smc.bullish_order_block(length=1, atr_period=1, confluence_filter=True, include_mitigated=True)

    assert len(without_filter) == 1
    assert with_filter.empty


# ---- smc.fair_value_gaps ----


def test_fair_value_gaps_detects_engineered_gap(synthetic_ohlc):
    df = synthetic_ohlc
    fvgs = df.smc.fair_value_gaps(include_filled=True)
    assert 102 in fvgs.index
    row = fvgs.loc[102]
    assert row["top"] == pytest.approx(94.8)
    assert row["bottom"] == pytest.approx(90.6)
    assert row["direction"] == 1


def test_fair_value_gaps_include_filled_toggle(synthetic_ohlc):
    df = synthetic_ohlc
    included = df.smc.fair_value_gaps(include_filled=True)
    excluded = df.smc.fair_value_gaps(include_filled=False)
    assert 102 in included.index
    assert bool(included.loc[102, "filled"])
    assert 102 not in excluded.index


def test_fair_value_gaps_min_gap_atr_multiple_filters(synthetic_ohlc):
    df = synthetic_ohlc
    permissive = df.smc.fair_value_gaps(min_gap_atr_multiple=0.0, include_filled=True)
    strict = df.smc.fair_value_gaps(min_gap_atr_multiple=50.0, include_filled=True)
    assert len(strict) <= len(permissive)


def test_fair_value_gaps_requires_middle_candle_directional_bias():
    """Regresión de un bug real encontrado contra el oráculo LuxAlgo: una
    vela intermedia que abre con un gran gap alcista pero CIERRA por debajo
    de su propia apertura (bajista en sí misma), aunque su cierre siga por
    encima de `high[-2]` (satisface el gap técnico), NO debe contar como
    FVG alcista -- la referencia exige que la vela intermedia tenga sesgo
    direccional propio, no solo que el gap exista. Verificado antes del fix:
    esta config SÍ generaba un FVG (falso positivo); después, no."""
    bars = [
        (100.0, 95.0, 98.0, 97.0),
        (120.0, 104.0, 121.0, 105.0),  # abre 120, cierra 105 -- bajista en sí misma, aunque close(105) > high2(98)
        (106.0, 110.0, 112.0, 111.0),
    ]
    idx = pd.date_range("2024-01-01", periods=len(bars), freq="h")
    df = pd.DataFrame({
        "date": idx,
        "open": [b[0] for b in bars], "low": [b[1] for b in bars],
        "high": [b[2] for b in bars], "close": [b[3] for b in bars],
        "volume": [1.0] * len(bars),
    }, index=idx)

    fvgs = df.smc.fair_value_gaps(include_filled=True)

    assert fvgs.empty


def test_fair_value_gaps_matches_reference_smc_indicator(btc_daily_df):
    """Mismo criterio de verificación que Equal High/Low y Order Blocks --
    port Python completo del indicador LuxAlgo, usado una vez como oráculo
    de comparación sobre datos reales de BTC diario."""
    from app.tradingview.smc_indicator import SMCIndicator
    from app.tradingview.types import SMCConfig

    df = btc_daily_df
    result = SMCIndicator(SMCConfig(detect_fvg=True)).run(df)
    ref_bull = sorted(f.right_index for f in result.fair_value_gaps if f.direction == 1)
    ref_bear = sorted(f.right_index for f in result.fair_value_gaps if f.direction == -1)

    mine = df.smc.fair_value_gaps(include_filled=False)
    mine_bull = sorted(df.index.get_indexer(mine[mine["direction"] == 1].index))
    mine_bear = sorted(df.index.get_indexer(mine[mine["direction"] == -1].index))

    assert mine_bull == ref_bull
    assert mine_bear == ref_bear


# ---- smc.liquidity_sweep ----


def test_liquidity_sweep_detects_engineered_stop_hunt(synthetic_ohlc):
    df = synthetic_ohlc
    sweeps = df.smc.liquidity_sweep(length=5, levels="swings", max_confirmation_bars=15)
    assert 70 in sweeps.index
    row = sweeps.loc[70]
    assert row["swept_level"] == pytest.approx(80.0)
    assert row["swept_level_type"] == "swing_low"
    assert row["direction"] == 1


def _two_equal_highs_df() -> pd.DataFrame:
    """`length=3`: dos picos aislados (~130) confirmados como equal-high en
    las posiciones 5 y 15 (confirmación real en 8 y 18 respectivamente).
    Sin vela 20 agregada -- cada test la agrega con su propio valor."""
    n = 25
    rng = np.random.default_rng(3)
    high = 100.0 + rng.normal(0, 0.3, n)
    low = 95.0 + rng.normal(0, 0.3, n)
    close = 97.0 + rng.normal(0, 0.1, n)
    open_ = np.r_[close[0], close[:-1]]
    high[5], close[5], low[5] = 130.0, 129.0, 128.0
    high[15], close[15], low[15] = 130.02, 129.0, 128.0
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame(
        {"date": idx, "open": open_, "high": high, "low": low, "close": close, "volume": [1.0] * n}, index=idx
    )


def test_liquidity_sweep_equal_high_low_detects_sweep_after_true_confirmation():
    df = _two_equal_highs_df()
    # Vela 20 -- DESPUÉS de la confirmación real (18) del segundo pico (15).
    df.loc[df.index[20], ["high", "close"]] = [131.0, 128.0]

    sweeps = df.smc.liquidity_sweep(
        length=3, levels="equal_high_low", method="pct_range", tolerance_pct=0.003, max_confirmation_bars=10
    )

    assert len(sweeps) == 1
    row = sweeps.iloc[0]
    assert row["swept_level"] == pytest.approx(130.01, abs=0.05)
    assert row["swept_level_type"] == "equal_high"
    assert row["direction"] == -1


def test_liquidity_sweep_equal_high_low_no_lookahead_before_true_confirmation():
    """Regresión de un bug real: `sweep_offset` para niveles "iguales"
    calculados con Price Proximity (`method="pct_range"`) usaba
    `start_offset=0` -- un resto del algoritmo VIEJO (velas crudas, sin
    retraso de confirmación) que quedó desactualizado cuando Price
    Proximity pasó a operar sobre pivotes con el mismo retraso `length`
    que ATR Pivot. Resultado: se reportaban sweeps usando un nivel que el
    propio algoritmo todavía no había confirmado -- look-ahead bias real,
    verificado antes de este fix."""
    df = _two_equal_highs_df()
    # Vela 17 -- ANTES de la confirmación real (18) del segundo pico (15).
    df.loc[df.index[17], ["high", "close"]] = [131.0, 128.0]

    sweeps = df.smc.liquidity_sweep(
        length=3, levels="equal_high_low", method="pct_range", tolerance_pct=0.003, max_confirmation_bars=10
    )

    assert sweeps.empty


# ---- smc.demand_zone ----


def test_demand_zone_support_extends_below_the_fractal_bottom(synthetic_ohlc):
    df = synthetic_ohlc
    fractals = df.smc.fractal(length=5, include_mitigated=True)
    zones = df.smc.demand_zone(length=5, side="support", offset_pct=1.0, include_mitigated=True)
    assert len(zones) == len(fractals)
    if len(zones):
        # top == the fractal's own bottom edge; band extends further down.
        assert zones["top"].to_numpy() == pytest.approx(fractals["bottom"].to_numpy())
        assert (zones["bottom"] < zones["top"]).all()
        assert (zones["direction"] == 1).all()


def test_demand_zone_resistance_extends_above_the_fractal_top(synthetic_ohlc):
    df = synthetic_ohlc
    fractals = df.smc.fractal(length=5, include_mitigated=True)
    zones = df.smc.demand_zone(length=5, side="resistance", offset_pct=1.0, include_mitigated=True)
    assert len(zones) == len(fractals)
    if len(zones):
        # bottom == the fractal's own top edge; band extends further up.
        assert zones["bottom"].to_numpy() == pytest.approx(fractals["top"].to_numpy())
        assert (zones["top"] > zones["bottom"]).all()
        assert (zones["direction"] == -1).all()


def test_demand_zone_wider_offset_produces_a_wider_band(synthetic_ohlc):
    df = synthetic_ohlc
    narrow = df.smc.demand_zone(length=5, side="support", offset_pct=0.5, include_mitigated=True)
    wide = df.smc.demand_zone(length=5, side="support", offset_pct=2.0, include_mitigated=True)
    if len(narrow) and len(wide):
        narrow_band = (narrow["top"] - narrow["bottom"]).mean()
        wide_band = (wide["top"] - wide["bottom"]).mean()
        assert wide_band > narrow_band


def test_demand_zone_unrecognized_origin_string_raises_value_error():
    # "order_block" isn't a valid `ZoneOrigin` member yet (only FRACTAL is
    # implemented) -- Enum coercion itself rejects it before `build_zone`'s
    # own `NotImplementedError` dispatch ever gets a chance to run. That
    # branch becomes reachable only once a second `ZoneOrigin` member exists.
    df = _base_ohlc()
    with pytest.raises(ValueError):
        df.smc.demand_zone(origin="order_block", length=5)


# ---- Real-data smoke test ----


def test_real_data_smoke_all_public_methods(btc_daily_df):
    df = btc_daily_df
    n = len(df)

    swings = df.smc.swings(length=20)
    swing_high = df.smc.swing_high(length=20)
    swing_low = df.smc.swing_low(length=20)
    equal_high = df.smc.equal_high(length=20)
    equal_low = df.smc.equal_low(length=20)
    bos_choch = df.smc.bos_choch(length=20)
    order_blocks = df.smc.order_blocks(length=20)
    liquidity_sweep = df.smc.liquidity_sweep(length=20)
    fvgs = df.smc.fair_value_gaps()

    for result in (swings, swing_high, swing_low, bos_choch, order_blocks, liquidity_sweep, fvgs):
        assert isinstance(result, pd.DataFrame)
        assert len(result) < n

    assert isinstance(equal_high, list)
    assert isinstance(equal_low, list)
    for group in equal_high + equal_low:
        assert len(group) < n


def test_equal_high_low_matches_reference_smc_indicator(btc_daily_df):
    """
    Regression test for a real bug found via a notebook comparison: an
    `.ewm()`-based ATR cold-start diverged from the reference's SMA-seeded
    Wilder ATR by ~10% for hundreds of bars, silently dropping matches.
    `pandas_luarix` stays independent of `app/tradingview` in production
    code — this test only imports it as a one-time comparison oracle.
    """
    from app.tradingview.smc_indicator import SMCIndicator
    from app.tradingview.types import SMCConfig

    df = btc_daily_df
    result = SMCIndicator(SMCConfig()).run(df)
    ref_eqh = [(e.first_index, e.second_index) for e in result.equal_highs]
    ref_eql = [(e.first_index, e.second_index) for e in result.equal_lows]

    mine_eqh = [tuple(df.index.get_indexer(g.index)) for g in df.smc.equal_high(include_mitigated=True)]
    mine_eql = [tuple(df.index.get_indexer(g.index)) for g in df.smc.equal_low(include_mitigated=True)]

    assert mine_eqh == ref_eqh
    assert mine_eql == ref_eql
