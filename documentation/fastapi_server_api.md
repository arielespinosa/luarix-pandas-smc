# API de indicadores (`fastapi_server`)

Servidor FastAPI que expone los indicadores de `pandas_luarix` (accessors `df.smc`,
`df.indicators` y `df.analysis`) vía HTTP, pensado para ser consumido desde un
frontend Next.js (`/markets/chart`). No usa base de datos: providers, intervals e
indicators son catálogos mockeados en código (`fastapi_server/catalog/`).

La API tiene **3 grupos**: `indicator` (BB50, Stochastic Oscillator), `smc`
(swings, equal levels, BOS/CHoCH, order blocks, liquidity sweep, fair value gaps,
fractal) y `analysis` (divergencia genérica — primer y único elemento hoy). Cada
uno se lista con `GET /indicators`, `GET /smc`, `GET /analysis` respectivamente.

- **Levantar el servidor**: `python -m fastapi_server.run` (o `uvicorn fastapi_server.main:app --reload`).
- **Swagger UI**: `http://localhost:8000/docs`.
- **CORS**: habilitado para `http://localhost:3000`.

Todas las rutas de "ejecutar indicador" son `POST` y reciben un body JSON con los
campos comunes (`symbol`, `provider`, `interval`, `start_date`, `end_date`) más los
parámetros propios del indicador (mismos nombres/defaults que el método del accessor
en `pandas_luarix`). El servidor descarga las velas de Binance (sin API key, endpoints
públicos) y corre el indicador sobre ellas.

## El contrato de respuesta: `{"elements": [...]}`

El frontend (`/markets/chart`, `lightweight-charts`) solo sabe dibujar **5 tipos de
objeto**. Cada endpoint de indicador devuelve una lista de estos objetos ya
convertidos — el cliente no necesita saber nada del indicador específico, solo hace
`switch` sobre `kind`. El estilo visual (color, grosor, línea punteada, etc.) es
100% responsabilidad del frontend, indexado por `sub_kind` (o por `lines[].key` en
`multiline_series`) — el backend nunca manda estilo, solo geometría/valores.

| `kind` | Forma | Quién lo produce |
|---|---|---|
| `marker` | `{kind, sub_kind, time, price}` | `swings`, `swing_high`, `swing_low` |
| `line` | `{kind, sub_kind, time1, price1, time2, price2}` (+ `direction` si aplica) | `equal_high`, `equal_low`, `equal_high_low`, `bos_choch`, `liquidity_sweep`, `divergence` |
| `box` | `{kind, sub_kind, time1, price1, time2, price2, direction}` (+ `filled` en FVG) | `bullish_order_block`, `bearish_order_block`, `order_blocks`, `fair_value_gaps`, `fractal` |
| `line_series` | `{kind, data:[{time,value}]}` | (ninguno hoy, reservado) |
| `multiline_series` | `{kind, lines:[{key,label,data:[{time,value}]}], ...extra}` | `bb50`, `stochastic_oscillator` |

**`id` estable** (para el tab "Propiedades" del frontend): todo elemento producido
por un método de `df.smc`/`df.analysis` (es decir, todo lo de arriba excepto
`bb50`/`stochastic_oscillator`) trae un campo `id` determinístico:
`"<indicator_id>:<sub_kind>:<vela de origen>"` — mismo evento detectado ⇒ mismo
`id` entre refetches/repaints, para que el frontend pueda reasociar un override
manual del usuario (mover el objeto a otra vela) después de recalcular. La edición
en sí vive 100% en el frontend, el backend no persiste nada.

Notas importantes:
- `direction` (`1` alcista / `-1` bajista) **solo** aparece en `order_blocks` y
  `fair_value_gaps` (los combinados) — `bos_choch` y `liquidity_sweep` no lo llevan,
  aunque su indicador subyacente sí tenga un concepto de dirección.
- `bullish_order_block`/`bearish_order_block` (las rutas de un solo lado) sí llevan
  `direction` pero **fijo** (`1`/`-1` siempre, no leído de una columna) — solo
  `order_blocks` (combinado) lo lee de la fila.
