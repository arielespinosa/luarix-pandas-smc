# Conceptos y gotchas

Cuatro cosas que hay que entender para interpretar bien los resultados. Las dos
primeras son la causa del 90 % de los "esto no coincide con TradingView".

## El pivote es asimétrico

`compute_leg` porta la función `leg()` de LuxAlgo. Su condición para declarar un
swing high es:

```python
new_leg_high = high.shift(length) > high.rolling(length).max()
#              high[i-length]     >  max(high[i-length+1 .. i])
```

**Solo mira las `length` velas POSTERIORES al pivote.** No exige nada de las
anteriores.

!!! warning "No es `ta.pivothigh` de Pine"
    `ta.pivothigh` es **simétrico**: exige que el pivote supere las `length` velas de
    cada lado. Aquí un swing high puede tener velas más altas a su izquierda y seguir
    siendo válido.

    Medido sobre BTCUSDT 1d, 260 velas, `length=10`: de 10 swing highs y 10 swing lows,
    **0** incumplen la definición asimétrica real, pero **3 de cada lado** incumplen la
    simétrica. Si escribes un test que asume simetría, va a fallar — y el que está mal
    es el test.

### Corolario: los swings alternan

`find_pivots` solo emite un pivote cuando la pierna **cambia** de sentido
(`leg != leg.shift(1)`). Por eso los swings alternan high/low estrictamente: nunca
salen dos highs seguidos.

```python
df.smc.swings(length=50)["swing_type"].tolist()
# ['low', 'high', 'low', 'high', 'low', 'high', ...]
```

Esto importa para `fib_expansion` y `ipda_fractal`, que consumen tripletas y sextetos
de swings alternados: si un patrón no aparece, suele ser porque la secuencia de
pivotes no tiene la forma requerida, no porque el detector falle.

## Confirmación vs origen

Un pivote **ocurre** en la vela `i - length` pero solo se **sabe** en la vela `i`. Son
dos barras distintas y la librería las distingue con cuidado:

```mermaid
graph LR
    A["vela i-length<br/>ORIGEN<br/>aquí está el máximo real"] -->|"pasan length velas"| B["vela i<br/>CONFIRMACIÓN<br/>aquí se detecta"]
```

| Concepto | Qué es | Dónde aparece |
|---|---|---|
| **Origen** | La vela donde realmente ocurrió el extremo de precio | Es la fila que devuelven `swings`, `swing_high`, `fractal`, `order_blocks`… |
| **Confirmación** | La vela `length` después, donde el algoritmo se entera | `fractal` la expone como `confirm_time`; `bos_choch` la expone como `broken_bar_index` |

!!! info "Por qué esto no es look-ahead bias"
    El retraso de `length` velas es exactamente lo que hace la detección honesta: en
    tiempo real no puedes saber que la vela de hace `length` barras era un máximo hasta
    que pasan esas `length` barras. Si escribes un backtest, el nivel solo está
    disponible a partir de `confirm_time`, no de la fila devuelta.

    `smc.liquidity_sweep` respeta esto explícitamente: solo busca barridos a partir de
    `origen + length`, nunca antes.

### El gotcha de implementación

Si trabajas con `_core.pivots.find_pivots` directamente, devuelve series *sparse*: NaN
salvo en la vela de confirmación, **pero el valor guardado es el precio de la vela de
origen**. Indexar con `pivot_high.notna()` selecciona la vela equivocada:

```python
# MAL: devuelve la vela de confirmación, cuyo OHLC no tiene nada que ver con el nivel
df.loc[pivot_high.notna()]

# BIEN: hay que restar length a las posiciones
positions = pivot_high.notna().to_numpy().nonzero()[0] - length
df.iloc[positions]
```

Este desfase ya causó un bug real y es la fuente más probable de look-ahead bias en
cualquier código nuevo que consuma pivotes.

## Mitigación: marcar, nunca borrar

Un nivel está **mitigado** cuando el precio ya lo atravesó, así que dejó de ser una
zona sin explotar. La librería lo marca con una columna booleana y **retiene la fila**.

| Elemento | Criterio de mitigación | Columna |
|---|---|---|
| `swing_high` | Un cierre posterior queda por encima del nivel | `mitigated` |
| `swing_low` | Un cierre posterior queda por debajo del nivel | `mitigated` |
| Order block alcista | Según `ob_mitigation`: un `low` (o `close`) posterior baja del `bottom` | `mitigated` |
| Order block bajista | Según `ob_mitigation`: un `high` (o `close`) posterior sube del `top` | `mitigated` |
| Fair value gap | El precio vuelve a entrar en el hueco | `filled` |
| Equal high/low | Se evalúa **por miembro**, no por grupo entero | `mitigated` |

El filtrado por miembro de los equal levels merece una nota: si de 3 niveles iguales el
primero ya fue mitigado antes de que se formara el segundo, el grupo vigente es el de
los otros dos — no "nada". Por eso `include_mitigated=False` recorta miembros en vez de
descartar el grupo.

## ATR sembrado con SMA (Wilder), no `.ewm()` en frío

`compute_atr` **no** es un `.ewm(alpha=1/period)` desde la barra 0. Siembra la
recursión con el promedio simple de los primeros `period` true ranges y solo desde ahí
aplica el suavizado de Wilder.

!!! danger "No son la misma fórmula"
    Un `.ewm(adjust=False)` en frío diverge sistemáticamente de esto durante **cientos
    de barras**. Medido: ATR(200) en la barra 450 daba 455.48 con el arranque en frío
    contra 508.87 con la siembra SMA — un ~10 % de diferencia, suficiente para que pares
    de equal highs/lows caigan del lado equivocado del umbral.

    Esto fue un bug real que no lanzaba ningún error: solo devolvía menos grupos de los
    que debía.

Todo lo que consume ATR en la librería (`equal_high`, `order_blocks`, `fair_value_gaps`
con filtro de tamaño, `expansion`, `consolidation`) usa esta misma función.

!!! note "`df.indicators.atr()` es otra cosa"
    Ese método delega en `pandas_ta_classic` y tiene `length=14` por defecto. Es el ATR
    "de indicador", para mostrar o para alimentar tu propia lógica. El ATR interno de
    los detectores SMC es `_core.volatility.compute_atr` con `atr_period=200` por
    defecto, elegido para replicar el indicador de referencia.

## Los defaults tienen historia

No son arbitrarios y conviene no cambiarlos sin motivo:

| Default | Dónde | Por qué |
|---|---|---|
| `length=50` | `swings`, `bos_choch`, `order_blocks`, `liquidity_sweep`, `fib_expansion`, `ipda_fractal` | Coincide con el `swing_length` del indicador de referencia |
| `length=3` | `equal_high`, `equal_low`, `equal_high_low` | En la referencia, el lookback de equal levels es un campo **independiente** y mucho más corto. Heredar `50` hacía que `equal_high()` devolviera `[]` |
| `length=5` | `fractal`, `demand_zone` | Fractal clásico de 5 velas |
| `atr_period=200` | Todo lo SMC | Default real del `_compute_atr` de la referencia |
| `atr_period=14` | `df.indicators.atr()` | Convención estándar del indicador ATR |
