# Servidor FastAPI para indicadores de `pandas_luarix`

## Contexto

El proyecto tiene una librería propia, `pandas_luarix/`, que extiende `pandas.DataFrame`
con accessors que exponen indicadores (originalmente `df.structure` para primitivas de
detección de patrones y `df.smc` para conceptos construidos sobre ellas — ver la
corrección de arquitectura más abajo, en el Anexo, sobre cómo evolucionó esto). Estos
indicadores hoy solo se pueden usar desde código Python/notebooks.

El usuario quiere exponerlos vía HTTP para que un frontend Next.js los consuma. Ya
existe una carpeta `fastapi_server/` vacía en la raíz del repo, creada como
placeholder para este trabajo. No hay base de datos: el catálogo de providers,
intervals e indicators se mockea como datos estáticos en código (como si fuera una
tabla). El cliente nunca manda el DataFrame — manda symbol/provider/interval/fechas y
el servidor arma el DataFrame llamando a Binance.

Decisiones ya tomadas con el usuario:
- El consumidor es Next.js → JSON body (no HTML form literal).
- Cada indicador tiene su propio modelo Pydantic tipado (no un dict genérico de
  params) — mejor validación y mejor doc/OpenAPI para generar tipos en el frontend.
- Cliente de Binance **sin API key** (los klines son endpoints públicos).

## Layout de archivos

```
fastapi_server/
├── __init__.py
├── main.py                     # FastAPI(), CORS, include_router(), entrypoint uvicorn
├── run.py                      # uvicorn.run("fastapi_server.main:app", reload=True)
├── dependencies.py              # Depends: get_binance_provider() -> BinanceMarketDataProvider (Client() sin keys, reusado)
├── errors.py                    # exception_handler(ValueError) -> 422; NoDataError -> 404
├── catalog/
│   ├── __init__.py
│   ├── providers.py              # mock: solo Binance
│   ├── intervals.py               # mock: intervalos por defecto de Binance
│   └── indicators.py              # catálogo hecho a mano: name/description/icon/category/group/endpoint/kind por cada indicador
├── schemas/
│   ├── __init__.py
│   ├── common.py                  # OHLCVRequestBase (symbol, provider, interval, start_date, end_date)
│   ├── catalog.py                  # ProviderOut, IntervalOut, IndicatorMetadataOut
│   ├── structure.py                 # 1 modelo Pydantic por indicador de df.smc (swings/order blocks/etc.) + bb50/stochastic
│   └── smc.py                        # 1 modelo Pydantic por indicador de liquidity_sweep/fair_value_gaps
├── services/
│   ├── __init__.py
│   ├── market_data_service.py        # fetch_ohlcv(...) -> pd.DataFrame vía BinanceMarketDataProvider
│   ├── serialization.py               # rows_response (usado solo por /brokers/candles tras el refactor de elementos)
│   └── visual_elements.py             # NUEVO (ver Anexo) — conversión a {"elements":[...]}
└── routers/
    ├── __init__.py
    ├── meta.py                        # GET /providers, /intervals, /indicators, /smc (catálogo)
    ├── indicators.py                   # POST /indicators/* -> df.smc.*  (ver Anexo para el contrato de respuesta actual)
    └── smc.py                          # POST /smc/* -> df.smc.*
```

## Catálogo de indicadores (mock "base de datos")

`IndicatorMetadataOut` (pydantic, en `schemas/catalog.py`):
`id`, `name`, `description`, `group` (`"indicator"|"smc"`), `category` (p.ej. "Pivots",
"Equal Levels", "Market Structure", "Order Blocks", "Liquidity", "Gaps"), `icon`
(nombre de icono **lucide-react** — es el set de iconos estándar en el ecosistema
Next.js/shadcn, así el frontend hace un lookup directo sin capa de traducción),
`endpoint` (ruta completa, p.ej. `/indicators/swings`), y `kind` (ver Anexo — el campo
`output_kind` original fue reemplazado por `kind` con los 5 valores del contrato de
elementos visuales).

