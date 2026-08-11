# Recetas

Combinaciones de uso real. Todas asumen un `df` OHLC ordenado cronológicamente y
`import pandas_luarix` hecho.

## Preparar un CSV de exchange

```python
import pandas as pd
import pandas_luarix  # noqa: F401

df = (
    pd.read_csv("BTCUSDT_1d.csv", parse_dates=["date"])
      .rename(columns=str.lower)
      .set_index("date")
      .sort_index()
)
df = df[~df.index.duplicated(keep="last")]     # índice único
df = df[["open", "high", "low", "close", "volume"]]
```

## Todos los niveles vigentes en este momento

Una foto del estado actual del gráfico: qué zonas siguen sin explotar.

```python
niveles = {
    "order_blocks":    df.smc.order_blocks(length=50),
    "fair_value_gaps": df.smc.fair_value_gaps(),
    "swing_highs":     df.smc.swing_high(length=50),
    "swing_lows":      df.smc.swing_low(length=50),
}

for nombre, tabla in niveles.items():
    print(f"{nombre:18s} {len(tabla):3d} vigentes")
```

Como los detectores excluyen los mitigados por defecto, lo que queda es exactamente lo
que sigue en juego.

## Confluencias: dos señales en la misma vela

Los índices son comparables entre detectores, así que cruzarlos es aritmética de
conjuntos.

```python
sweeps = df.smc.liquidity_sweep(length=20, max_confirmation_bars=10)
fvgs   = df.smc.fair_value_gaps()

# Barridos de liquidez que además dejaron un hueco en la misma vela
confluencia = sweeps.index.intersection(fvgs.index)
df.loc[confluencia]
```

Con más de dos:

```python
from functools import reduce

señales = [
    df.smc.liquidity_sweep(length=20).index,
    df.smc.expansion(atr_period=100).index,
    df.smc.bos_choch(length=20).index,
]
triple = reduce(lambda a, b: a.intersection(b), señales)
```

Que la intersección triple salga vacía es lo normal, no un error: exigir tres eventos
independientes en la **misma** vela es muy restrictivo. Si buscas confluencia en un
entorno de N velas en vez de en la misma, trabaja sobre posiciones:

```python
pos_sweep = set(df.index.get_indexer(sweeps.index))
pos_bos   = set(df.index.get_indexer(df.smc.bos_choch(length=20).index))

cercanas = {p for p in pos_sweep if any(abs(p - q) <= 3 for q in pos_bos)}
df.iloc[sorted(cercanas)]
```

## Marcar señales como columnas del df original

Para pasar el resultado a un backtester o a un modelo, suele ser más cómodo tener
columnas booleanas alineadas que tablas sueltas.

```python
señales = pd.DataFrame(index=df.index)

señales["es_expansion"]  = df.index.isin(df.smc.expansion().index)
señales["hay_sweep"]     = df.index.isin(df.smc.liquidity_sweep(length=20).index)
señales["hay_bos"]       = df.index.isin(df.smc.bos_choch(length=20).index)

# Con dirección en vez de booleano
bos = df.smc.bos_choch(length=20)
señales["bos_direccion"] = bos["direction"].reindex(df.index).fillna(0).astype(int)
```

!!! warning "Cuidado con el look-ahead al construir features"
    Una fila de `swings` o de `order_blocks` está en la vela de **origen**, pero ese
    dato no se conoce hasta `length` velas después. Si vas a entrenar algo, desplaza la
    señal a su vela de confirmación:

    ```python
    length = 20
    pos_origen = df.index.get_indexer(df.smc.swings(length=length).index)
    pos_confirm = pos_origen + length
    pos_confirm = pos_confirm[pos_confirm < len(df)]
    señales["swing_conocido"] = False
    señales.iloc[pos_confirm, señales.columns.get_loc("swing_conocido")] = True
    ```

## Zonas de reacción alrededor del precio actual

