# pandas-luarix

Accessors de `pandas.DataFrame` para análisis de mercado. Un solo `import` registra
tres espacios de nombres sobre cualquier DataFrame OHLC:

| Accessor | Qué contiene |
|---|---|
| **`df.smc`** | Smart Money Concepts: swings, BOS/CHoCH, order blocks, fair value gaps, barridos de liquidez, equal highs/lows, fractales, zonas, expansiones |
| **`df.indicators`** | Indicadores clásicos: Bollinger, EMA, RSI, ATR, Estocástico |
| **`df.analysis`** | Análisis genérico sobre cualquier serie: divergencias precio ↔ indicador |

```python
import pandas as pd
import pandas_luarix  # el import ES el efecto: registra .smc / .indicators / .analysis

df = pd.read_csv("BTCUSDT_1d.csv", parse_dates=["date"], index_col="date")

df.smc.order_blocks()          # bloques de orden vigentes
df.smc.fair_value_gaps()       # huecos de valor justo sin rellenar
df.smc.bos_choch(length=50)    # rupturas y cambios de carácter
df.indicators.rsi(length=14)   # RSI sobre el cierre
```

## Qué es y qué no es

Es una librería **pura de cálculo**: entra un DataFrame OHLC, sale otro DataFrame con
lo detectado. Es determinista, no tiene estado y no hace efectos secundarios.

!!! warning "Lo que la librería NO hace, por diseño"
    No descarga velas, no habla con exchanges, no dibuja gráficos, no persiste en base
    de datos y no expone HTTP. Sus únicas dependencias son `pandas`, `numpy` y
    `pandas_ta_classic`. Si necesitas datos o gráficos, eso vive en la capa que
    consume esta librería.

## Las tres ideas que hay que entender antes de usarla

1. **La salida son filas del DataFrame de entrada.** Cada detector devuelve un
   subconjunto de filas del `df` original **más columnas nuevas**, así que el resultado
   siempre es indexable contra la serie original. Ver
   [Contrato de entrada y salida](guia/contratos.md).

2. **Un pivote se confirma `length` velas después de ocurrir.** La fila devuelta es la
   de **origen** (donde ocurrió el extremo de precio), no la de confirmación. El
   `length` de retraso es lo que evita el look-ahead bias. Ver
   [Conceptos y gotchas](guia/conceptos.md#confirmacion-vs-origen).

3. **El pivote es asimétrico.** No es `ta.pivothigh` de Pine: un swing high solo exige
   ser mayor que las `length` velas **posteriores**, nada sobre las anteriores. Una
   diferencia contra TradingView casi siempre es esto. Ver
   [Conceptos y gotchas](guia/conceptos.md#el-pivote-es-asimetrico).

## Por dónde seguir

<div class="grid cards" markdown>

- :material-download: **[Instalación](guia/instalacion.md)** — instalar, entorno, tests.
- :material-rocket-launch: **[Primeros pasos](guia/primeros-pasos.md)** — de un CSV al primer detector.
- :material-table: **[Índice de métodos](referencia/index.md)** — los 24 métodos públicos en una tabla.
- :material-book-open-variant: **[Recetas](recetas.md)** — combinaciones de uso real.

</div>
