"""Contratos de la superficie pública: validación de parámetros, forma del
resultado vacío y agnosticismo del índice.

Cada test de este módulo es la regresión de un bug REAL encontrado en la
revisión de cierre del proyecto (ver `docs/plans/bugs.md`, sección "Revisión
de cierre"), no una comprobación defensiva especulativa. La segunda mitad
del archivo consume `tests/builders.py` — fixtures con resultados calculados
a mano — para fijar los números exactos de un doble techo y de un stop hunt.
"""

import numpy as np
import pandas as pd
import pytest

import pandas_luarix  # noqa: F401  (el import registra los accessors)
from tests.builders import ATR_PERIOD, LENGTH, double_top, stop_hunt


def _sine_ohlc(n: int = 300, seed: int = 7, *, datetime_index: bool = True) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    close = 100 + 15 * np.sin(2 * np.pi * t / 20) + rng.normal(0, 0.5, n)
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) + rng.uniform(0.05, 0.8, n)
    low = np.minimum(open_, close) - rng.uniform(0.05, 0.8, n)
    index = pd.date_range("2024-01-01", periods=n, freq="h") if datetime_index else pd.RangeIndex(n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=index)


@pytest.fixture
def sine_ohlc() -> pd.DataFrame:
    return _sine_ohlc()


# ---- El índice del df no tiene por qué ser de fechas ----


def test_ipda_fractal_works_on_a_non_datetime_index():
    """`_attach_point_times` fijaba `dtype="datetime64[ns]"` para la columna
    de tiempos de cada punto, así que cualquier df con índice entero
    (RangeIndex — perfectamente válido para el resto de la librería)
    reventaba con `TypeError: Invalid value ... for dtype datetime64[ns]`.
    Ningún otro método tenía esta restricción."""
    df = _sine_ohlc(400, datetime_index=False)
    result = df.smc.ipda_fractal(length=10, mode="both")

    assert not result.empty
    # p0 siempre existe (es X); su "tiempo" es la etiqueta de índice del df,
    # que acá es un entero, no un Timestamp.
    assert (result["p0_time"] == result["p0_pos"]).all()


def test_ipda_fractal_point_times_match_the_index_on_a_datetime_index(sine_ohlc):
    result = sine_ohlc.smc.ipda_fractal(length=10, mode="both")
    assert not result.empty
    expected = sine_ohlc.index[result["p0_pos"].astype(int).to_numpy()]
    assert list(result["p0_time"]) == list(expected)


# ---- Contrato del resultado vacío: filas del df + columnas nuevas ----


@pytest.mark.parametrize(
    "call",
    [
        lambda df: df.smc.swings(length=20),
        lambda df: df.smc.swing_high(length=20),
        lambda df: df.smc.swing_low(length=20),
        lambda df: df.smc.bos_choch(length=20),
        lambda df: df.smc.order_blocks(length=20, atr_period=50),
        lambda df: df.smc.fair_value_gaps(),
        lambda df: df.smc.fractal(length=5),
        lambda df: df.smc.demand_zone(length=5),
        lambda df: df.smc.ipda_fractal(length=20),
        lambda df: df.smc.liquidity_sweep(length=20),
    ],
)
def test_empty_results_keep_the_ohlc_columns(call):
    """Una serie perfectamente plana no dispara ningún detector. La salida
    vacía tiene que seguir siendo indexable como el df de entrada: `df.iloc[0:0]`
    MÁS las columnas nuevas. `liquidity_sweep` era el único que devolvía un df
    de 3 columnas sueltas sin OHLC, así que el código del llamador que leía
    `sweeps["close"]` solo se rompía cuando no había sweeps."""
    n = 200
    flat = pd.DataFrame(
        {"open": [100.0] * n, "high": [100.0] * n, "low": [100.0] * n, "close": [100.0] * n},
        index=pd.date_range("2024-01-01", periods=n, freq="h"),
    )
    result = call(flat)

    assert isinstance(result, pd.DataFrame)
    assert result.empty
    assert set(flat.columns) <= set(result.columns)


def test_liquidity_sweep_empty_declares_its_own_columns_too():
    n = 200
    flat = pd.DataFrame(
        {"open": [100.0] * n, "high": [100.0] * n, "low": [100.0] * n, "close": [100.0] * n},
        index=pd.date_range("2024-01-01", periods=n, freq="h"),
    )
    result = flat.smc.liquidity_sweep(length=20)
    assert {"swept_level", "swept_level_type", "direction"} <= set(result.columns)


# ---- Validación de parámetros categóricos ----