- `fair_value_gaps` además lleva `filled: bool`.
- `equal_high_low` devuelve **una sola lista `elements`** mezclando líneas
  `sub_kind="equal-high"` y `sub_kind="equal-low"` — no hay claves separadas en la
  raíz.
- `multiline_series` (`bb50`, `stochastic_oscillator`) es una lista de **un solo
  elemento**; `data` de cada línea omite (no emite `null`) las filas del período de
  warm-up del indicador.
- `bb50` usa claves `lower`/`middle`/`upper`; `stochastic_oscillator` usa
  `slowK`/`fastD` (**camelCase**, distinto de bb50) más `upper_trigger`/
  `lower_trigger` como campos a nivel raíz del elemento (son escalares constantes,
  no series).

## Errores comunes

| Situación | Status | Body |
|---|---|---|
| `provider` no es `"binance"` | 422 | error de validación de Pydantic (`Literal["binance"]`) |
| `interval` no está en el catálogo mockeado | 404 | `{"detail": "Unknown interval: ..."}` |
| `symbol` inválido o Binance no devuelve velas | 404 | `{"detail": "No data returned from Binance for ..."}` |
| Parámetro inválido (ej. `length=0`) | 422 | `{"detail": "'length' must be a positive int, got 0."}` |
| Rango de fechas insuficiente para el `atr_period`/`length` pedido | 422 | `{"detail": "... requires at least N rows, got M."}` |
| `broker` desconocido (`/brokers/candles`) | 422 | error de validación de Pydantic (enum `"binance"`/`"bitunix"`) |
| No se pudo inicializar el broker o falló la llamada al proveedor (`/brokers/candles`) | 502 | `{"detail": "Could not initialize broker '...': ..."}` / `{"detail": "Error fetching candles from '...': ..."}` |

---

## Metadata

### `GET /providers`

Lista de providers disponibles (mock: solo Binance), con los activos e intervalos que
maneja cada uno. Ambos se leen de `fastapi_server/utils/data/binance.json`
(`{"intervals": [...], "symbols": [...]}` — fuente única también para `GET /intervals`).

**Respuesta** (truncada, son 1000 assets para Binance)
```json
[
  {
    "id": "binance",
    "name": "Binance",
    "description": "Datos de mercado spot de Binance (klines públicos, sin autenticación).",
    "assets": ["ETHBTC", "LTCBTC", "BNBBTC", "NEOBTC", "QTUMETH", "..."],
    "intervals": ["1s", "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
  }
]
```

### `GET /intervals`

Intervalos soportados (los códigos vienen de `binance.json` → `intervals`; el
`label` en español se mapea a mano en `fastapi_server/catalog/intervals.py`).

**Respuesta**
```json
[
  { "id": "1s", "label": "1 segundo" },
  { "id": "1m", "label": "1 minuto" },
  { "id": "4h", "label": "4 horas" },
  { "id": "1d", "label": "1 día" },
  "..."
]
```

### `GET /indicators`

Catálogo del grupo `indicator` (12 items — pivots/BOS/order blocks + BB50/Stochastic).

**Respuesta**
```json
[
  {
    "id": "swings", "name": "Swings",
    "description": "Pivotes confirmados (máximos y mínimos), marcados en su vela de origen.",
    "group": "indicator", "category": "Pivots", "icon": "waypoints",
    "endpoint": "/indicators/swings", "kind": "marker"
  },
  {
    "id": "equal_high", "name": "Equal Highs",
    "description": "Grupos de máximos dentro de una tolerancia entre sí.",
    "group": "indicator", "category": "Equal Levels", "icon": "equal",
    "endpoint": "/indicators/equal-high", "kind": "line"
  },
  {
    "id": "order_blocks", "name": "Order Blocks",
    "description": "Order blocks alcistas y bajistas combinados, con columna de dirección.",
    "group": "indicator", "category": "Order Blocks", "icon": "layers",
    "endpoint": "/indicators/order-blocks", "kind": "box"
  },
  {
    "id": "bb50", "name": "Bollinger Bands 50",
    "description": "Bandas de Bollinger (media móvil + desviación estándar) sobre el cierre.",
    "group": "indicator", "category": "Volatility", "icon": "activity",
    "endpoint": "/indicators/bb50", "kind": "multiline_series"
  }
]
```
(lista abreviada — son 12 entradas en total: `swings`, `swing_high`, `swing_low`,
`equal_high`, `equal_low`, `equal_high_low`, `bos_choch`, `bullish_order_block`,
`bearish_order_block`, `order_blocks`, `bb50`, `stochastic_oscillator`.)

