# Enums y parámetros

Todos los parámetros categóricos de la librería son `Enum` de tipo `str`. Eso da tres
cosas gratis: autocompletado, validación automática y compatibilidad con cadenas
sueltas.

```python
from pandas_luarix import EqualLevelMethod, ObMitigation, VolatilityMethod
from pandas_luarix import LiquidityLevels, ZoneOrigin, ZoneSide

df.smc.order_blocks(ob_mitigation="close")                # cadena
df.smc.order_blocks(ob_mitigation=ObMitigation.CLOSE)     # miembro -- idéntico

df.smc.order_blocks(ob_mitigation="Close")
# ValueError: 'Close' is not a valid ObMitigation
```

!!! tip "La validación es automática, no manual"
    Cada método coacciona el valor recibido con `TipoEnum(valor)`, así que un valor
    inválido lanza `ValueError` **antes** de calcular nada. No hay forma de que un
    parámetro categórico mal escrito produzca un resultado silenciosamente distinto.

---

## `EqualLevelMethod`

Cómo se decide que dos niveles son "iguales". Usado por
[`equal_high`](estructura.md#equal_high), `equal_low`, `equal_high_low` y
[`liquidity_sweep`](liquidez.md#liquidity_sweep).

| Miembro | Valor | Comportamiento |
|---|---|---|
| `ATR_PIVOT` | `"atr_pivot"` | Compara cada pivote **solo con el anterior** del mismo tipo. Tolerancia = `equal_threshold × ATR(atr_period)`, adaptativa a la volatilidad. Grupos siempre de 2 miembros. Replica el indicador de referencia |
| `PCT_RANGE` | `"pct_range"` | Agrupa **todos** los pivotes dentro de `tolerance_pct` entre sí, no solo los adyacentes. Grupos de 2, 3 o más miembros |

Parámetros que aplican a cada rama:

| Parámetro | `ATR_PIVOT` | `PCT_RANGE` |
|---|---|---|
| `equal_threshold` | ✅ | ❌ |
| `atr_period` | ✅ | ❌ |
| `tolerance_pct` | ❌ | ✅ |
| `search_window` | ❌ | ✅ |

!!! note "`PCT_RANGE` es un nombre heredado"
    Ya no compara velas crudas por pares: opera sobre pivotes confirmados igual que
    `ATR_PIVOT`, con el mismo retraso de confirmación. El nombre se mantuvo por
    compatibilidad, pero lo que hace es **agrupar por proximidad de precio**.

---

## `ObMitigation`

Con qué precio se comprueba si un order block ya fue mitigado. Usado por
[`bullish_order_block`](zonas.md#bullish_order_block), `bearish_order_block` y
`order_blocks`.

| Miembro | Valor | Comportamiento |
|---|---|---|
| `HIGH_LOW` | `"high_low"` | La **mecha** basta: para un OB alcista, cualquier `low` posterior por debajo del `bottom` lo mitiga. Más estricto |
| `CLOSE` | `"close"` | Hace falta un **cierre**: una mecha que perfora pero cierra dentro no mitiga. Más permisivo |

La diferencia importa en la práctica: una vela que perfora la zona con la mecha y cierra
por encima es, para muchas estrategias, un rebote válido y no una invalidación.

---

## `VolatilityMethod`

Qué medida de volatilidad usa el paso `parsed_high_low` de los order blocks para decidir
qué es una vela de alta volatilidad.

| Miembro | Valor | Comportamiento |
|---|---|---|
| `ATR` | `"atr"` | ATR de Wilder sembrado con SMA, de periodo `atr_period` |
| `CUMULATIVE_MEAN_RANGE` | `"cumulative_mean_range"` | Media **acumulada** (expanding) del true range desde el inicio de la serie. No tiene periodo: usa todo el histórico disponible en cada barra |

---

## `LiquidityLevels`

Qué niveles vigila [`liquidity_sweep`](liquidez.md#liquidity_sweep).

| Miembro | Valor | Comportamiento |
|---|---|---|
| `SWINGS` | `"swings"` | Solo pivotes individuales (swing highs y lows) |
| `EQUAL_HIGH_LOW` | `"equal_high_low"` | Solo niveles donde coinciden 2+ pivotes |
| `BOTH` | `"both"` | Los dos. La columna `swept_level_type` te dice cuál disparó cada fila |

---

## `ZoneOrigin`

A qué nivel se ancla una [`demand_zone`](zonas.md#demand_zone).

| Miembro | Valor | Estado |
|---|---|---|
| `FRACTAL` | `"fractal"` | Implementado |

Es un punto de extensión deliberado: agregar un origen nuevo (por ejemplo anclar la
banda a un order block) es añadir un miembro aquí **y** una rama en `build_zone`, no
escribir otra función de zona.

---

## `ZoneSide`

Hacia qué lado se proyecta la banda de una [`demand_zone`](zonas.md#demand_zone).

| Miembro | Valor | Comportamiento |
|---|---|---|
| `SUPPORT` | `"support"` | Demanda: ancla el borde **bajo** del origen, la banda extiende hacia abajo. `direction = 1` |
| `RESISTANCE` | `"resistance"` | Oferta: ancla el borde **alto**, la banda extiende hacia arriba. `direction = -1` |

---

## Parámetros numéricos comunes

Los que aparecen en varios métodos y conviene entender de una vez:

| Parámetro | Rango típico | Qué controla | Dónde |
|---|---|---|---|
| `length` | 3–50 | Ventana de confirmación de pivotes. **El parámetro que más cambia los resultados** | Casi todos los de `df.smc` |
| `atr_period` | 14–200 | Periodo del ATR interno de Wilder | Order blocks, equal levels (ATR), FVG con filtro, expansión, consolidación |
| `include_mitigated` | — | Incluir los elementos ya invalidados, con su flag | Swings, order blocks, equal levels, fractales, zonas |
| `include_filled` | — | Lo mismo para los fair value gaps | `fair_value_gaps` |
| `as_records` | — | Devolver `list[dict]` en vez de DataFrame | `bos_choch`, `order_blocks`, `fair_value_gaps`, `equal_high`/`equal_low`, `ipda_fractal` |
| `confluence_filter` | — | Exigir cuerpo dominante en la vela que rompe | `bos_choch`, order blocks |

### Tipos aceptados

| Parámetro | Acepta | Rechaza con `ValueError` |
|---|---|---|
| Enteros (`length`, `atr_period`, `window`…) | `int` de Python **y enteros de numpy** (`np.int64`, `np.int32`…) | `bool`, `float`, `str`, `None`, ≤ 0 |
| Flotantes (`multiplier`, `tolerance_pct`, `offset_pct`…) | Cualquier número real | `bool`, no numéricos, ≤ 0 (o < 0 en los que admiten cero) |
| Categóricos | El miembro del Enum o su cadena exacta | Cualquier otra cosa |