def test_demand_zone_rejects_an_unknown_side(sine_ohlc):
    """`side` era un str libre: TODO valor distinto de "support" caía en la
    rama `resistance` sin error, así que un typo devolvía zonas del lado
    contrario en silencio."""
    with pytest.raises(ValueError):
        sine_ohlc.smc.demand_zone(length=5, side="suport")
    with pytest.raises(ValueError):
        sine_ohlc.smc.demand_zone(length=5, side="long")


def test_demand_zone_rejects_a_non_positive_offset(sine_ohlc):
    """Un `offset_pct` negativo producía una banda invertida (bottom > top)."""
    with pytest.raises(ValueError):
        sine_ohlc.smc.demand_zone(length=5, offset_pct=-1.0)
    with pytest.raises(ValueError):
        sine_ohlc.smc.demand_zone(length=5, offset_pct=0)


def test_demand_zone_side_accepts_both_the_enum_and_its_string(sine_ohlc):
    from pandas_luarix import ZoneSide

    by_string = sine_ohlc.smc.demand_zone(length=5, side="resistance", include_mitigated=True)
    by_enum = sine_ohlc.smc.demand_zone(length=5, side=ZoneSide.RESISTANCE, include_mitigated=True)
    assert by_string["top"].to_numpy() == pytest.approx(by_enum["top"].to_numpy())
    assert (by_string["direction"] == -1).all()


def test_ema_rejects_a_missing_source_column(sine_ohlc):
    """Salía un `KeyError` crudo de pandas — el único parámetro inválido de
    la librería que no se reportaba como ValueError."""
    with pytest.raises(ValueError, match="source"):
        sine_ohlc.indicators.ema(length=10, source="typical")


# ---- Enteros de numpy ----


@pytest.mark.parametrize("length", [np.int64(20), np.int32(20), np.uint8(20)])
def test_numpy_integers_are_accepted_as_lengths(sine_ohlc, length):
    """`isinstance(np.int64(20), int)` es False, así que un `length` calculado
    con numpy (`.astype(int)`, un índice posicional, un valor leído de un
    array de config) era rechazado como "no es un int positivo" pese a serlo."""
    assert len(sine_ohlc.smc.swings(length=length)) > 0
    assert "rsi" in sine_ohlc.indicators.rsi(length=np.int64(14)).columns


@pytest.mark.parametrize("bad", [True, 0, -3, 2.5, "20", None])
def test_non_integer_lengths_are_still_rejected(sine_ohlc, bad):
    with pytest.raises(ValueError):
        sine_ohlc.smc.swings(length=bad)


# ---- Divergencia: la serie del indicador tiene que estar alineada ----


def test_divergence_rejects_a_shorter_indicator(sine_ohlc):
    """Los pivotes se detectan sobre las posiciones de la SERIE y luego se
    usan para indexar el DF: una serie desalineada devolvía filas reales del
    df pero de las barras equivocadas, sin lanzar nada."""
    rsi = sine_ohlc.indicators.rsi()["rsi"]
    with pytest.raises(ValueError, match="aligned"):
        sine_ohlc.analysis.divergence(rsi.iloc[:50], length=5)


def test_divergence_rejects_a_reindexed_indicator(sine_ohlc):
    rsi = sine_ohlc.indicators.rsi()["rsi"]
    with pytest.raises(ValueError, match="index"):
        sine_ohlc.analysis.divergence(rsi.reset_index(drop=True), length=5)


def test_divergence_rejects_a_non_series_indicator(sine_ohlc):
    rsi = sine_ohlc.indicators.rsi()["rsi"]
    with pytest.raises(ValueError):
        sine_ohlc.analysis.divergence(rsi.to_numpy(), length=5)


def test_divergence_empty_result_has_typed_columns(sine_ohlc):
    """El resultado vacío declaraba TODAS las columnas como `object`,
    incluida `direction` (int en el resultado no vacío)."""
    all_nan = pd.Series(np.nan, index=sine_ohlc.index)
    result = sine_ohlc.analysis.divergence(all_nan, length=5)
    assert result.empty
    assert result["direction"].dtype == np.int64 or result["direction"].dtype == int
    assert result["price"].dtype == float


# ---- Geometría de los registros de Fair Value Gap ----


def test_fair_value_gap_records_span_the_three_candles(sine_ohlc):
    """Un FVG ocupa las velas [pos-2, pos]. `left_index`/`left_time`
    apuntaban a `pos` (la vela de confirmación) igual que `right_index`, así
    que una caja dibujada con `left_index` arrancaba 2 velas tarde."""
    records = sine_ohlc.smc.fair_value_gaps(as_records=True, include_filled=True)
    assert records

    frame = sine_ohlc.smc.fair_value_gaps(include_filled=True)
    confirming = list(sine_ohlc.index.get_indexer(frame.index))
    assert [r["right_index"] for r in records] == confirming

    for record in records:
        assert record["left_index"] == max(record["right_index"] - 2, 0)
        assert record["left_time"] == sine_ohlc.index[record["left_index"]]
        assert record["right_time"] == sine_ohlc.index[record["right_index"]]