### `GET /smc`

Catálogo del grupo `smc` (2 items).

**Respuesta**
```json
[
  {
    "id": "liquidity_sweep", "name": "Liquidity Sweep",
    "description": "Mecha que rompe un swing o equal level y cuyo cierre vuelve dentro (caza de stops).",
    "group": "smc", "category": "Liquidity", "icon": "crosshair",
    "endpoint": "/smc/liquidity-sweep", "kind": "line"
  },
  {
    "id": "fair_value_gaps", "name": "Fair Value Gaps",
    "description": "Gaps clásicos de 3 velas, opcionalmente filtrados por tamaño mínimo relativo al ATR.",
    "group": "smc", "category": "Gaps", "icon": "square-dashed",
    "endpoint": "/smc/fair-value-gaps", "kind": "box"
  }
]
```

---

## Indicadores del grupo `indicator` (`/indicators/*`)

### `POST /indicators/swings` — `marker`

Parámetros propios: `length` (int, default `50`).

**Request**
```json
{ "symbol": "BTCUSDT", "interval": "1h", "start_date": "2024-01-01T00:00:00", "end_date": "2024-03-01T00:00:00", "length": 50 }
```

**Response**
```json
{
  "elements": [
    { "kind": "marker", "sub_kind": "swing-low", "time": "2024-01-01T05:00:00+00:00", "price": 42180.77 },
    { "kind": "marker", "sub_kind": "swing-high", "time": "2024-01-02T12:00:00+00:00", "price": 45879.63 }
  ]
}
```

### `POST /indicators/swing-high` / `POST /indicators/swing-low` — `marker`

Parámetros propios: `length` (int, default `50`), `include_mitigated` (bool, default `false`).
`sub_kind` fijo (`"swing-high"`/`"swing-low"`), `price` = `high`/`low` de la vela.

### `POST /indicators/equal-high` / `POST /indicators/equal-low` — `line`

Parámetros propios: `length` (int, default `3`), `method`, `equal_threshold` (float,
default `0.1`), `atr_period` (int, default `200`), `tolerance_pct` (float, default
`0.003`), `include_mitigated` (bool, default `false`).

Cada grupo detectado (2+ velas con nivel casi igual) se convierte en **una línea**:
`time1/price1` = primera vela del grupo, `time2/price2` = última vela del grupo.

**Response**
```json
{
  "elements": [
    { "kind": "line", "sub_kind": "equal-high", "time1": "2024-03-27T00:00:00+00:00", "price1": 71769.54, "time2": "2024-04-08T00:00:00+00:00", "price2": 72797.99 }
  ]
}
```

### `POST /indicators/equal-high-low` — `line` (mezcla ambos sub_kind)

Mismos parámetros que `equal-high`/`equal-low`. Devuelve **una sola lista `elements`**
con líneas `sub_kind="equal-high"` y `sub_kind="equal-low"` mezcladas — a diferencia
de versiones anteriores de este endpoint, no hay claves `equal_high`/`equal_low`
separadas en la raíz.

### `POST /indicators/bos-choch` — `line` (sin `direction`)

Parámetros propios: `length` (int, default `50`), `confluence_filter` (bool, default `false`).
Una línea por evento: tick horizontal de una sola vela a la altura del cierre
(`time1`=apertura de la vela, `time2`=`close_time`, `price1==price2==close`).
`sub_kind` = `"bos"` o `"choch"`.