Se define como una lista Python de instancias `IndicatorMetadataOut` en
`catalog/indicators.py`, una entrada por cada uno de los 12 métodos públicos que
producen indicadores de trading (`swings`, `swing_high`, `swing_low`, `equal_high`,
`equal_low`, `equal_high_low`, `bos_choch`, `bullish_order_block`,
`bearish_order_block`, `order_blocks`, `bb50`, `stochastic_oscillator` — todos
`group="indicator"`) más `liquidity_sweep`/`fair_value_gaps` (`group="smc"`).

`GET /indicators` devuelve el catálogo filtrado a `group=indicator`; `GET /smc`
devuelve el filtrado a `group=smc` (mismo modelo, dos rutas según el grupo — la
taxonomía de la API es un concepto de cara al cliente, independiente del namespace
interno de Python, ver Anexo).

`catalog/providers.py`: mock con un único provider `{"id": "binance", "name":
"Binance"}` + `assets`/`intervals` leídos de `fastapi_server/utils/data/binance.json`.
`catalog/intervals.py`: mock con los intervalos soportados por Binance (misma fuente
JSON): `1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M`.

## Schemas de request (uno por indicador)

Base compartida (`schemas/common.py`):
```python
class OHLCVRequestBase(BaseModel):
    symbol: str
    provider: Literal["binance"] = "binance"
    interval: str
    start_date: datetime
    end_date: datetime
```
Cada indicador hereda de `OHLCVRequestBase` y agrega sus propios parámetros, con los
mismos defaults y tipos que el método del accessor correspondiente
(`pandas_luarix/smc/accessor.py`, `pandas_luarix/indicators/accessor.py`). Los enums de
`pandas_luarix._core.enums` (`EqualLevelMethod`, `ObMitigation`, `VolatilityMethod`,
`LiquidityLevels`) se usan directamente como tipo de campo (son `str, Enum`, Pydantic
v2 los soporta nativamente y los renderiza como enum en el OpenAPI/Swagger).

Ejemplo (`schemas/structure.py`):
```python
class SwingsRequest(OHLCVRequestBase):
    length: int = 50

class EqualHighRequest(OHLCVRequestBase):
    length: int = 3
    method: EqualLevelMethod = EqualLevelMethod.ATR_PIVOT
    equal_threshold: float = 0.1
    atr_period: int = 200
    tolerance_pct: float = 0.003
    include_mitigated: bool = False
```
Ejemplo (`schemas/smc.py`):
```python
class LiquiditySweepRequest(OHLCVRequestBase):
    length: int = 50
    levels: LiquidityLevels = LiquidityLevels.SWINGS
    method: EqualLevelMethod = EqualLevelMethod.ATR_PIVOT
    equal_threshold: float = 0.1
    atr_period: int = 200
    tolerance_pct: float = 0.003
    max_confirmation_bars: int = 1
```

No se tipan modelos de respuesta por indicador (las columnas varían por método); ver
Anexo para la forma actual de la respuesta (`{"elements": [...]}`).

## Rutas

Metadata:
- `GET /providers` → `list[ProviderOut]`
- `GET /intervals` → `list[IntervalOut]`
- `GET /indicators` → catálogo `group=indicator`
- `GET /smc` → catálogo `group=smc`

Ejecutar indicador, `/indicators/*`:
`POST /indicators/swings`, `/swing-high`, `/swing-low`, `/equal-high`, `/equal-low`,
`/equal-high-low`, `/bos-choch`, `/bullish-order-block`, `/bearish-order-block`,
`/order-blocks`, `/bb50`, `/stochastic-oscillator`.

Ejecutar indicador, `/smc/*`:
`POST /smc/liquidity-sweep`, `/smc/fair-value-gaps`.

(slugs con guiones en la URL; el `id` interno puede quedar en snake_case, el
`endpoint` del catálogo guarda el string exacto con guiones para que el frontend no
tenga ambigüedad.)

## Flujo request → DataFrame → accessor → JSON

`services/market_data_service.py::fetch_ohlcv(symbol, provider, interval, start_date, end_date)`:
1. Valida `provider` contra `catalog/providers.py` e `interval` contra
   `catalog/intervals.py` (si no están → 404).