```python
precio = df["close"].iloc[-1]

obs = df.smc.order_blocks(length=50)
obs = obs.assign(distancia_pct=(obs["bottom"] - precio).abs() / precio * 100)

cercanos = obs[obs["distancia_pct"] < 5].sort_values("distancia_pct")
cercanos[["top", "bottom", "direction", "distancia_pct"]]
```

## Divergencias de varios indicadores a la vez

```python
indicadores = {
    "rsi":   df.indicators.rsi(length=14)["rsi"],
    "stoch": df.indicators.stochastic_oscillator(length=14)["slow_k"],
}

todas = []
for nombre, serie in indicadores.items():
    ev = df.analysis.divergence(serie, length=5)
    todas.append(ev.assign(indicador=nombre))

divergencias = pd.concat(todas).sort_index()

# Barras donde AMBOS indicadores divergen en el mismo sentido
conteo = divergencias.groupby([divergencias.index, "direction"]).size()
conteo[conteo > 1]
```

## Filtrar patrones IPDA por calidad

```python
patrones = df.smc.ipda_fractal(length=30, mode="both", direction=0)

buenos = patrones[
    (patrones["compliance"] >= 0.66)
    & (~patrones["invalidated"])
]
buenos[["pattern", "direction", "compliance", "invalidation_level"]]
```

Recuerda que en las correcciones `rule3_ok`/`rule4_ok` valen `False` por "no aplica":
no los uses como filtro para ese patrón.

## Objetivos de Fibonacci razonables

`fib_expansion` no filtra nada, así que las proyecciones absurdas hay que descartarlas.

```python
precio = df["close"].iloc[-1]
fib = df.smc.fib_expansion(length=50)

razonables = fib[
    (fib["d_price"] > 0)
    & ((fib["d_price"] - precio).abs() / precio < 1.0)   # dentro del ±100 % del precio
]
razonables.sort_values("c_pos").tail(9)
```

## Recorrer varios símbolos y timeframes

La librería es pura, así que barrer un directorio es un bucle sin sorpresas.

```python
from pathlib import Path

resumen = []
for csv in Path("test_data").glob("*/1d.csv"):
    símbolo = csv.parent.name
    d = pd.read_csv(csv, parse_dates=["date"], index_col="date").sort_index()
    if len(d) < 300:
        continue
    resumen.append({
        "símbolo":  símbolo,
        "velas":    len(d),
        "obs":      len(d.smc.order_blocks(length=50)),
        "fvgs":     len(d.smc.fair_value_gaps()),
        "sweeps":   len(d.smc.liquidity_sweep(length=50)),
    })

pd.DataFrame(resumen).set_index("símbolo")
```

```text
          velas  obs  fvgs  sweeps
símbolo
AVAXUSDT   1933    3    19       6
BNBUSDT    2984    6    46      13
BTCUSDT    3241    9    53       7
DOGEUSDT   2378    6    26      10
ETHUSDT    3065    5    34       5
PEPEUSDT    978    3    17       2
SOLUSDT    1975    5    30       8
XRPUSDT    2805    6    16      15
```

!!! tip "Los detectores no tienen escala de precio hardcodeada"
    Verificado sobre 6 símbolos con precios de 60.112 $ a 0,0000067 $ — **7 órdenes de
    magnitud**— y los conteos siguen siendo comparables. Puedes mezclar BTC y PEPE en el
    mismo barrido sin normalizar nada.

## Manejar los errores de validación

Todos los problemas de entrada llegan como `ValueError` con un mensaje accionable.

```python
try:
    señales = df.smc.order_blocks(length=50, atr_period=200)
except ValueError as e:
    print(f"No se pudo calcular: {e}")
    # p. ej. "order_block(length=50, atr_period=200) requires at least 201 rows, got 120."
```

Para un barrido sobre datos heterogéneos, comprobar el mínimo antes sale más barato que
capturar:

```python
def suficientes_filas(d, length=50, atr_period=200):
    return len(d) >= max(length * 2 + 1, atr_period + 1)
```