**Response**
```json
{
  "elements": [
    { "kind": "line", "sub_kind": "bos", "time1": "2024-01-03T14:00:00+00:00", "price1": 42179.99, "time2": "2024-01-03T14:59:59.999000+00:00", "price2": 42179.99 }
  ]
}
```

### `POST /indicators/bullish-order-block` / `POST /indicators/bearish-order-block` — `box`

Parámetros propios: `length` (int, default `50`), `ob_mitigation`, `atr_period` (int,
default `200`), `high_vol_multiplier` (float, default `2.0`), `volatility_method`,
`confluence_filter` (bool, default `false`), `include_mitigated` (bool, default `false`).

`sub_kind`/`direction` **fijos** por ruta (`"bullish-ob"`/`1` o `"bearish-ob"`/`-1` —
no se leen de ninguna columna, ya que estas rutas son de un solo lado).

**Response** (`bullish-order-block`)
```json
{
  "elements": [
    { "kind": "box", "sub_kind": "bullish-ob", "time1": "2023-03-10T00:00:00+00:00", "price1": 20367.78, "time2": "2023-03-10T23:59:59.999000+00:00", "price2": 19549.09, "direction": 1 }
  ]
}
```

### `POST /indicators/order-blocks` — `box` (`direction` leído de la fila)

Mismos parámetros que `bullish-order-block`. Combina ambos lados; a diferencia de las
rutas individuales, aquí `sub_kind`/`direction` sí se determinan por fila
(`direction==1` → `"bullish-ob"`, `direction==-1` → `"bearish-ob"`).

### `POST /indicators/bb50` — `multiline_series`

Parámetros propios: `length` (int, default `50`), `std` (float, default `2.0`).
Una fila por vela; `data` de cada línea omite las velas de warm-up (no emite `null`).

**Response**
```json
{
  "elements": [
    {
      "kind": "multiline_series",
      "lines": [
        { "key": "lower", "label": "Lower", "data": [{ "time": "2024-01-09T04:00:00+00:00", "value": 41888.06 }, "..."] },
        { "key": "middle", "label": "Base", "data": ["..."] },
        { "key": "upper", "label": "Upper", "data": ["..."] }
      ]
    }
  ]
}
```

### `POST /indicators/stochastic-oscillator` — `multiline_series`

Parámetros propios: `length` (int, default `14`), `d_length` (int, default `3`),
`upper_trigger` (float, default `80.0`), `lower_trigger` (float, default `20.0`).

**Response**
```json
{
  "elements": [
    {
      "kind": "multiline_series",
      "lines": [
        { "key": "slowK", "label": "Slow K", "data": ["..."] },
        { "key": "fastD", "label": "Fast D", "data": ["..."] }
      ],
      "upper_trigger": 80.0,
      "lower_trigger": 20.0
    }
  ]
}
```

---

## Indicadores del grupo `smc` (`/smc/*`)

### `POST /smc/liquidity-sweep` — `line` (sin `direction`)

Parámetros propios: `length` (int, default `50`), `levels`, `method`,
`equal_threshold` (float, default `0.1`), `atr_period` (int, default `200`),
`tolerance_pct` (float, default `0.003`), `max_confirmation_bars` (int, default `1`).

Mismo patrón que `bos-choch`: tick horizontal de una vela, a la altura del nivel
barrido (`swept_level`). `sub_kind="liquidity-sweep"` fijo.

### `POST /smc/fair-value-gaps` — `box` (`direction` + `filled`)

Parámetros propios: `min_gap_atr_multiple` (float, default `0.0`), `atr_period` (int,
default `200`), `include_filled` (bool, default `false`).

**Response**
```json
{
  "elements": [
    { "kind": "box", "sub_kind": "bullish-fvg", "time1": "2024-01-27T00:00:00+00:00", "price1": 41394.34, "time2": "2024-01-27T23:59:59.999000+00:00", "price2": 40300.24, "direction": 1, "filled": false, "id": "fair_value_gaps:bullish-fvg:2024-01-27T00:00:00+00:00" }
  ]
}
```

### `POST /smc/fractal` — `box`

