# Análisis

---

## `divergence`

```python
df.analysis.divergence(indicator: pd.Series, length: int = 5) -> pd.DataFrame
```

**Qué hace.** Compara los pivotes de **cualquier** serie de indicador contra el precio
en esas mismas barras y clasifica las divergencias.

La clave del diseño: el método **no sabe qué es un RSI**. Recibe una `pd.Series`
alineada al índice del df y trabaja con ella. Eso significa que sirve igual para RSI,
%K del estocástico, MACD, un oscilador de volumen, CVD, momentum o cualquier serie que
calcules tú.

### Las cuatro clasificaciones

| `divergence_type` | `direction` | Precio | Indicador | Lectura |
|---|---|---|---|---|
| `regular_bullish` | `1` | Mínimo más bajo (LL) | Mínimo más alto (HL) | Agotamiento de la caída |
| `hidden_bullish` | `1` | Mínimo más alto (HL) | Mínimo más bajo (LL) | Continuación alcista |
| `regular_bearish` | `-1` | Máximo más alto (HH) | Máximo más bajo (LH) | Agotamiento de la subida |
| `hidden_bearish` | `-1` | Máximo más bajo (LH) | Máximo más alto (HH) | Continuación bajista |

Los pivotes se detectan **sobre el indicador**, no sobre el precio; el precio se lee en
esas mismas barras. Los pivotes bajos del indicador se comparan contra `low`, los altos
contra `high`, y siempre entre pares **consecutivos**.

**Requiere.** `length * 2 + 1` filas, y que `indicator` comparta exactamente el índice
del df.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `indicator` | `pd.Series` | — | La serie a comparar. **Obligatoria y alineada al índice del df** |
| `length` | `int` | `5` | Ventana de confirmación de los pivotes del indicador |

!!! danger "La alineación se valida y es obligatoria"
    ```python
    rsi = df.indicators.rsi()["rsi"]

    df.analysis.divergence(rsi)                       # OK
    df.analysis.divergence(rsi.iloc[:50])             # ValueError: must be aligned
    df.analysis.divergence(rsi.reset_index(drop=True))# ValueError: must share the index
    df.analysis.divergence(rsi.to_numpy())            # ValueError: must be a Series
    ```

    Sin esta comprobación, una serie desalineada devolvía filas del df de **barras
    equivocadas** sin lanzar nada: los pivotes se buscan sobre las posiciones de la
    serie y luego se usan para indexar el df. Era corrupción silenciosa, no un crash.

**Devuelve.** Filas del df en la vela del **segundo** pivote de cada par (el que cierra
la divergencia), más:

| Columna | Tipo | Contenido |
|---|---|---|
| `divergence_type` | `str` | Una de las cuatro de la tabla |
| `direction` | `int` | `1` alcista, `-1` bajista |
| `price` | `float` | Precio en el segundo pivote (`low` en las alcistas, `high` en las bajistas) |
| `prior_time` | etiqueta del índice | Timestamp del primer pivote |
| `prior_price` | `float` | Precio en el primer pivote |
| `indicator_value` | `float` | Valor del indicador en el segundo pivote |
| `prior_indicator_value` | `float` | Valor del indicador en el primer pivote |

```python
rsi = df.indicators.rsi(length=14)["rsi"]
df.analysis.divergence(rsi, length=5)[
    ["close", "divergence_type", "direction", "price", "prior_price",
     "indicator_value", "prior_indicator_value"]
].head(4)
```

```text
               close  divergence_type  direction     price  prior_price  indicator_value  prior_indicator_value
date
2017-10-21   6024.97  regular_bearish         -1   6171.00      5900.00        74.626543              81.561303
2017-10-24   5477.03   hidden_bullish          1   5450.00      5037.95        56.605414              67.389490
2017-12-16  19102.66  regular_bearish         -1  19539.00     16649.96        81.818239              93.459276
2017-12-23  13300.00   hidden_bullish          1  12978.18     12535.00        45.240265              73.995633
```

Lee la primera fila: el precio hizo un máximo más alto (6171 > 5900) mientras el RSI
hacía uno más bajo (74.6 < 81.6). Divergencia bajista regular.

### Con otros indicadores

```python
# Estocástico
k = df.indicators.stochastic_oscillator(length=14)["slow_k"]
df.analysis.divergence(k, length=5)

# Una serie propia: volumen acumulado con signo (CVD)
signo = (df["close"] > df["open"]).map({True: 1, False: -1})
cvd = (df["volume"] * signo).cumsum()
df.analysis.divergence(cvd, length=5)
```

**Notas.**

- Cada evento se detecta entre pivotes **consecutivos** del indicador. Una divergencia
  entre el pivote 1 y el 5 no se reporta, aunque exista visualmente.
- La coherencia de signos está verificada numéricamente: las cuatro combinaciones
  imponen el signo de ambas pendientes, y los tests lo comprueban sin depender del ojo.
- El `length` aquí actúa sobre la serie del indicador, que suele ser mucho más suave
  que el precio. Valores de 3 a 10 son lo razonable; `50` casi nunca produce nada.