def test_fair_value_gap_record_bounds_come_from_the_right_bars(sine_ohlc):
    """El borde del hueco de un FVG alcista es `high` de la vela izquierda y
    `low` de la de confirmación — comprobado contra el df, no solo contra sí mismo."""
    records = [
        r for r in sine_ohlc.smc.fair_value_gaps(as_records=True, include_filled=True) if r["direction"] == 1
    ]
    assert records
    for record in records:
        left = sine_ohlc.iloc[record["left_index"]]
        right = sine_ohlc.iloc[record["right_index"]]
        assert record["bottom"] == pytest.approx(left["high"])
        assert record["top"] == pytest.approx(right["low"])


# ---- Superficie pública exportada ----


def test_every_enum_is_reachable_from_the_package_root():
    """`ZoneOrigin` (y ahora `ZoneSide`) quedaban fuera de `__all__` aunque
    son parámetros públicos de `demand_zone`."""
    import pandas_luarix as pl

    for name in ("EqualLevelMethod", "ObMitigation", "VolatilityMethod", "LiquidityLevels", "ZoneOrigin", "ZoneSide"):
        assert name in pl.__all__, f"{name} no está en __all__"
        assert getattr(pl, name, None) is not None


def test_package_exposes_a_version():
    import pandas_luarix as pl

    assert isinstance(pl.__version__, str)


# ---- Fixtures calculados a mano (tests/builders.py) ----


def test_double_top_pivots_and_equal_high_match_the_hand_computed_fixture():
    """`builders.double_top` documenta pivots, niveles y grupos EQH exactos,
    calculados a mano al diseñar la serie. Este test los fija: si el motor de
    pivotes o el de equal levels cambia, falla acá con números concretos."""
    df, expected = double_top()

    highs = df.smc.swing_high(length=LENGTH, include_mitigated=True)
    lows = df.smc.swing_low(length=LENGTH, include_mitigated=True)
    assert list(df.index.get_indexer(highs.index)) == [p["origin_pos"] for p in expected["pivot_highs"]]
    assert list(df.index.get_indexer(lows.index)) == [p["origin_pos"] for p in expected["pivot_lows"]]
    assert highs["high"].to_numpy() == pytest.approx([p["level"] for p in expected["pivot_highs"]])
    assert lows["low"].to_numpy() == pytest.approx([p["level"] for p in expected["pivot_lows"]])

    assert df.smc.bos_choch(length=LENGTH).empty  # ningún close cruza un nivel rastreado
    assert df.smc.fair_value_gaps(include_filled=True).empty

    groups = df.smc.equal_high(length=LENGTH, atr_period=ATR_PERIOD, include_mitigated=True)
    assert len(groups) == len(expected["equal_highs"])
    group, expected_group = groups[0], expected["equal_highs"][0]
    assert list(df.index.get_indexer(group.index)) == expected_group["member_origin_pos"]
    assert float(group["high"].mean()) == pytest.approx(expected_group["level_mean"])
    assert not group["mitigated"].any()

    assert df.smc.equal_low(length=LENGTH, atr_period=ATR_PERIOD, include_mitigated=True) == []


def test_stop_hunt_sweep_matches_the_hand_computed_fixture():
    """El sweep de este fixture ocurre en la barra 14, 3 velas DESPUÉS de la
    confirmación del pivot (barra 11). El docstring del builder lo marcaba
    como xfail esperado contra una versión vieja que escaneaba desde
    `origin_pos + 1` con `max_confirmation_bars=1`; el escaneo actual arranca
    en `origin_pos + length` y lo encuentra. Queda fijado como test normal."""
    df, expected = stop_hunt()

    sweeps = df.smc.liquidity_sweep(length=LENGTH, levels="swings", max_confirmation_bars=5)
    assert len(sweeps) == len(expected["sweeps"])

    sweep, expected_sweep = sweeps.iloc[0], expected["sweeps"][0]
    assert int(df.index.get_indexer(sweeps.index)[0]) == expected_sweep["sweep_pos"]
    assert sweep["swept_level"] == pytest.approx(expected_sweep["swept_level"])
    assert sweep["swept_level_type"] == expected_sweep["swept_level_type"]
    assert sweep["direction"] == expected_sweep["direction"]

    # Sweep y ruptura son mutuamente excluyentes: el close vuelve por debajo
    # del nivel, así que no hay BOS/CHoCH ni mitigación del swing high.
    assert df.smc.bos_choch(length=LENGTH).empty
    assert not df.smc.swing_high(length=LENGTH, include_mitigated=True)["mitigated"].any()
