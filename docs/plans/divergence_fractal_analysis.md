# Nuevos elementos de `pandas_luarix` (Divergencia + Fractal) y `id` estable para elementos SMC

## Contexto

Hasta ahora `pandas_luarix` tiene dos accessors con indicadores concretos:
`df.smc` (pivots, BOS/CHoCH, order blocks, liquidity sweeps, fair value gaps) y
`df.indicators` (BB50, Stochastic Oscillator). La API HTTP los expone en 2 grupos
(`"indicator"`/`"smc"`) con un contrato de 5 tipos de elemento visual
(`marker`/`line`/`box`/`line_series`/`multiline_series`).

Todos los elementos ("SMC" y "Indicadores") se calculan de forma 100% automática a
partir de las velas. Pero el frontend va a agregar un tab **"Propiedades"** en el
modal de configuración de cada elemento de tipo **SMC** (concepto de smart-money —
pivots, equal levels, BOS/CHoCH, order blocks, liquidity sweep, fair value gaps,
fractal — **no** aplica a BB50/Stochastic, que son series densas sin una "vela de
origen" que tenga sentido reasignar): ese tab muestra los valores CRUDOS del objeto
detectado (no el estilo — eso ya vive 100% en el frontend) para que el usuario
pueda editarlos a mano — por ejemplo, si el detector marcó un swing high en la vela
X y luego, al llegar más velas, el pivote "se repinta" en otro lado, el usuario
pueda fijar manualmente a qué vela pertenece.

Confirmado con el usuario: esta edición vive **100% en el frontend** (localStorage
o similar) — no se agrega base de datos ni persistencia en el backend. Lo único
que necesita el backend es que cada elemento traiga un **`id` estable y
determinístico** (mismo evento detectado ⇒ mismo `id` entre refetches/repaints),
para que el frontend pueda asociar el override guardado con la instancia correcta
del objeto después de recalcular. Este `id` se agrega a **todos** los elementos
"SMC" que ya existen hoy (swings, swing_high, swing_low, equal_high, equal_low,
equal_high_low, bos_choch, bullish_order_block, bearish_order_block, order_blocks,
liquidity_sweep, fair_value_gaps) y a los 2 nuevos de este plan (divergence,
fractal) — **no** a bb50/stochastic_oscillator.

Además se necesitan 2 elementos nuevos:

1. **Detector de divergencias genérico** — en vez de implementar "divergencia RSI",
   "divergencia MACD", etc. por separado, un único detector que compara pivotes de
   **cualquier serie temporal** (RSI, MACD, Volume Oscillator, CVD, Delta, Momentum...)
   contra el precio, para clasificar las 4 divergencias clásicas (regular
   alcista/bajista, oculta alcista/bajista). Como no es un "indicador" ni un
   concepto "smc", vive en un **grupo nuevo: `analysis`** — este es su primer
   elemento.
2. **Fractal** — un elemento `smc` nuevo: caja (alto, bajo, rango horizontal) que
   representa un swing point, pensado como base para futuros elementos IPDA.

Decisiones ya confirmadas con el usuario:
- Divergencia: los pivotes se detectan **solo sobre el indicador** (no sobre precio
  por separado) — en esas mismas barras se lee el precio para comparar. Evita el
  problema de emparejar dos conjuntos de pivotes independientes.
- Fractal: es un **detector automático** que reutiliza la misma primitiva de pivotes
  (`find_pivots`) que ya usan `swings`/`order_blocks`, no una estructura pasiva.

## 1. Detector de divergencias — `df.analysis.divergence(...)`

### Núcleo puro: `pandas_luarix/_core/divergence.py`

```python
def detect_divergence(
    high: pd.Series, low: pd.Series, indicator: pd.Series, length: int = 5
) -> pd.DataFrame:
    """
    Detecta pivotes CONFIRMADOS de `indicator` (reusa find_pivots(indicator, indicator, length)
    — el mismo truco de pasar la misma serie como "high" y "low" que ya usa `stochastic_oscillator`
    para pivotar una serie única). En cada par CONSECUTIVO de pivotes bajos, compara:
        precio (low) en esas 2 barras  vs  indicador en esas 2 barras
    y en cada par consecutivo de pivotes altos:
        precio (high) en esas 2 barras vs  indicador en esas 2 barras

    Clasificación (las 4 reglas estándar):
        - regular_bullish : price[p2] <  price[p1]  Y  indicator[p2] >  indicator[p1]   (LL precio, HL indicador)
        - hidden_bullish  : price[p2] >  price[p1]  Y  indicator[p2] <  indicator[p1]   (HL precio, LL indicador)
        - regular_bearish : price[p2] >  price[p1]  Y  indicator[p2] <  indicator[p1]   (HH precio, LH indicador)
        - hidden_bearish  : price[p2] <  price[p1]  Y  indicator[p2] >  indicator[p1]   (LH precio, HH indicador)

    Devuelve un DataFrame con una fila por evento: `position` (posición entera del
    segundo pivote, para indexar el df OHLC completo), `divergence_type`
    (uno de los 4 strings de arriba), `direction` (1 alcista / -1 bajista),
    `price` (precio en el segundo pivote), `prior_position`, `prior_price`
    (precio en el primer pivote), `indicator_value`, `prior_indicator_value`.
    """
```
Implementación: usar `find_pivots(indicator, indicator, length)` para obtener
`(ind_pivot_high, ind_pivot_low)`; para cada serie, las posiciones de origen son
`pivot.notna().nonzero()[0] - length` (mismo patrón que `swings()`/`_swing_side()`
en `pandas_luarix/smc/accessor.py`). Iterar pares consecutivos `(p1, p2)` de
posiciones de origen (bajos entre sí para bullish, altos entre sí para bearish) y
aplicar las 4 reglas de arriba con `low`/`high` según corresponda.

### Accessor: `pandas_luarix/analysis/accessor.py`

```python
@pd.api.extensions.register_dataframe_accessor("analysis")
class AnalysisAccessor:
    """Herramientas de análisis genéricas, no atadas a un indicador concreto."""

    def __init__(self, df: pd.DataFrame):
        validate_ohlc_columns(df)
        self._df = df

    def divergence(self, indicator: pd.Series, length: int = 5) -> pd.DataFrame:
        """
        `indicator` es CUALQUIER serie alineada al mismo índice que el df (RSI,
        MACD, Volume Oscillator, CVD, Momentum, el propio %K de Stochastic...).
        Columnas del resultado (fila = vela del segundo pivote de cada evento):
        `divergence_type`, `direction`, `price`, `prior_time`, `prior_price`,
        `indicator_value`, `prior_indicator_value`.
        """
        check_positive_int("length", length)
        require_min_rows(self._df, length * 2 + 1, context=f"divergence(length={length})")
        events = detect_divergence(self._df["high"], self._df["low"], indicator, length)
        if events.empty:
            return <df vacío con las mismas columnas, patrón igual al resto de métodos>
        result = self._df.iloc[events["position"].to_numpy()].copy()
        result["divergence_type"] = events["divergence_type"].to_numpy()
        result["direction"] = events["direction"].to_numpy()
        result["price"] = events["price"].to_numpy()
        result["prior_time"] = self._df.index[events["prior_position"].to_numpy()]
        result["prior_price"] = events["prior_price"].to_numpy()
        result["indicator_value"] = events["indicator_value"].to_numpy()
        result["prior_indicator_value"] = events["prior_indicator_value"].to_numpy()
        return result
```
Registrar en `pandas_luarix/__init__.py` junto a `StructureAccessor`... (ya no existe,
ver bugs.md) — junto a `SMCAccessor`/`IndicatorsAccessor`: agregar
`from pandas_luarix.analysis.accessor import AnalysisAccessor` + `__all__`.

### Wiring API: nuevo grupo `analysis`

- `fastapi_server/schemas/catalog.py`: `IndicatorMetadataOut.group` pasa a
  `Literal["indicator", "smc", "analysis"]`.
- `fastapi_server/routers/meta.py`: agregar `GET /analysis` (mismo patrón que
  `/indicators`/`/smc`, `get_by_group("analysis")`).
- `fastapi_server/catalog/indicators.py`: nueva entrada `id="divergence"`,
  `group="analysis"`, `category="Divergence"`, `kind="line"`,
  `endpoint="/analysis/divergence"`.
- `fastapi_server/schemas/analysis.py` (nuevo): `DivergenceRequest(OHLCVRequestBase)`.
  **Limitación honesta de v1**: como hoy `pandas_luarix` NO tiene RSI/MACD/CVD/
  Volume Oscillator/Momentum implementados (solo BB50 y Stochastic Oscillator en
  `df.indicators`), la única fuente real disponible para "el indicador" es el
  propio Stochastic Oscillator. El request queda así, con params separados y
  claramente nombrados para no confundir "longitud del pivote de divergencia" con
  "longitud del stochastic":
  ```python
  class DivergenceRequest(OHLCVRequestBase):
      length: int = 5                     # longitud de pivote para la divergencia
      source: Literal["slow_k", "fast_d"] = "slow_k"
      stochastic_length: int = 14
      stochastic_d_length: int = 3
  ```
  El router (`fastapi_server/routers/analysis.py`, nuevo) computa
  `stoch = df.indicators.stochastic_oscillator(length=stochastic_length, d_length=stochastic_d_length)`,
  toma `stoch[request.source]` como la serie `indicator`, y llama
  `df.analysis.divergence(indicator=stoch[request.source], length=request.length)`.
  **Extensión futura** (no se hace ahora, solo se deja documentado): agregar RSI/
  MACD/etc. a `df.indicators` y sumar más branches a `DivergenceRequest.source` (o
  nuevas rutas `/analysis/divergence/<fuente>`) — el detector en sí
  (`df.analysis.divergence`) no cambia nada, ahí está la modularidad.
- `fastapi_server/services/visual_elements.py`: nueva `convert_divergence(df)` →
  `kind="line"`, `sub_kind=row["divergence_type"]` (uno de los 4 strings),
  `time1=row["prior_time"], price1=row["prior_price"], time2=index, price2=row["price"]`,
  `direction=row["direction"]`.

## 2. Fractal — `df.smc.fractal(...)`

Método nuevo en `pandas_luarix/smc/accessor.py` (mismo archivo que ya tiene
`swings`/`order_blocks`/etc. desde la consolidación — ver `docs/plans/bugs.md`).
Reutiliza `find_pivots` igual que `_swing_side`/`_order_block_side`, pero en vez de
devolver un marker (una vela), devuelve una **caja**: `top`/`bottom` = high/low de
la vela de ORIGEN del pivote, horizontal desde esa vela de origen hasta la vela de
CONFIRMACIÓN (`length` velas después) — mismo concepto de "origen vs confirmación"
que ya usan `swings()`/`_swing_side()`, aplicado a ambos extremos de la caja en vez
de a un solo punto.

```python
def fractal(self, length: int = 5, include_mitigated: bool = False) -> pd.DataFrame:
    """
    Fractales (swing highs/lows) representados como caja: `top`/`bottom` = high/low
    de la vela de origen del pivote; horizontal desde esa vela hasta la vela de
    confirmación (`confirm_time`). `direction`: 1 (fractal alcista, sobre un swing
    low — soporte) / -1 (fractal bajista, sobre un swing high — resistencia).
    Pensado como base para representar más adelante fractales estilo IPDA sin
    romper este contrato (top/bottom/horizontal/direction).
    """
```
Columnas del resultado (fila = vela de origen, igual que `swing_high`/`swing_low`):
`top`, `bottom`, `confirm_time`, `direction`, `mitigated` (mismo criterio de
mitigación que ya usa `_swing_side`: el precio cierra más allá del nivel después de
confirmado). `include_mitigated=False` filtra igual que en el resto de métodos.

### Wiring API

- `fastapi_server/catalog/indicators.py`: nueva entrada `id="fractal"`,
  `group="smc"`, `category="Fractals"`, `kind="box"`, `endpoint="/smc/fractal"`.
- `fastapi_server/schemas/smc.py`: `FractalRequest(OHLCVRequestBase)` con
  `length: int = 5`, `include_mitigated: bool = False`.
- `fastapi_server/routers/smc.py`: `POST /smc/fractal` → `df.smc.fractal(**kwargs)`
  → `convert_fractal`.
- `fastapi_server/services/visual_elements.py`: nueva `convert_fractal(df)` →
  `kind="box"`, `sub_kind = "bullish-fractal" if direction==1 else "bearish-fractal"`,
  `time1=index, price1=row["top"], time2=row["confirm_time"], price2=row["bottom"]`,
  `direction=row["direction"]`.

## 3. `id` estable en todos los elementos SMC (retrofit + los 2 nuevos)

`elements_response(elements, indicator_id=None)` en
`fastapi_server/services/visual_elements.py` gana un parámetro opcional
`indicator_id`. Cuando se pasa, estampa un campo `id` en cada elemento **antes**
de envolver en `{"elements": [...]}`:

```python
def elements_response(elements: list[dict], indicator_id: str | None = None) -> dict:
    if indicator_id:
        for el in elements:
            anchor = el.get("time", el.get("time1"))
            el["id"] = f"{indicator_id}:{el['sub_kind']}:{anchor}"
    return {"elements": elements}
```
`anchor` es `time` para `marker`, `time1` para `line`/`box` — la vela de ORIGEN del
evento, que es la parte estable entre recálculos (aunque el otro extremo —
`time2`/mitigación/etc. — cambie al repintarse con velas nuevas, el origen no).
`multiline_series` (bb50/stochastic) no tiene `sub_kind`/`time` de esta forma, así
que simplemente no se llama con `indicator_id` para esas 2 rutas — quedan sin `id`,
tal como se confirmó con el usuario.

Cada ruta de `routers/indicators.py` y `routers/smc.py` que hoy hace
`return elements_response(convert_x(result))` pasa a
`return elements_response(convert_x(result), indicator_id="<su id de catálogo>")`
— ej. `elements_response(convert_swings(result), indicator_id="swings")`,
`elements_response(convert_order_blocks(result), indicator_id="order_blocks")`,
etc., para los 12 métodos ya existentes (`swings`, `swing_high`, `swing_low`,
`equal_high`, `equal_low`, `equal_high_low`, `bos_choch`, `bullish_order_block`,
`bearish_order_block`, `order_blocks`, `liquidity_sweep`, `fair_value_gaps`) **y**
los 2 nuevos de este plan (`divergence`, `fractal`). `equal_high_low` usa su propio
`indicator_id="equal_high_low"` para ambas mitades de la lista concatenada (aunque
internamente reusa `convert_equal_high`/`convert_equal_low`, el `id` que se estampa
es el de la ruta que se llamó, no el del sub-conversor).

## Archivos a tocar (resumen)

- `pandas_luarix/_core/divergence.py` (nuevo) — función pura `detect_divergence`.
- `pandas_luarix/analysis/__init__.py` + `pandas_luarix/analysis/accessor.py` (nuevo)
  — `AnalysisAccessor` registrado como `df.analysis`.
- `pandas_luarix/smc/accessor.py` — agregar método `fractal(...)`.
- `pandas_luarix/__init__.py` — registrar `AnalysisAccessor`.
- `fastapi_server/schemas/catalog.py` — `group` acepta `"analysis"`.
- `fastapi_server/catalog/indicators.py` — 2 entradas nuevas (`divergence`, `fractal`).
- `fastapi_server/schemas/analysis.py` (nuevo) — `DivergenceRequest`.
- `fastapi_server/schemas/smc.py` — `FractalRequest`.
- `fastapi_server/routers/analysis.py` (nuevo) — `POST /analysis/divergence`.
- `fastapi_server/routers/smc.py` — `POST /smc/fractal` + pasar `indicator_id` en
  `liquidity_sweep`/`fair_value_gaps` (retrofit).
- `fastapi_server/routers/indicators.py` — pasar `indicator_id` en las 10 rutas
  existentes que no son bb50/stochastic (retrofit).
- `fastapi_server/routers/meta.py` — `GET /analysis`.
- `fastapi_server/services/visual_elements.py` — `convert_divergence`,
  `convert_fractal`, y `elements_response(elements, indicator_id=None)` (retrofit).
- `fastapi_server/main.py` — registrar el router `analysis`.

## Verificación

Sin mocks, contra Binance real, igual que el resto del framework:
1. `df.analysis.divergence(indicator=..., length=5)` ejecutado directo en Python
   contra un DataFrame sintético con una divergencia conocida a mano (igual que
   `pandas_luarix/tests/builders.py` hace para el resto de detectores) — confirmar
   que clasifica correctamente los 4 tipos.
2. `POST /analysis/divergence` con `source=slow_k` sobre BTCUSDT real → `elements`
   con `kind=line`, `sub_kind` en los 4 valores esperados, `direction` coherente
   (1 en los `*_bullish`, -1 en los `*_bearish`).
3. `df.smc.fractal(length=5)` contra el mismo tipo de fixture sintético — confirmar
   `top`/`bottom` correctos y `confirm_time` = vela `length` después del origen.
4. `POST /smc/fractal` sobre BTCUSDT real → `elements` con `kind=box`, `sub_kind` en
   {`bullish-fractal`,`bearish-fractal`}, `direction` presente.
5. `GET /analysis` → catálogo con la entrada `divergence`; `GET /smc` → ahora
   también incluye `fractal`.
6. Regresión: los endpoints existentes (`/indicators/*`, `/smc/liquidity-sweep`,
   `/smc/fair-value-gaps`, `/brokers/candles`) siguen respondiendo igual.
7. `id` estable: llamar dos veces seguidas el mismo `POST /indicators/swings` (u
   otra ruta SMC) con los mismos parámetros → los `id` de los elementos deben ser
   idénticos entre ambas respuestas. Confirmar que `bb50`/`stochastic-oscillator`
   NO traen `id` (no se les pasa `indicator_id`).

---

## Prompt para el backend (autocontenido, listo para copiar/pegar)

> Implementa 2 elementos nuevos en `pandas_luarix` y expónlos en `fastapi_server`,
> siguiendo el patrón ya establecido en el repo (accessors de pandas registrados
> vía `pd.api.extensions.register_dataframe_accessor`, funciones puras en `_core/`,
> catálogo mockeado en `fastapi_server/catalog/indicators.py`, contrato de
> respuesta `{"elements": [...]}` con 5 kinds: `marker`/`line`/`box`/`line_series`/
> `multiline_series`, conversión en `fastapi_server/services/visual_elements.py`).
>
> **1. Detector de divergencias genérico — grupo API nuevo `"analysis"`.**
> Núcleo puro en `pandas_luarix/_core/divergence.py::detect_divergence(high, low,
> indicator, length=5)`: detecta pivotes CONFIRMADOS solo de la serie `indicator`
> (reusando `find_pivots(indicator, indicator, length)` de `_core/pivots.py` — pasar
> la misma serie dos veces pivota una serie única). Para cada par CONSECUTIVO de
> pivotes bajos del indicador, compara precio (`low`) e indicador en esas 2 barras;
> para cada par consecutivo de pivotes altos, compara precio (`high`) e indicador.
> Clasifica: `regular_bullish` (precio LL + indicador HL), `hidden_bullish` (precio
> HL + indicador LL), `regular_bearish` (precio HH + indicador LH), `hidden_bearish`
> (precio LH + indicador HH). Exponer como accessor nuevo `df.analysis.divergence(
> indicator: pd.Series, length: int = 5) -> pd.DataFrame` (`pandas_luarix/analysis/
> accessor.py`, clase `AnalysisAccessor`, registrar en `pandas_luarix/__init__.py`).
> Columnas del resultado: `divergence_type`, `direction` (1 alcista/-1 bajista),
> `price`, `prior_time`, `prior_price`, `indicator_value`, `prior_indicator_value`.
> En la API: nuevo grupo `"analysis"` en `IndicatorMetadataOut.group`, ruta
> `GET /analysis` en `routers/meta.py`, entrada de catálogo `id="divergence"`,
> `kind="line"`. Ruta `POST /analysis/divergence` (`routers/analysis.py`, nuevo)
> con `DivergenceRequest(length=5, source: Literal["slow_k","fast_d"]="slow_k",
> stochastic_length=14, stochastic_d_length=3)` — hoy la única fuente disponible es
> el Stochastic Oscillator ya existente en `df.indicators`; el router calcula
> `stoch = df.indicators.stochastic_oscillator(...)` y pasa `stoch[source]` como
> `indicator` a `df.analysis.divergence`. `convert_divergence` en
> `visual_elements.py`: `kind="line"`, `sub_kind=divergence_type`,
> `time1=prior_time/price1=prior_price`, `time2=index/price2=price`,
> `direction=direction`.
>
> **2. Fractal — nuevo elemento del grupo API `"smc"`.**
> Método nuevo `fractal(length: int = 5, include_mitigated: bool = False) ->
> pd.DataFrame` en `pandas_luarix/smc/accessor.py` (misma clase `SMCAccessor` que ya
> tiene `swings`/`order_blocks`/etc.). Reutiliza `find_pivots` igual que
> `_swing_side`/`_order_block_side`, pero en vez de un marker de una vela, devuelve
> una **caja**: `top`/`bottom` = high/low de la vela de ORIGEN del pivote,
> horizontal desde esa vela hasta la vela de CONFIRMACIÓN (`length` velas después,
> columna `confirm_time`). `direction`: `1` (fractal alcista sobre un swing low) /
> `-1` (fractal bajista sobre un swing high). `mitigated`: mismo criterio que
> `_swing_side` (el cierre supera el nivel después de confirmado);
> `include_mitigated=False` filtra por defecto. Pensado como base para representar
> más adelante fractales estilo IPDA sin romper este contrato
> (top/bottom/horizontal/direction). En la API: entrada de catálogo `id="fractal"`,
> `group="smc"`, `kind="box"`, `endpoint="/smc/fractal"`. `FractalRequest(length=5,
> include_mitigated=False)` en `schemas/smc.py`. Ruta `POST /smc/fractal` en
> `routers/smc.py`. `convert_fractal` en `visual_elements.py`: `kind="box"`,
> `sub_kind = "bullish-fractal" if direction==1 else "bearish-fractal"`,
> `time1=index/price1=top`, `time2=confirm_time/price2=bottom`,
> `direction=direction`.
>
> Verificar ambos con un DataFrame sintético de fixture (igual que
> `pandas_luarix/tests/builders.py`) antes de probar contra Binance real, y
> confirmar que las rutas existentes no tienen regresión.
>
> **3. `id` estable en todos los elementos "SMC" (retrofit sobre lo ya existente +
> los 2 nuevos de arriba).** El frontend va a agregar un tab "Propiedades" al modal
> de configuración de cada elemento SMC (pivots, equal levels, BOS/CHoCH, order
> blocks, liquidity sweep, fair value gaps, fractal, divergence — **no** BB50/
> Stochastic) para que el usuario pueda editar a mano los valores del objeto
> detectado (ej. reasignar un swing a otra vela). Esa edición vive 100% en el
> frontend (sin base de datos nueva en el backend) — lo único que necesita del
> backend es que cada elemento traiga un `id` **determinístico y estable** entre
> refetches, para poder reasociar el override guardado tras recalcular. Cambio:
> `elements_response(elements: list[dict], indicator_id: str | None = None) ->
> dict` en `visual_elements.py` — si se pasa `indicator_id`, estampa
> `el["id"] = f"{indicator_id}:{el['sub_kind']}:{el.get('time', el.get('time1'))}"`
> en cada elemento antes de envolver en `{"elements": [...]}` (usa la vela de
> ORIGEN — `time` en marker, `time1` en line/box — porque es la parte estable del
> evento entre repintados). Actualizar las 12 rutas SMC ya existentes en
> `routers/indicators.py`/`routers/smc.py` para pasar su propio
> `indicator_id="<id de catálogo>"` (`swings`, `swing_high`, `swing_low`,
> `equal_high`, `equal_low`, `equal_high_low`, `bos_choch`, `bullish_order_block`,
> `bearish_order_block`, `order_blocks`, `liquidity_sweep`, `fair_value_gaps`) más
> las 2 nuevas (`divergence`, `fractal`) — un total de 14 rutas con `id`. Las rutas
> de `bb50`/`stochastic-oscillator` NO pasan `indicator_id` (quedan sin `id`,
> intencionalmente).
