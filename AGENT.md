# AGENT.md — `pandas-luarix`

Guía de orientación rápida para trabajar en este repo sin tener que releerlo entero.

## Qué es

Una librería **pura de cálculo**: recibe un `pd.DataFrame` OHLC y devuelve otro
DataFrame con lo detectado. Se instala con `pip install pandas-luarix` y se activa
con un solo import, que registra tres accessors de pandas:

```python
import pandas_luarix   # el import ES el side effect: registra .smc/.indicators/.analysis
df.smc.order_blocks()
```

**Lo que la librería NO hace** (y no debe empezar a hacer): descargar velas, hablar
con Binance, dibujar gráficos, persistir en BD, exponer HTTP. Todo eso vive en el
repo hermano `nexora-trading-framework` (`d:\Trabajo\nexora-trading-framework`),
que consume esta librería. Si un cambio aquí necesita `requests`, `django`,
`fastapi` o `matplotlib`, está en el repo equivocado.

## Mapa del repo

```
pandas_luarix/          <- el paquete (lo único que se publica en pip)
├── __init__.py         <- API pública: reexporta accessors + enums
├── _core/              <- algoritmos puros: funciones sobre Series/arrays, sin pandas accessors
├── smc/accessor.py     <- @register_dataframe_accessor("smc")        (821 líneas, el grueso)
├── indicators/accessor.py  <- @register_dataframe_accessor("indicators")
└── analysis/accessor.py    <- @register_dataframe_accessor("analysis")

tests/                  <- pytest; builders.py = fixtures OHLC sintéticos deterministas
test_data/              <- 77 CSV reales de Binance (19 símbolos × 4-5 timeframes, 30 MB)
docs/plans/             <- planes y bugs.md (leer bugs.md ANTES de investigar algo)
```

## La regla de arquitectura que estructura todo

**`_core/` no conoce pandas-accessors; `*/accessor.py` no implementa algoritmos.**

- `_core/*.py` = funciones libres que reciben Series/DataFrames y devuelven Series/
  DataFrames de eventos. Testeables en aislamiento (ver `tests/test_fractals.py`,
  que importa `_core.fractals` directo sin pasar por ningún accessor).
- `*/accessor.py` = validación de parámetros + orquestación + ensamblado del
  DataFrame de salida. Cada método público empieza validando y termina devolviendo
  filas del df original más columnas nuevas.

Añadir un indicador nuevo = una función en `_core/` + un método delgado en el
accessor que corresponda.

## Convenciones que se repiten en todo el código

| Convención | Dónde | Detalle |
|---|---|---|
| Validación al entrar | `_core/validation.py` | `validate_ohlc_columns` en cada `__init__` de accessor; `check_positive_int/float`, `require_min_rows` al inicio de cada método público |
| Categóricos como Enum | `_core/enums.py` | `EqualLevelMethod`, `ObMitigation`, `VolatilityMethod`, `LiquidityLevels`, `ZoneOrigin` — todos `(str, Enum)`. Cada método coacciona con `Enum(value)`, lo que da `ValueError` gratis ante valores inválidos |
| Nunca borrar, marcar | `order_blocks.py`, `fair_value_gaps.py`, `equal_levels.py` | Los elementos mitigados/rellenados se **retienen** con columna booleana; `include_mitigated` / `include_filled` solo filtran la vista devuelta |
| Salida = filas del df + columnas | todos los accessors | El resultado siempre es indexable contra el df de entrada. Salida vacía = `df.iloc[0:0]` con las columnas esperadas, nunca `None` ni un df sin columnas |
| Columnas OHLC en minúscula | `validation.py` | `open`, `high`, `low`, `close`. `volume` es opcional |

## El gotcha nº1: pivots de confirmación vs. origen

`find_pivots` (`_core/pivots.py`) devuelve Series *sparse*: NaN salvo en la vela de
**confirmación** (posición `i`), pero el valor que guarda es el precio de la vela de
**origen** (posición `i - length`). Indexar con `pivot_high.notna()` selecciona la
vela equivocada — hay que restar `length` a las posiciones:

```python
positions = pivot_high.notna().to_numpy().nonzero()[0] - length
```

Este desfase ya causó un bug real y es la fuente más probable de look-ahead bias en
cualquier código nuevo que consuma pivots. Está documentado en `docs/plans/bugs.md`.

## Superficie pública

- **`df.smc`** — `swings`, `swing_high`, `swing_low`, `equal_high`, `equal_low`,
  `equal_high_low`, `bos_choch`, `bullish_order_block`, `bearish_order_block`,
  `order_blocks`, `fair_value_gaps`, `liquidity_sweep`, `fractal`, `ipda_fractal`,
  `demand_zone`, `expansion`, `consolidation`, `fib_expansion`.
  Ojo: `equal_*` devuelven **list[DataFrame]** (un df por grupo de niveles iguales),
  no un DataFrame.
- **`df.indicators`** — `bb50`, `ema`, `rsi`, `atr`, `stochastic_oscillator`.
  Delegan en `pandas_ta_classic`, salvo el estocástico que es cálculo propio.
- **`df.analysis`** — `divergence(indicator: pd.Series, length)`. Es agnóstico del
  indicador: le pasas cualquier Series alineada al índice (RSI, %K, CVD...).

Defaults con historia detrás, no tocar a la ligera: `length=3` en `equal_*` (el
resto usa `50`), `atr_period=200`.

## Entorno

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pip install -e .
.venv/Scripts/python -m pytest          # 48 pasan, 3 se saltan
```

Python 3.13 · pandas 3.0 · numpy 2.5 · pandas_ta_classic 0.6.

- `requirements.txt` = solo runtime (espejo de `[project].dependencies`).
- `requirements-dev.txt` = runtime + pytest + jupyterlab + matplotlib.

## Los 3 tests que se saltan

`test_order_blocks_match_reference_smc_indicator`,
`test_fair_value_gaps_matches_reference_smc_indicator` y
`test_equal_high_low_matches_reference_smc_indicator` comparan bit-a-bit contra
`app.tradingview.smc_indicator` (el port Python del indicador LuxAlgo de Pine), que
vive en `nexora-trading-framework` y se usó como **oráculo** durante el desarrollo.
Van con `pytest.importorskip`, así que aquí se saltan y allí corren. No son deuda
técnica: si tocas ATR, order blocks o equal levels, vale la pena correrlos con el
otro repo en el `PYTHONPATH`.

## Deuda conocida

- `tests/builders.py` (167 líneas de fixtures OHLC documentados y verificados) no lo
  importa ningún test todavía. Es infraestructura lista para usar, no código muerto.
- `notebooks/` se borró entero: los 6 notebooks importaban `app.brokers` /
  `app.tradingview` / `config.settings` del repo nexora y no arrancaban aquí. Falta
  rehacer uno de demo contra la librería instalada + `test_data/`.
- `README.md` no documenta aún parámetros método por método.
