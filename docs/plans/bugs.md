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

## El pivote es ASIMÉTRICO — no confundir con `ta.pivothigh` (NO es un bug)

Al construir el notebook de verificación visual escribí un assert "obvio" — el high de un
swing high debe ser el máximo de su ventana ±length — y **falló en 3 de 10 swings**. El
assert estaba mal, no la librería.

`compute_leg` (`_core/pivots.py`) porta la función `leg()` de LuxAlgo, cuya condición es:

```python
new_leg_high = high.shift(length) > high.rolling(length).max()
#              high[i-length]     >  max(high[i-length+1 .. i])
```

**Solo mira las `length` velas POSTERIORES al pivote.** No exige nada de las anteriores, a
diferencia de `ta.pivothigh` de Pine, que es simétrico. Un swing high puede tener velas más
altas a su izquierda y seguir siendo válido.

Segundo efecto del mismo algoritmo: `find_pivots` solo emite un pivote cuando la pierna
**cambia** de sentido (`leg != leg.shift(1)`), así que los swings **alternan** high/low
estrictamente — nunca salen dos highs seguidos.

Medido sobre BTCUSDT 1d, 260 velas, `length=10`: 10 swing highs y 10 swing lows, **0**
incumplen la definición asimétrica real, **3 de cada lado** incumplen la simétrica. Ambas
comprobaciones quedaron como celdas con `assert` en
`notebooks/01_pandas_luarix.ipynb` §1.

**Antes de reportar una diferencia contra TradingView como bug, comprobar si es esto.**

## Verificación visual: qué se comprobó y qué salió (sesión de limpieza)

`notebooks/01_pandas_luarix.ipynb` + `notebooks/plot_smc.py` (helper de ploteo con
matplotlib, deliberadamente FUERA del paquete — la librería no dibuja). Resultados sobre
BTCUSDT 1d / 260 velas:

- **Divergencias**: las 4 combinaciones (`regular`/`hidden` × `bullish`/`bearish`) imponen
  el signo de las dos pendientes. Comprobado numéricamente: 3/3 coherentes. Es un test
  automático, no depende del ojo.
- **Fractal**: `confirm_time - origen` == exactamente `length` para los 28 fractales, o sea
  sin look-ahead bias.
- **Bollinger**: `middle` == `SMA(20)` exacta (`np.allclose`). Ojo: el % de cierres dentro
  de las bandas da ~81%, **no** el 95% teórico — eso es normal y NO es un fallo (el 95%
  asume retornos normales; una serie de precios real es tendencial y de colas pesadas).
- **Barrido multi-símbolo** (BTC/ETH/SOL/DOGE/PEPE/XRP): los detectores dan conteos
  comparables en los 6, con precios de $60.112 a $0,0000067 — **7 órdenes de magnitud** sin
  degradarse. Descarta supuestos de escala de precio hardcodeados.
- `ipda_fractal` devuelve 0 filas con `length=10` en 260 velas — necesita una secuencia
  completa de pivotes alternados; no es un fallo, pero conviene tenerlo presente al probar.
- `print(mode)` de debug encontrado y eliminado en `smc/accessor.py::ipda_fractal`.

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

## Revisión de cierre (paso a producción) — 10 bugs vivos encontrados y arreglados

Barrido completo de la superficie pública antes de dar el proyecto por cerrado. Los 48
tests existentes pasaban con TODOS estos bugs presentes: ninguno se manifestaba en el
camino feliz (df con índice de fechas, parámetros literales de Python, resultado no
vacío). Regresiones en `tests/test_contracts.py`; suite ahora en **84 pasan, 3 skip**.

| # | Qué pasaba | Severidad |
|---|---|---|
| 1 | `ipda_fractal` reventaba con `TypeError` en cualquier df de índice NO temporal | crash |
| 2 | `analysis.divergence` con un indicador desalineado devolvía las barras equivocadas | silencioso |
| 3 | `demand_zone(side=...)` aceptaba cualquier string; todo lo != `"support"` daba resistencia | silencioso |
| 4 | `liquidity_sweep` vacío perdía las columnas OHLC | contrato |
| 5 | En los records de FVG, `left_index`/`left_time` apuntaban a la vela de confirmación | dato mal etiquetado |
| 6 | `check_positive_int` rechazaba enteros de numpy (`np.int64`) | fricción de API |
| 7 | `ZoneOrigin` no estaba exportado desde `pandas_luarix` | fricción de API |
| 8 | `indicators.ema(source=...)` lanzaba `KeyError` crudo en vez de `ValueError` | fricción de API |
| 9 | El resultado vacío de `divergence` declaraba todas las columnas `object` | cosmético |
| 10 | `demand_zone(offset_pct=<0)` producía una banda invertida (`bottom > top`) | silencioso |