2. Usa el `BinanceMarketDataProvider` inyectado por `dependencies.py` (construido una
   sola vez con `binance.Client()` sin keys) y llama
   `get_historical_candles(symbol, interval, start=start_date, end=end_date, format=DataFormat.OHLCV)`
   (`app/brokers/market_data/binance.py`).
3. El DataFrame que devuelve tiene columnas `date, open, high, low, close, volume,
   close_time` con índice `RangeIndex` — hacer `df = df.set_index("date")` antes de
   pasarlo a los accessors, para que el índice temporal quede disponible al
   serializar (los accessors solo validan que existan columnas `open/high/low/close`,
   no exigen índice datetime, pero lo preservan en el resultado vía `iloc`/`loc`).
4. Si el DataFrame queda vacío → `NoDataError` (404).

Handler de router (p.ej. `POST /indicators/swings`):
1. FastAPI valida el body contra `SwingsRequest`.
2. `df = fetch_ohlcv(request.symbol, request.provider, request.interval, request.start_date, request.end_date)`.
3. `kwargs = request.model_dump(exclude={"symbol","provider","interval","start_date","end_date"})`.
4. `result = df.smc.swings(**kwargs)` (deja propagar `ValueError` — lo captura el handler global).
5. Ver Anexo para cómo se convierte `result` a la respuesta final (`{"elements": [...]}`).

## Manejo de errores

- Provider desconocido → `404` (`Unknown provider: {provider}`).
- Interval desconocido → `404` (`Unknown interval: {interval}`).
- Symbol inválido / Binance sin datos → capturar `BinanceAPIException` de
  `binance.exceptions` y `df.empty` → `404` (`No data returned from Binance for
  {symbol}/{interval}`).
- `ValueError` del accessor (parámetros inválidos, filas insuficientes por
  `require_min_rows`/`check_positive_int`/etc.) → handler global en `errors.py`
  (`@app.exception_handler(ValueError)`) → `422` con `str(exc)` como detail. Así los
  routers no necesitan try/except repetido.
- Ruta de indicador inexistente → 404 nativo de FastAPI (las rutas están declaradas
  explícitamente, no hay `/indicators/{id}` catch-all).

## Dependencias nuevas

`fastapi` y `uvicorn` no estaban en `requirements.txt` (raíz, **UTF-16 LE con BOM** —
artefacto de `pip freeze` en PowerShell). Ya insertados manteniendo el encoding exacto
(`fastapi==0.139.0` antes de `fastjsonschema==2.21.2`; `uvicorn==0.51.0` después de
`urllib3==2.7.0`). `pydantic==2.13.4` ya estaba instalado.

`main.py` agrega `CORSMiddleware` permitiendo el origen de desarrollo de Next.js
(`http://localhost:3000`), y un bloque `if __name__ == "__main__": uvicorn.run(...)`.

## Verificación (sesión 1 — ya ejecutada)

1. `uvicorn fastapi_server.main:app --reload` y abrir `http://localhost:8000/docs`.
2. Confirmar que `/providers`, `/intervals`, `/indicators`, `/smc` devuelven los
   mocks, y que las rutas POST muestran bodies tipados correctamente (enums como
   dropdown, defaults iguales a los del accessor).
3. `POST /indicators/swings` con `BTCUSDT`, rango de fechas corto reciente,
   `interval=1h`, `length` por defecto → confirmar respuesta con `time` en ISO y
   sin `NaN` literal (debe ser `null` válido).
4. Forzar errores: symbol inexistente (404), interval no soportado (404),
   `length=0` o negativo (422 con mensaje del accessor), rango de fechas insuficiente
   para `atr_period=200` (422 `require_min_rows`).

## Notas para `docs/plans/` y `docs/plans/bugs.md`

Por convención del repo (`CLAUDE.md`), al ejecutar este plan se debe:
- Guardar una copia de este plan en `docs/plans/fastapi_server.md`.
- Si aparece algún hallazgo o decisión no obvia durante la implementación (p.ej. algo
  sobre el encoding de `requirements.txt`, comportamiento real de
  `get_historical_candles` con símbolos inválidos, los bugs de la consolidación de
  accessors descritos en el Anexo, etc.), registrarlo en `docs/plans/bugs.md` para no
  tener que re-analizarlo después.

