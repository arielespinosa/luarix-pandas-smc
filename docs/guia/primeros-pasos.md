# Primeros pasos

## 1. Preparar el DataFrame

La librería exige cuatro columnas **en minúscula**: `open`, `high`, `low`, `close`.
`volume` es opcional y se ignora (ningún detector lo usa hoy). El índice puede ser
cualquier cosa — fechas, enteros, strings — porque todo el cálculo interno es
posicional.

```python
import pandas as pd
import pandas_luarix  # noqa: F401 — el import registra los accessors

df = pd.read_csv("BTCUSDT_1d.csv", parse_dates=["date"], index_col="date")
df = df.rename(columns=str.lower)     # por si vienen en mayúscula
df = df.sort_index()                   # cronológico ascendente, sin excepción
```

!!! danger "El orden importa"
    Todos los detectores asumen que la fila 0 es la vela **más antigua**. Un DataFrame
    en orden inverso no lanza ningún error: devuelve resultados sin sentido.

## 2. Llamar a un detector

```python
obs = df.smc.order_blocks(length=50)
obs[["close", "top", "bottom", "direction", "mitigated"]].head(4)
```

```text
               close       top    bottom  direction  mitigated
date
2019-01-29   3411.04   3443.45   3349.92          1      False
2020-06-27   9012.00   9196.24   8833.00          1      False
2020-09-05  10166.69  10565.68   9825.00          1      False
2022-11-21  15781.29  16319.00  15476.00          1      False
```

Fíjate en la forma del resultado: **las columnas originales del df siguen ahí**, más
las que agrega el detector. Eso significa que puedes seguir operando con normalidad:

```python
alcistas = obs[obs["direction"] == 1]
altura   = obs["top"] - obs["bottom"]
df.loc[obs.index, "volume"].mean()     # el índice sirve para volver al df original
```

## 3. Elegir el `length`

`length` es la ventana de confirmación de pivotes y es **el parámetro que más cambia
los resultados** de toda la librería. No hay un valor correcto: define qué escala de
swing te interesa.

| `length` | Qué detecta | Retraso de confirmación |
|---|---|---|
| 3–5 | Micro-estructura, ruido incluido | 3–5 velas |
| 10–20 | Swings intermedios | 10–20 velas |
| 50 (default) | Estructura mayor | 50 velas |

Cada método necesita un mínimo de filas para poder trabajar; si no las tiene, lanza
`ValueError` con el número exacto en el mensaje en vez de devolver algo vacío y
ambiguo:

```python
df.head(20).smc.swings(length=50)
# ValueError: swings(length=50) requires at least 101 rows, got 20.
```

La regla general es `length * 2 + 1`; los métodos que además usan ATR piden
`max(length * 2 + 1, atr_period + 1)`.

## 4. Combinar detectores

Como todo comparte índice, cruzar señales es aritmética de pandas:

```python
sweeps = df.smc.liquidity_sweep(length=20)
fvgs   = df.smc.fair_value_gaps()

# Barridos de liquidez que además dejaron un fair value gap en la misma vela
confluencia = sweeps.index.intersection(fvgs.index)
df.loc[confluencia]
```

## 5. Divergencias con cualquier indicador

`df.analysis.divergence` no sabe nada de RSI: recibe **cualquier** Series alineada al
índice del df y compara sus pivotes contra el precio.

```python
rsi = df.indicators.rsi(length=14)["rsi"]
df.analysis.divergence(rsi, length=5)

k = df.indicators.stochastic_oscillator()["slow_k"]
df.analysis.divergence(k, length=5)
```

## Siguiente paso

- El [contrato de entrada y salida](contratos.md) en detalle: qué valida, qué devuelve
  cuando no hay nada, cómo se comportan las columnas.
- Los [conceptos y gotchas](conceptos.md): el desfase confirmación/origen, la asimetría
  del pivote y la mitigación. Leerlo evita interpretar mal los resultados.
- El [índice de métodos](../referencia/index.md) con los 24 métodos públicos.