Parámetros propios: `length` (int, default `5`), `include_mitigated` (bool, default
`false`). Reutiliza la misma detección de swings (pivots) que `swings`/
`swing_high`/`swing_low`, pero representada como caja en vez de un marker: `top`/
`bottom` = high/low de la vela de origen del pivote, horizontal desde esa vela
hasta la vela de confirmación (`length` velas después). `sub_kind` en
{`bullish-fractal`,`bearish-fractal`} (`direction` `1`/`-1` respectivamente). Base
pensada para representar más adelante fractales estilo IPDA.

**Request**
```json
{ "symbol": "BTCUSDT", "interval": "4h", "start_date": "2024-01-01T00:00:00", "end_date": "2024-02-01T00:00:00", "length": 5 }
```

**Response**
```json
{
  "elements": [
    { "kind": "box", "sub_kind": "bearish-fractal", "time1": "2024-01-08T16:00:00+00:00", "price1": 47248.99, "time2": "2024-01-09T12:00:00+00:00", "price2": 44793.97, "direction": -1, "id": "fractal:bearish-fractal:2024-01-08T16:00:00+00:00" }
  ]
}
```

---

## Indicadores del grupo `analysis` (`/analysis/*`)

### `POST /analysis/divergence` — `line`

Detector **genérico** de divergencias: compara pivotes confirmados de un
oscilador contra el precio en esas mismas barras, clasificando las 4 divergencias
clásicas. No está atado a un indicador concreto (funciona con RSI, MACD, Volume
Oscillator, CVD, Momentum, etc.) — hoy la única fuente disponible en la API es el
Stochastic Oscillator ya existente en `df.indicators` (agregar RSI/MACD/etc. más
adelante solo necesita una nueva rama de `source`, el detector en sí no cambia).

Parámetros propios: `length` (int, default `5` — longitud de pivote para la
divergencia, no confundir con `stochastic_length`), `source`
(`"slow_k"|"fast_d"`, default `"slow_k"`), `stochastic_length` (int, default `14`),
`stochastic_d_length` (int, default `3`).

`sub_kind` en {`regular-bullish`,`hidden-bullish`,`regular-bearish`,`hidden-bearish`}
(guiones, no guion bajo — distinto de la columna interna `divergence_type`).
`direction`: `1` en las 2 alcistas, `-1` en las 2 bajistas.

**Request**
```json
{ "symbol": "BTCUSDT", "interval": "4h", "start_date": "2023-06-01T00:00:00", "end_date": "2024-06-01T00:00:00", "length": 5 }
```

**Response**
```json
{
  "elements": [
    { "kind": "line", "sub_kind": "hidden-bullish", "time1": "2023-06-07T20:00:00+00:00", "price1": 26125.01, "time2": "2023-06-09T00:00:00+00:00", "price2": 26269.91, "direction": 1, "id": "divergence:hidden-bullish:2023-06-07T20:00:00+00:00" }
  ]
}
```

---

## Velas crudas de un broker (`/brokers/*`)

A diferencia de `/indicators/*` y `/smc/*` (que devuelven elementos visuales listos
para dibujar), esta ruta instancia el broker real vía
`BrokerFactory.get_broker(...)` (`app/brokers/factory.py`) y devuelve el DataFrame
OHLCV **crudo**, sin correr ningún indicador — no cambió con el refactor de
elementos visuales.

### `POST /brokers/candles`

Parámetros: `broker` (`"binance"|"bitunix"`), `symbol`, `interval`, `start_date`,
`end_date`, `testnet` (bool, default `false`).

**Response**
```json
{
  "data": [
    { "time": "2024-01-01T00:00:00+00:00", "open": 42283.58, "high": 42775.0, "low": 42230.08, "close": 42330.49, "volume": 3948.08335, "close_time": "2024-01-01T03:59:59.999000+00:00" }
  ],
  "count": 12
}
```

Errores: `broker` fuera del enum → 422; sin datos para el rango pedido → 404;
fallo al inicializar el broker o al llamar a su API → 502.