---

# Anexo: contrato de "elementos visuales" para `/markets/chart` (sesión 2)

## Contexto

El frontend Next.js (`/markets/chart`) solo sabe dibujar **5 tipos de objeto** sobre
el chart (`marker`, `line`, `box`, `line_series`, `multiline_series`). Hoy cada uno de
los 14 endpoints de indicadores devuelve filas crudas de pandas (`{"data": [...],
"count": N}`, o el envelope especial de `equal-high-low`), y el frontend tiene un
conversor a mano por cada indicador (`structure-shapes.ts`, `indicator-series.ts`).
El objetivo es mover esa conversión al backend: cada endpoint pasa a devolver
directamente `{"elements": [...]}`, y el frontend queda con un único `switch` sobre
`el.kind`, sin lógica por indicador. El estilo visual (color, grosor, etc.) sigue
siendo 100% responsabilidad del frontend, indexado por `sub_kind` (o por `lines[].key`
en `multiline_series`) — el backend solo entrega geometría/valores.

Decisiones ya confirmadas con el usuario:
- Reemplazo completo del formato de respuesta (no coexiste con `{"data","count"}`; no
  hay query param de compatibilidad).
- `fair_value_gaps` usa `sub_kind` `"bullish-fvg"`/`"bearish-fvg"` (paralelo a
  `"bullish-ob"`/`"bearish-ob"` de order blocks).

**Corrección importante de arquitectura (confirmada con el usuario):** `pandas_luarix`
ya NO tiene un accessor `df.structure` separado — la carpeta `pandas_luarix/structure/`
fue eliminada y todos sus métodos (`swings`, `swing_high`, `swing_low`, `equal_high`,
`equal_low`, `equal_high_low`, `bos_choch`, `bullish_order_block`,
`bearish_order_block`, `order_blocks`) se consolidaron dentro de `SMCAccessor`
(`pandas_luarix/smc/accessor.py`), junto a `liquidity_sweep`/`fair_value_gaps`. Hoy
**todo** se llama vía `df.smc.*` (verificado con `hasattr`: `df.structure` ya no
existe, `df.smc` expone los 12 métodos). `df.indicators` (bb50/stochastic) no cambia.

**Bugs reales encontrados en la consolidación (deben arreglarse antes de que el
contrato de elementos funcione — confirmado ejecutando cada método directamente
contra un DataFrame sintético):**
1. `pandas_luarix/smc/accessor.py` no importa `check_positive_float` de
   `_core.validation` (el import actual solo trae `check_non_negative_float`,
   `check_positive_int`, `require_min_rows`, `validate_ohlc_columns`). Esto rompe con
   `NameError` a **6 de los 12 métodos**: `equal_high`, `equal_low`,
   `equal_high_low`, `bullish_order_block`, `bearish_order_block`, `order_blocks`.
   Fix: agregar `check_positive_float` al import existente.
2. `liquidity_sweep` todavía instancia `structure = StructureAccessor(df)` (línea 64)
   para llamar a `.swing_high()`/`.swing_low()`/`.equal_high()`/`.equal_low()` — esa
   clase ya no existe (fue eliminada junto con `pandas_luarix/structure/`), así que
   `liquidity_sweep` rompe con `NameError: name 'StructureAccessor' is not defined`.
   Fix: como esos métodos ahora viven en la misma clase (`SMCAccessor`), reemplazar
   `structure = StructureAccessor(df)` por `structure = self` (o llamar directamente
   `self.swing_high(...)`/`self.equal_high(...)` sin la variable intermedia).

