# Indicadores clásicos

`df.indicators` agrupa los indicadores técnicos de toda la vida. Delegan en
`pandas_ta_classic` salvo el estocástico, que es cálculo propio.

!!! info "Estos NO filtran filas"
    A diferencia de `df.smc`, cada método devuelve el **DataFrame completo** —todas las
    velas— con las columnas del indicador agregadas. Las primeras filas llevan `NaN`
    hasta que hay historia suficiente para el cálculo.

---

## `bb50`

```python
df.indicators.bb50(length: int = 50, std: float = 2.0) -> pd.DataFrame
```

**Qué hace.** Bandas de Bollinger sobre el cierre: una media móvil simple con dos
bandas a `std` desviaciones típicas.

**Requiere.** `length` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `50` | Periodo de la media y de la desviación típica |
| `std` | `float` | `2.0` | Cuántas desviaciones típicas separan las bandas de la media |

**Devuelve.** El df completo más:

| Columna | Tipo | Contenido |
|---|---|---|
| `lower` | `float` | Banda inferior: `middle - std × σ` |
| `middle` | `float` | La media móvil simple de `length` periodos |
| `upper` | `float` | Banda superior: `middle + std × σ` |

```python
df.indicators.bb50(length=20)[["close", "lower", "middle", "upper"]].tail(3)
```

!!! note "El nombre dice 50 pero el periodo es un parámetro"
    `bb50` se llama así por su default histórico. `df.indicators.bb50(length=20)` te da
    unas Bollinger de 20 perfectamente normales.

!!! tip "El ~95 % teórico no se cumple en precios, y no es un fallo"
    Sobre datos reales, alrededor del **81 %** de los cierres caen dentro de las bandas,
    no el 95 % de la teoría. El 95 % asume retornos normales; una serie de precios real
    es tendencial y de colas pesadas. Comprobado explícitamente, no es un bug.

---

## `ema`

```python
df.indicators.ema(length: int = 20, source: str = "close") -> pd.DataFrame
```

**Qué hace.** Media móvil exponencial sobre la columna que elijas.

**Requiere.** `length` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `20` | Periodo de la media |
| `source` | `str` | `"close"` | Columna de entrada. Debe existir en el df; si no, `ValueError` con la lista de columnas disponibles |

**Devuelve.** El df completo más la columna `ema` (`float`).

```python
df.indicators.ema(length=200)                 # EMA 200 del cierre
df.indicators.ema(length=20, source="high")   # EMA de los máximos
```

---

## `rsi`

```python
df.indicators.rsi(length: int = 14) -> pd.DataFrame
```

**Qué hace.** Relative Strength Index sobre el cierre. Oscilador de 0 a 100.

**Requiere.** `length` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `14` | Periodo del RSI |

**Devuelve.** El df completo más la columna `rsi` (`float`, 0–100).

```python
df.indicators.rsi()[["close", "rsi"]].tail(3)
```

```text
               close        rsi
date
2026-06-29  60260.21  34.393114
2026-06-30  58624.71  30.263454
2026-07-01  60112.76  37.604346
```

**Uso típico.** Alimentar el detector de divergencias:

```python
rsi = df.indicators.rsi(length=14)["rsi"]
df.analysis.divergence(rsi, length=5)
```

---

## `atr`

```python
df.indicators.atr(length: int = 14) -> pd.DataFrame
```

**Qué hace.** Average True Range: la medida estándar de volatilidad en unidades de
precio.

**Requiere.** `length` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `14` | Periodo del ATR |

**Devuelve.** El df completo más la columna `atr` (`float`).

```python
df.indicators.atr()[["close", "atr"]].tail(3)
```

```text
               close          atr
date
2026-06-29  60260.21  2219.352818
2026-06-30  58624.71  2209.080474
2026-07-01  60112.76  2246.743297
```

!!! warning "No es el mismo ATR que usan los detectores SMC"
    Este delega en `pandas_ta_classic` con `length=14`. Los detectores de `df.smc` usan
    `_core.volatility.compute_atr`, que **siembra la recursión de Wilder con la SMA de
    los primeros `period` true ranges** y por defecto usa `atr_period=200`. Las dos
    fórmulas divergen sistemáticamente durante cientos de barras; ver
    [ATR sembrado con SMA](../guia/conceptos.md#atr-sembrado-con-sma-wilder-no-ewm-en-frio).

    Si quieres reproducir a mano lo que hace un detector SMC, importa `compute_atr`,
    no uses este método.

---

## `stochastic_oscillator`

```python
df.indicators.stochastic_oscillator(
    length: int = 14,
    d_length: int = 3,
    upper_trigger: float = 80.0,
    lower_trigger: float = 20.0,
) -> pd.DataFrame
```

**Qué hace.** Oscilador estocástico: dónde está el cierre actual dentro del rango
máximo-mínimo de las últimas `length` velas, en porcentaje.

```python
slow_k = (close - min(low, length)) / (max(high, length) - min(low, length)) * 100
fast_d = slow_k.rolling(d_length).mean()
```

**Requiere.** `length + d_length` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `14` | Ventana del rango para %K |
| `d_length` | `int` | `3` | Suavizado de %D (media móvil de %K) |
| `upper_trigger` | `float` | `80.0` | Nivel de sobrecompra (se emite como columna constante) |
| `lower_trigger` | `float` | `20.0` | Nivel de sobreventa (ídem) |

**Devuelve.** El df completo más:

| Columna | Tipo | Contenido |
|---|---|---|
| `slow_k` | `float` | %K, de 0 a 100 |
| `fast_d` | `float` | %D, media móvil de %K |
| `upper_trigger` | `float` | El valor pasado, repetido en todas las filas |
| `lower_trigger` | `float` | Ídem |

```python
df.indicators.stochastic_oscillator()[
    ["close", "slow_k", "fast_d", "upper_trigger", "lower_trigger"]
].tail(3)
```

```text
               close     slow_k     fast_d  upper_trigger  lower_trigger
date
2026-06-29  60260.21  24.165849  20.317600           80.0           20.0
2026-06-30  58624.71   6.118172  15.404970           80.0           20.0
2026-07-01  60112.76  29.562526  19.948849           80.0           20.0
```

Las columnas de trigger son constantes a propósito: así el resultado se puede graficar
o comparar directamente sin arrastrar los umbrales por separado.

!!! note "Serie sin rango → `NaN`"
    Si en la ventana `max(high) == min(low)` (una serie perfectamente plana), la
    división es `0/0` y `slow_k` sale `NaN`. No lanza excepción.
