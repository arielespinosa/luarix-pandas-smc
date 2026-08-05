# Bugs y hallazgos importantes

> Cosas ya analizadas — leer antes de volver a investigar el código para no repetir trabajo.
> Solo entradas de ESTA librería. El histórico de `luarix_rest_api` / `fastapi_server` /
> frontend / Pine vive en el repo `nexora-trading-framework`.

---

## El paquete no se empaquetaba: la raíz del repo ERA el paquete (resuelto)

Al extraer esta librería de `nexora-trading-framework`, la carpeta `pandas_luarix/`
se convirtió en la raíz del repo. Consecuencias que dejó ese corte, todas resueltas:

- **`pip install .` producía un paquete VACÍO.** `[tool.setuptools.packages.find]`
  buscaba `include = ["pandas_luarix*"]` y no había ninguna carpeta con ese nombre —
  `top_level.txt` del `.egg-info` quedaba literalmente en blanco. No fallaba con
  error: instalaba nada, en silencio.
- **Los ~20 imports `from pandas_luarix._core...` ya eran los correctos.** La
  tentación era quitarles el prefijo (`from _core.enums import ...`), que arregla la
  ejecución desde la raíz pero rompe justo el `pip install`: setuptools instalaría
  4 nombres top-level genéricos (`_core`, `smc`, `indicators`, `analysis`) en
  site-packages, con riesgo real de colisión, y `import pandas_luarix` dejaría de
  existir junto con el `__init__.py` que define la API pública. **Fix**: recrear la
  carpeta `pandas_luarix/` y mover dentro los 4 paquetes + `__init__.py` — cero
  ediciones de imports. Verificado: el wheel empaqueta 21 módulos, `top_level.txt`
  dice `pandas_luarix`, y no arrastra `tests/`, `test_data/` ni `docs/`.
- **`__pycache__/` y `pandas_luarix.egg-info/` estaban COMMITEADOS** (no había
  `.gitignore`). Los `.pyc` eran de CPython 3.14, un intérprete que ya ni figura en
  el `py` launcher de esta máquina.
- **Fixture `btc_daily_df` apuntaba a una ruta muerta**: `backtests_data/BTCUSDT/1d.csv`
  con `dirname(dirname(__file__))` desde la raíz — o sea, el directorio PADRE del
  repo. Esa carpeta se renombró a `test_data/` al extraer la librería. Ahora los
  tests viven en `tests/`, así que `dirname(dirname(__file__))` sí da la raíz.

## Los 3 tests que comparan contra `app.tradingview` no son deuda técnica

`test_order_blocks_match_reference_smc_indicator`,
`test_fair_value_gaps_matches_reference_smc_indicator` y
`test_equal_high_low_matches_reference_smc_indicator` importan
`app.tradingview.smc_indicator` (el port Python del LuxAlgo de Pine) como **oráculo**
de comparación bit-a-bit. Ese módulo vive en `nexora-trading-framework`, no aquí.

Llevan `pytest.importorskip`, así que en este repo se saltan (48 pasan, 3 skip) y en
el otro corren. **No borrarlos**: son la única defensa contra el tipo de bug del
punto 9 de la sección siguiente (ATR con arranque SMA-seed vs EMA-cold-start, que
divergía ~10% durante cientos de barras sin lanzar ningún error). Si tocas ATR,
order blocks o equal levels, córrelos con el otro repo en el `PYTHONPATH`.

---

## `pandas_luarix` — gotchas del port `SMCIndicator`/LuxAlgo (`app/tradingview/`) que la nueva librería NO debe repetir

Contexto: `pandas_luarix/` (accessors `.smc`/`.structure` sobre `pd.DataFrame`) es una librería nueva e independiente — NO importa `app/tradingview/`. El código de `app/tradingview/smc_indicator.py` (port bar-a-bar de Pine LuxAlgo) se usó solo como referencia algorítmica para el primer batch de indicadores (swings, equal highs/lows, BOS/CHoCH, order blocks, fair value gaps, liquidity sweeps). Hallazgos de esa referencia que se evitaron deliberadamente en el diseño nuevo:

1. **Campos muertos en `SMCConfig`** (`app/tradingview/types.py:309-322`): `max_swing_obs`, `max_internal_obs`, `detect_trailing` se declaran pero nunca se leen en `smc_indicator.py`. El cap real de order blocks es un literal hardcodeado `100` en `_store_order_block` (línea 684), no controlado por config. → En `pandas_luarix` todo parámetro expuesto se consume realmente en la implementación; no hay cap de retención de order blocks (se retienen todos, mitigados incluidos, con flag).
2. **Default de ATR inconsistente**: `_compute_atr(..., period=200)` es el default interno de `SMCIndicator.run()` (`smc_indicator.py:97`), pero el caller real (`contexts.py:216`) precalcula `ta.atr(..., 100)` y lo inyecta vía `precomputed_atr`, pisando silenciosamente el default de 200. → `pandas_luarix` usa `atr_period=14` como único default explícito en todo helper que consuma ATR (`_core/volatility.py`), siempre como kwarg explícito, nunca heredado de un objeto de config compartido.
3. **Borrado destructivo de order blocks/FVG mitigados en vez de flag**: `_delete_order_blocks` (líneas 710-720) hace `ob.mitigated = True` y ACTO SEGUIDO `obs.pop(idx)` — el flag queda en un objeto ya removido de la única lista que lo referencia. Mismo patrón en `_delete_fair_value_gaps`. → `pandas_luarix` retiene SIEMPRE las filas mitigadas/filled con su columna booleana (`mitigate_order_blocks`, `mark_filled_fvgs` en `_core/`); `include_mitigated`/`include_filled` solo filtran la vista devuelta.
4. **Threshold de FVG nunca implementado**: `threshold = 0.0` hardcodeado (líneas 758-759), simulando una feature que nunca se calculó de verdad. → `pandas_luarix.smc.fair_value_gaps()` implementa un filtro de tamaño mínimo real y funcional (`min_gap_atr_multiple`, comparado contra `ATR(atr_period)`), no un parámetro decorativo.
5. **Dos algoritmos de Equal High/Low incompatibles conviviendo sin resolver**: el ATR/pivot-based (dentro de `_get_current_structure`) y el pct-based (`find_equals_in_ohvl`/`_group_equal_pct`) son funciones separadas, hay que invocar la segunda a mano y pisar `result.equal_highs/equal_lows`. → `pandas_luarix.structure.equal_high/equal_low` exponen ambos vía `method: EqualLevelMethod = ATR_PIVOT | PCT_RANGE`, con default explícito y documentando qué parámetros aplican a cada rama.
6. **Multiplicador de alta volatilidad hardcodeado**: `high_vol_bar = (h - l) >= 2 * vol` (línea 130), el `2` es literal. → `pandas_luarix` lo expone como `high_vol_multiplier` explícito en `_core/volatility.py::parsed_high_low`.
7. **Bug propio encontrado durante la implementación (no viene de la referencia)**: al construir `structure.swing_high()`/`swing_low()`/`swings()`, la primera versión devolvía la fila de la vela de **confirmación** del pivot (posición `i`, donde el algoritmo de detección "se entera" de que hubo un pivot) en vez de la vela de **origen** (posición `i - length`, donde realmente ocurrió el extremo de precio). Como el valor del pivot (`pivot_high`/`pivot_low`) se guarda en `find_pivots` en la posición de confirmación pero representa el precio de `length` barras atrás, usar `df.loc[pivot_high.notna()]` directamente selecciona la vela equivocada — el contenido de esa fila (open/high/low/close de la vela de confirmación) no coincide con el nivel de precio que describe. Fix: restar `length` a las posiciones de confirmación antes de indexar (`pivot_high.notna().to_numpy().nonzero()[0] - length`). Lección: cuando una serie "sparse" (NaN salvo en el bar de confirmación) representa un valor que en realidad pertenece a una barra anterior (por `shift(length)`), hay que propagar ese desfase a cualquier indexación posicional derivada de ella, no solo al valor.
8. **Categóricos como `Enum`, no strings sueltos**: la referencia usa strings mágicos (`ob_filter="Atr"`, `ob_mitigation="High/Low"`) sin validación. → `pandas_luarix._core.enums` define `EqualLevelMethod`, `ObMitigation`, `VolatilityMethod`, `LiquidityLevels` como `class X(str, Enum)`; cada método coacciona el valor recibido con `EnumType(value)`, dando `ValueError` automático ante valores inválidos.
9. **Bug propio, encontrado por un reporte del usuario (`equal_high` devolvía `[]`) — dos causas reales apiladas, no solo un parámetro mal pasado**:
   - **Defaults mal elegidos**: `equal_high`/`equal_low`/`equal_high_low` heredaban `length=50` de `swings`/`bos_choch`/`order_blocks`, pero en `SMCConfig` el lookback de equal-highs/lows es un campo independiente y mucho más corto (`equal_length`, default `3`). Fix: `length` default bajado a `3` en esos tres métodos (el resto de `structure` mantiene `50`, que sí coincide con `swing_length`).
   - **Bug de cómputo real en `compute_atr`**: usaba `tr.ewm(alpha=1/period, adjust=False, min_periods=period)`, que arranca la recursión de Wilder desde la primera barra de la serie. La referencia (`SMCIndicator._compute_atr`) en cambio **siembra el ATR con el promedio simple (SMA) de las primeras `period` barras** y solo desde ahí aplica la recursión de Wilder — son fórmulas matemáticamente distintas (no solo una reimplementación equivalente) que divergen sistemáticamente por cientos de barras (medido: ATR(200) en la barra 450 daba 455.48 vs 508.87 de la referencia, ~10% de diferencia), suficiente para que pares de equal-highs/lows caigan del lado equivocado del umbral `equal_threshold * ATR`. Fix: `compute_atr` ahora siembra con `tr.iloc[:period].mean()` y aplica `.ewm(adjust=False)` solo sobre la cola, arrancando la recursión en ese punto — validado bit-a-bit (diferencia máxima 0.0) contra la referencia en una serie de 3241 barras.
   - También se corrigió `detect_equal_levels_atr_pivot` para usar comparación estricta `<` (la referencia usa `abs(...) < threshold`, `pandas_luarix` tenía `<=`).
   - Con ambos fixes + defaults alineados (`length=3`, `atr_period=200` — el default real de `SMCIndicator._compute_atr` cuando no se pasa `precomputed_atr`), `equal_high`/`equal_low` con **cero argumentos explícitos** replican exactamente (23/23 y 21/21 grupos, mismos índices) a `SMCIndicator(SMCConfig()).run(df)` con config y ATR puramente por defecto. Test de regresión: `test_equal_high_low_matches_reference_smc_indicator` en `test_pandas_luarix.py`.
   - **Lección general**: al portar un indicador con ATR/Wilder u otro suavizado recursivo, "misma fórmula en teoría" no basta — hay que validar bit-a-bit contra la referencia, porque el manejo del arranque/warmup (SMA-seed vs EMA-cold-start) puede divergir silenciosamente por cientos de barras sin lanzar ningún error, solo produciendo resultados sutilmente distintos (grupos/eventos de menos, no un crash).

Es documentación, no código del que `pandas_luarix` dependa.