Confirmado con una prueba directa (script ad-hoc, no parte del código): con estos 2
fixes, los 12 métodos de `df.smc` deben funcionar; sin ellos, solo `swings`,
`swing_high`, `swing_low`, `bos_choch` y `fair_value_gaps` funcionan hoy (5 de 12) —
`equal_high`, `equal_low`, `equal_high_low`, `bullish_order_block`,
`bearish_order_block`, `order_blocks` y `liquidity_sweep` están rotos en este momento.
Estos 2 fixes son un prerequisito de este anexo (sin ellos, 7 de los 12 endpoints de
indicador devolverían 422 con un `NameError` disfrazado de `ValueError`... en realidad
`NameError` no hereda de `ValueError`, así que hoy esos 7 endpoints devuelven `500`
sin manejar, no `422` — otra razón para arreglarlo primero).

## Los 5 tipos de objeto y su regla de conversión

| kind | Forma | Quién lo produce | Regla de conversión desde el DataFrame/lista de pandas_luarix |
|---|---|---|---|
| `marker` | `{kind, sub_kind, time, price}` | `swings`, `swing_high`, `swing_low` | Una fila → un marker. `swings` decide `sub_kind`/`price` según `row.swing_type` (`"high"`→`price=row.high`, `"low"`→`price=row.low`); `swing_high`/`swing_low` son fijos (`price=row.high`/`row.low`). |
| `line` | `{kind, sub_kind, time1, price1, time2, price2}` (+ `direction` solo si aplica) | `equal_high`, `equal_low`, `equal_high_low`, `bos_choch`, `liquidity_sweep` | Ver detalle por indicador abajo. **`bos_choch` y `liquidity_sweep` NO llevan `direction`.** |
| `box` | `{kind, sub_kind, time1, price1, time2, price2, direction}` (+ `filled` solo en FVG) | `bullish_order_block`, `bearish_order_block`, `order_blocks`, `fair_value_gaps` | `time1=index, price1=row.top, time2=row.close_time, price2=row.bottom`. `direction` siempre presente aquí. |
| `line_series` | `{kind, data:[{time,value}]}` | (ninguno hoy — solo debe existir como valor válido del `Literal` de catálogo) | — |
| `multiline_series` | `{kind, lines:[{key,label,data:[{time,value}]}], ...extra}` | `bb50`, `stochastic_oscillator` | Una lista de 1 elemento. `data` de cada línea omite (no emite `null`) las filas con NaN durante el warm-up. |

### Detalle de conversión por indicador (campos exactos, no inventar otros nombres)

- **`swings`** (`df.smc.swings`, columna `swing_type`) → marker por fila:
  `sub_kind="swing-high"` + `price=row.high` si `swing_type=="high"`; si no,
  `sub_kind="swing-low"` + `price=row.low`.
- **`swing_high`** (`df.smc.swing_high`) → marker por fila: `sub_kind="swing-high"`,
  `price=row.high`.
- **`swing_low`** (`df.smc.swing_low`) → marker por fila: `sub_kind="swing-low"`,
  `price=row.low`.
- **`equal_high`** (`df.smc.equal_high` → `list[pd.DataFrame]`, cada grupo N filas
  con `high` casi igual) → una `line` por grupo: `time1`/`price1` = primera fila del
  grupo (`index`, `row.high`); `time2`/`price2` = última fila del grupo. `sub_kind="equal-high"`.
- **`equal_low`** → espejo de `equal_high` usando `low`, `sub_kind="equal-low"`.
- **`equal_high_low`** (`df.smc.equal_high_low` → `tuple[list[df], list[df]]`) →
  **una sola lista `elements` plana** que junta las líneas de `equal_high` +
  `equal_low` (cada una ya con su propio `sub_kind`) — cambio de comportamiento real
  respecto al envelope `{"equal_high":[...], "equal_low":[...]}` de hoy, confirmado
  con el usuario. No existe una función de conversión propia para este caso: el
  router llama a los conversores de `equal_high`/`equal_low` y concatena las listas.
- **`bos_choch`** (`df.smc.bos_choch`, columnas `structure_type`, `close`,
  `close_time`) → `line` por fila: `sub_kind = "bos" if structure_type=="BOS" else "choch"`;
  `time1=index, price1=row.close, time2=row.close_time, price2=row.close` (tick
  horizontal de una sola vela). **Sin `direction`.**