Detalle de los que dejan lección, no solo parche:

1. **`ipda_fractal` en índice no temporal.** `_attach_point_times` construía la columna
   de tiempos como `pd.Series(pd.NaT, dtype="datetime64[ns]")` y luego le asignaba
   `date_index[pos]`. Con un `RangeIndex` eso es asignar enteros a un bloque
   datetime64 → `TypeError`. Era la ÚNICA parte de la librería que asumía índice de
   fechas; todo el resto trabaja con posiciones y `date_index[...]` genérico. Fix: el
   hueco sale del propio índice (`NaT` si es `DatetimeIndex`, `None` si no) y se cierra
   con `infer_objects()`. **Lección**: los `dtype=` literales en construcción de
   columnas derivadas del índice son un supuesto sobre el índice del usuario.

2. **`divergence` con indicador desalineado — corrupción silenciosa.** El detector
   busca pivotes sobre las posiciones de la SERIE del indicador y usa esas posiciones
   para indexar el DF. Si la serie es más corta o tiene otro índice, el resultado son
   filas reales del df pero de barras que no corresponden: no hay `IndexError` porque
   las posiciones son válidas, solo están mal. Medido: un RSI recortado a 50 valores
   contra un df de 400 filas devolvía 1 evento (en vez de 10) apuntando a una barra
   arbitraria. Fix: `check_aligned_series` exige mismo largo Y mismo índice.
   **Lección**: cuando una función mezcla posiciones de dos objetos distintos, la
   alineación es una precondición que hay que verificar, no asumir.

5. **Geometría de los records de FVG.** Un FVG ocupa 3 velas `[pos-2, pos]`, pero el
   record ponía `left_index = right_index = pos` y `left_time` = tiempo de confirmación.
   Cualquiera que dibujara la caja con `left_index` la arrancaba 2 velas tarde. Se
   corrigió a `left_index = pos - 2` y se agregó `right_time`. **Es un cambio de valor
   devuelto**: si `nexora-trading-framework` compensaba el desfase a mano al dibujar,
   hay que quitar esa compensación. `right_index` no cambió (sigue siendo la vela de
   confirmación, que es contra lo que compara el test del oráculo LuxAlgo).

6. **Enteros de numpy.** `isinstance(np.int64(20), int)` es `False` en Python. Cualquier
   `length` que viniera de `.astype(int)`, de un índice posicional de numpy o de config
   deserializada era rechazado como "no es un int positivo" pese a serlo. Fix:
   `numbers.Integral` / `numbers.Real` (siguen rechazando `bool`, que es `Integral`).

Cosas que se comprobaron y **NO** son bugs (no volver a investigar):

- `_core/zones.py::build_zone` llama a `df.smc.fractal()`, lo que parece romper la regla
  "`_core` no conoce accessors". No falla nunca: importar `pandas_luarix._core.zones`
  importa el paquete padre, que registra los accessors. Sigue siendo un olor
  arquitectónico, no un bug.
- OHLC con `NaN` sueltos no rompe ningún detector ni cambia los conteos de forma
  apreciable (las comparaciones con NaN dan False y el evento simplemente no se emite).
- Índice duplicado o no monótono: `swings`/`fractal` funcionan (indexan por posición).
  Lo que sí rompe con índice duplicado es `get_indexer([label])`, usado en las ramas
  `as_records` y en `_levels_table_from_groups`.
- Serie plana en `stochastic_oscillator`: la división `0/0` da `NaN`, no lanza.
- `pytest -W error::FutureWarning -W error::DeprecationWarning` pasa limpio con
  pandas 3.0 / numpy 2.5.

## Deriva de documentación corregida en la misma revisión

`AGENT.md` (y este archivo) referenciaban un `notebooks/01_verificacion_visual.ipynb`
que ya no existe: el notebook real es `notebooks/01_pandas_luarix.ipynb`.
`tests/builders.py` figuraba como "infraestructura sin usar": ahora la consume
`tests/test_contracts.py`, y sus `expected` calculados a mano coinciden EXACTAMENTE con
la implementación actual — incluido el sweep de `stop_hunt()` que el docstring daba por
`xfail` "hasta la Fase 3.1" (ese fix ya está: el escaneo arranca en
`origin_pos + length`, no en `origin_pos + 1`).

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