- **`liquidity_sweep`** (`df.smc.liquidity_sweep`, columnas `swept_level`, `close_time`)
  → `line` por fila: `sub_kind="liquidity-sweep"`, `time1=index, price1=row.swept_level,
  time2=row.close_time, price2=row.swept_level`. **Sin `direction`.**
- **`bullish_order_block`** (`df.smc.bullish_order_block`, columnas `top`,
  `bottom`, `close_time`, sin columna `direction`) → `box` por fila:
  `sub_kind="bullish-ob"`, `direction=1` (fijo, no viene de una columna).
- **`bearish_order_block`** → espejo: `sub_kind="bearish-ob"`, `direction=-1` (fijo).
- **`order_blocks`** (`df.smc.order_blocks`, SÍ tiene columna `direction`) → `box`
  por fila: `sub_kind = "bullish-ob" if row.direction==1 else "bearish-ob"`,
  `direction=row.direction` (leído de la columna, a diferencia de los dos anteriores).
- **`fair_value_gaps`** (`df.smc.fair_value_gaps`, columnas `direction`, `filled`) →
  `box` por fila: `sub_kind = "bullish-fvg" if row.direction==1 else "bearish-fvg"`,
  `direction=row.direction`, `filled=bool(row.filled)`.
- **`bb50`** (`df.indicators.bb50`, columnas `lower`/`middle`/`upper`, todas las velas)
  → lista de **un** `multiline_series`: `lines=[{"key":"lower","label":"Lower",...},
  {"key":"middle","label":"Base",...}, {"key":"upper","label":"Upper",...}]`, cada
  `data` omitiendo filas NaN (warm-up).
- **`stochastic_oscillator`** (`df.indicators.stochastic_oscillator`, columnas
  `slow_k`/`fast_d`/`upper_trigger`/`lower_trigger`) → lista de **un**
  `multiline_series`: `lines=[{"key":"slowK","label":"Slow K",...},
  {"key":"fastD","label":"Fast D",...}]` (**camelCase**, distinto de `bb50`) +
  campos raíz `upper_trigger`/`lower_trigger` (escalares, tomados de cualquier fila —
  son constantes repetidas) fuera de `lines`.

## Archivos a cambiar

- **`fastapi_server/services/visual_elements.py`** (nuevo) — helpers compartidos
  (`_iso`, `_marker`, `_line`, `_box`, `_series_points`, `_multiline_element`) + una
  función `convert_<indicador>(...)` por cada uno de los 13 indicadores reales (no se
  crea `convert_equal_high_low`, ver arriba) + `elements_response(elements) -> {"elements": elements}`
  (sin `count` — el contrato objetivo es literalmente `{"elements": [...]}`).
- **`fastapi_server/services/serialization.py`** — se recorta, no se borra: mantiene
  `_to_json_safe`, `dataframe_to_rows`, `rows_response` (siguen siendo usados por
  `routers/brokers.py::get_candles`, que queda fuera de este refactor — las velas
  crudas de `/brokers/candles` no cambian). Se eliminan `groups_to_rows`,
  `grouped_rows_response`, `grouped_rows_pair_response` (confirmado por grep: sin más
  usos tras migrar `routers/indicators.py`).
- **`fastapi_server/schemas/catalog.py`** — `IndicatorMetadataOut.output_kind` se
  reemplaza por `kind: Literal["marker","line","box","line_series","multiline_series"]`.
- **`fastapi_server/catalog/indicators.py`** — cada entrada cambia `output_kind=` por
  `kind=` según la tabla de arriba (swings/swing_high/swing_low→`marker`;
  equal_high/equal_low/equal_high_low/bos_choch/liquidity_sweep→`line`;
  bullish_order_block/bearish_order_block/order_blocks/fair_value_gaps→`box`;
  bb50/stochastic_oscillator→`multiline_series`). De paso, al reescribir el archivo,
  dejar `group="indicator"` en los 10 items que no son smc y `group="smc"` en
  `liquidity_sweep`/`fair_value_gaps` (única taxonomía correcta ya validada
  end-to-end en la sesión anterior), y `endpoint` de `liquidity_sweep`/
  `fair_value_gaps` apuntando a `/smc/liquidity-sweep`/`/smc/fair-value-gaps`
  (coincidiendo con el prefijo real `APIRouter(prefix="/smc")` de `routers/smc.py`).
- **`fastapi_server/routers/indicators.py`** — cada ruta pasa a llamar a `df.smc.*`
  (para los 10 métodos que antes eran de `structure`) o `df.indicators.*` (para
  `bb50`/`stochastic_oscillator`), y envuelve el resultado con el `convert_*` +
  `elements_response` correspondientes, en vez de `rows_response`/`grouped_rows_response`/
  `grouped_rows_pair_response`.
- **`fastapi_server/routers/smc.py`** — mismo cambio de envoltorio
  (`convert_liquidity_sweep`/`convert_fair_value_gaps` + `elements_response`); las
  llamadas a `df.smc.*` ya son correctas.
- **`pandas_luarix/smc/accessor.py`** — los 2 fixes descritos arriba (import de
  `check_positive_float`, y `structure = self` en vez de `StructureAccessor(df)`)
  son prerequisito antes de que el resto del refactor tenga sentido.
- **Sin cambios**: `schemas/structure.py`, `schemas/smc.py`, `schemas/common.py`,
  `services/market_data_service.py`, `errors.py`, `routers/brokers.py`,
  `routers/meta.py` (solo el `Literal`/valores de `catalog/indicators.py` cambian, la
  ruta en sí no).

## Forma de las funciones de conversión (`visual_elements.py`)

Firma uniforme: reciben lo que el accessor devuelve tal cual (un `pd.DataFrame`, o
`list[pd.DataFrame]` para `equal_high`/`equal_low`) y devuelven `list[dict]` JSON-safe
(reusar `_to_json_safe`-equivalente para Timestamps/NaN/numpy igual que hoy). No se
introducen modelos Pydantic de respuesta por kind — se mantiene la convención actual
del código (routers sin `response_model`, dicts sueltos) porque una unión discriminada
de 5 formas con campos opcionales distintos por variante añadiría complejidad sin
que se haya pedido tipado estricto de la respuesta.

## Verificación

Sin mocks — levantar el servidor y probar contra Binance real, un caso por cada
familia de conversión:
1. `POST /indicators/swings` → cada elemento `kind=marker`, `sub_kind` en
   {`swing-high`,`swing-low`}.
2. `POST /indicators/equal-high` → `kind=line`, `sub_kind=equal-high`, sin `direction`.
3. `POST /indicators/equal-high-low` → una sola lista `elements` con ambos sub_kind
   mezclados (ya no hay claves `equal_high`/`equal_low` en la raíz).
4. `POST /indicators/bos-choch` → `kind=line`, `price1==price2`, `time1 != time2`, sin `direction`.
5. `POST /smc/liquidity-sweep` → mismo patrón que bos-choch, `sub_kind=liquidity-sweep`, sin `direction`.
6. `POST /indicators/order-blocks` → `kind=box`, `direction` presente (1/-1 según fila),
   `sub_kind` acorde.
7. `POST /indicators/bullish-order-block` → todos los elementos con `direction=1` fijo.
8. `POST /smc/fair-value-gaps` → `kind=box`, `sub_kind` en {`bullish-fvg`,`bearish-fvg`},
   `direction` y `filled` presentes.
9. `POST /indicators/bb50` → una lista de 1 `multiline_series`, `lines[].key` en
   {`lower`,`middle`,`upper`}, sin `null` en `data` (las filas de warm-up simplemente
   no aparecen).
10. `POST /indicators/stochastic-oscillator` → `lines[].key` en {`slowK`,`fastD`}
    (camelCase), más `upper_trigger`/`lower_trigger` a nivel raíz del elemento.
11. Regresión: `POST /brokers/candles` sigue devolviendo `{"data":[...],"count":N}`
    sin cambios (confirma que `rows_response` sobrevive intacto para ese endpoint).
12. `GET /indicators` y `GET /smc` — confirmar que cada entrada trae `kind` (no
    `output_kind`) con el valor correcto, y que los 12 items de `group="indicator"` +
    2 de `group="smc"` aparecen donde corresponde.
