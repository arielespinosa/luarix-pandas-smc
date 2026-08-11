# Estructura de mercado

Los detectores que describen el esqueleto de la serie: dónde giró el precio y cuándo
esa estructura se rompió.

Todos parten del mismo motor de pivotes ([`find_pivots`](../api-interna.md)), así que
todos comparten la [asimetría del pivote](../guia/conceptos.md#el-pivote-es-asimetrico)
y el [desfase confirmación/origen](../guia/conceptos.md#confirmacion-vs-origen).

---

## `swings`

```python
df.smc.swings(length: int = 50) -> pd.DataFrame
```

**Qué hace.** Devuelve **todos** los pivotes confirmados —altos y bajos— en una sola
tabla, cada uno en su vela de origen. Es la vista panorámica de la estructura: el
zigzag de la serie.

**Requiere.** `length * 2 + 1` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `50` | Ventana de confirmación del pivote. Más alto = swings más grandes y menos numerosos |

**Devuelve.** Filas del df en las velas de origen de cada pivote, ordenadas
cronológicamente, más:

| Columna | Tipo | Contenido |
|---|---|---|
| `swing_type` | `str` | `"high"` o `"low"` |

```python
df.smc.swings(length=50)[["open", "high", "low", "close", "swing_type"]].head(4)
```

```text
                open      high       low     close swing_type
date
2017-09-15   3188.01   3856.00   2817.00   3700.00        low
2017-12-17  19120.19  19798.68  18510.00  18860.02       high
2018-02-06   6939.63   7878.00   6000.01   7652.14        low
2018-02-20  11147.11  11786.01  11100.59  11200.99       high
```

!!! tip "Los tipos alternan siempre"
    `swing_type` nunca repite dos veces seguidas el mismo valor. Es una propiedad del
    algoritmo, no una casualidad de los datos: solo se emite un pivote cuando la pierna
    cambia de sentido.

**Notas.** El nivel de precio del pivote está en la columna `high` (para los `"high"`)
o `low` (para los `"low"`) de la fila devuelta. Este método no calcula mitigación; si
la necesitas, usa `swing_high`/`swing_low`.

---

## `swing_high`

```python
df.smc.swing_high(length: int = 50, include_mitigated: bool = False) -> pd.DataFrame
```

**Qué hace.** Solo los pivotes altos, cada uno con el dato de si el precio ya superó
ese nivel más adelante. Un swing high no mitigado es un techo que todavía no se ha
roto: liquidez pendiente por encima.

**Requiere.** `length * 2 + 1` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `50` | Ventana de confirmación del pivote |
| `include_mitigated` | `bool` | `False` | Si `True`, también devuelve los niveles ya superados (con `mitigated=True`) |

**Devuelve.** Filas del df en las velas de origen, más:

| Columna | Tipo | Contenido |
|---|---|---|
| `mitigated` | `bool` | `True` si algún **cierre** posterior a la vela de origen quedó por encima del nivel |

```python
df.smc.swing_high(length=50)[["high", "low", "close", "mitigated"]]
```

```text
                high       low     close  mitigated
date
2026-01-14  97924.49  94559.28  96951.78      False
2026-05-06  82850.00  80731.14  81447.01      False
```

!!! info "Por qué salen tan pocos"
    Sobre BTCUSDT diario (9 años) hay 23 swing highs, pero solo 2 siguen vigentes: en
    una serie tendencial casi todos los máximos acabaron superados. Con
    `include_mitigated=True` aparecen los 23.

**Notas.** El criterio de mitigación es por **cierre**, no por mecha: una vela que
perfora el nivel con la mecha pero cierra por debajo **no** lo mitiga (eso es un
[barrido de liquidez](liquidez.md), un concepto distinto).

---

## `swing_low`

```python
df.smc.swing_low(length: int = 50, include_mitigated: bool = False) -> pd.DataFrame
```

Simétrico de [`swing_high`](#swing_high): pivotes bajos, `mitigated=True` cuando un
cierre posterior queda **por debajo** del nivel. Mismos parámetros, mismas columnas.

---

## `bos_choch`

```python
df.smc.bos_choch(
    length: int = 50,
    confluence_filter: bool = False,
    as_records: bool = False,
) -> pd.DataFrame | list[dict]
```

**Qué hace.** Detecta cuándo el precio rompe el pivote vigente y clasifica la ruptura:

- **BOS** (*Break of Structure*): la ruptura va **a favor** de la tendencia en curso, o
  no había tendencia definida todavía. Continuación.
- **CHoCH** (*Change of Character*): la ruptura va **en contra** de la tendencia en
  curso. Primer aviso de giro.

La diferencia entre uno y otro no está en la vela: está en el estado de tendencia
acumulado. Por eso este detector es un recorrido secuencial y no una operación
vectorizada.

**Requiere.** `length * 2 + 1` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `50` | Ventana de confirmación de los pivotes que se rompen |
| `confluence_filter` | `bool` | `False` | Si `True`, exige además que la vela que rompe tenga cuerpo dominante en la dirección de la ruptura (descarta roturas de solo mecha) |
| `as_records` | `bool` | `False` | Devolver `list[dict]` en vez de DataFrame |

**Devuelve (DataFrame).** Filas del df en la vela **que rompió** —no en la del
pivote—, más:

| Columna | Tipo | Contenido |
|---|---|---|
| `structure_type` | `str` | `"BOS"` o `"CHOCH"` |
| `direction` | `int` | `1` ruptura alcista, `-1` bajista |

```python
df.smc.bos_choch(length=50)[["close", "structure_type", "direction"]].head(4)
```

```text
              close structure_type  direction
date
2018-06-13  6292.78            BOS         -1
2018-11-15  5753.40            BOS         -1
2019-04-02  4857.29          CHOCH          1
2019-09-24  8493.14          CHOCH         -1
```

**Devuelve (`as_records=True`).** Una lista de diccionarios con las dos barras del
evento explícitas:

| Clave | Tipo | Contenido |
|---|---|---|
| `structure_type` | `str` | `"BOS"` / `"CHOCH"` |
| `direction` | `int` | `1` / `-1` |
| `broken_bar_index` | `int` | Posición de la vela que rompió |
| `broken_time` | etiqueta del índice | Su timestamp |
| `pivot_bar_index` | `int` | Posición de origen del pivote roto |
| `pivot_level` | `float` | Precio del nivel roto |

```python
df.smc.bos_choch(length=50, as_records=True)[0]
```

```text
{'structure_type': 'BOS', 'direction': -1,
 'broken_bar_index': 300, 'broken_time': Timestamp('2018-06-13 00:00:00'),
 'pivot_bar_index': 227, 'pivot_level': 6430.0}
```

**Notas.**

- Cada pivote se rompe **una sola vez**: una vez cruzado deja de rastrearse, así que no
  hay eventos duplicados sobre el mismo nivel.
- La ruptura se evalúa por **cierre** cruzando el nivel (`close[i-1] < nivel <= close[i]`
  para las alcistas), no por mecha.
- Este es el motor que alimenta a los [order blocks](zonas.md#order_blocks): cada order
  block nace de un evento BOS/CHoCH.

---

## `equal_high`

```python
df.smc.equal_high(
    length: int = 3,
    method: EqualLevelMethod = EqualLevelMethod.ATR_PIVOT,
    equal_threshold: float = 0.1,
    atr_period: int = 200,
    tolerance_pct: float = 0.003,
    include_mitigated: bool = False,
    as_records: bool = False,
    search_window: int | None = None,
) -> list[pd.DataFrame] | list[dict]
```

**Qué hace.** Agrupa pivotes altos que están prácticamente al mismo precio. Dos o más
máximos alineados son un imán de liquidez: la acumulación de stops justo encima es lo
que suele provocar el barrido.

!!! warning "Devuelve una LISTA, no un DataFrame"
    Un "equal high" es un **grupo** de velas, así que el resultado es
    `list[pd.DataFrame]`: un DataFrame por grupo, cada uno con 2 o más filas. Es la
    única familia de métodos que rompe la forma habitual de salida.

**Requiere.** Depende del método: `max(length * 2 + 1, atr_period + 1)` para
`atr_pivot`, `length * 2 + 1` para `pct_range`.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `3` | Ventana de confirmación del pivote. **Ojo: el default es 3, no 50** |
| `method` | `EqualLevelMethod` | `ATR_PIVOT` | Cómo se decide si dos niveles son "iguales" (ver abajo) |
| `equal_threshold` | `float` | `0.1` | Solo con `atr_pivot`: tolerancia como múltiplo del ATR |
| `atr_period` | `int` | `200` | Solo con `atr_pivot`: periodo del ATR usado como tolerancia |
| `tolerance_pct` | `float` | `0.003` | Solo con `pct_range`: tolerancia como fracción del precio (0.003 = 0,3 %) |
| `include_mitigated` | `bool` | `False` | Si `False`, recorta los miembros ya mitigados del grupo |
| `as_records` | `bool` | `False` | Devolver `list[dict]` en vez de `list[DataFrame]` |
| `search_window` | `int \| None` | `None` | Solo con `pct_range`: limitar los candidatos a las N velas más recientes. `None` = todo el histórico |

### Los dos métodos

=== "`atr_pivot` (default)"

    Compara cada pivote **solo con el inmediatamente anterior** del mismo tipo. La
    tolerancia es `equal_threshold * ATR(atr_period)` en la vela de confirmación, así
    que se adapta sola a la volatilidad del momento.

    Los grupos son siempre de **exactamente 2 miembros**. Es el método que replica
    bit a bit el indicador de referencia.

=== "`pct_range` (proximidad de precio)"

    Agrupa **todos** los pivotes cuyo precio cae dentro de `tolerance_pct` entre sí,
    no solo los adyacentes. El pivote A y el C se agrupan aunque entre ellos haya un
    B a otro precio, y un grupo puede tener 3 o más miembros.

    !!! note "El nombre del enum quedó desactualizado"
        `PCT_RANGE` ya no compara velas crudas por pares: opera sobre pivotes
        confirmados igual que `atr_pivot`. El nombre se mantiene por
        compatibilidad; el comportamiento es "proximidad de precio".

**Devuelve (lista de DataFrames).** Cada grupo son filas del df en las velas de origen
de sus pivotes, más:

| Columna | Tipo | Contenido |
|---|---|---|
| `mitigated` | `bool` | Calculado **por miembro**: si el precio superó ese nivel concreto |

```python
grupos = df.smc.equal_high()
grupos[0][["high", "low", "close", "mitigated"]]
```

```text
               high       low     close  mitigated
date
2026-05-21  78200.0  76719.47  77615.52      False
2026-05-26  78080.0  75677.97  75930.01      False
```

**Devuelve (`as_records=True`).**

| Clave | Tipo | Contenido |
|---|---|---|
| `first_index` / `second_index` | `int` | Posiciones del primer y último miembro |
| `first_time` / `second_time` | etiquetas | Sus timestamps |
| `price` | `float` | Precio medio del grupo — el nivel "igual" |
| `bullish` | `bool` | `False` para equal highs, `True` para equal lows |
| `c1` / `c2` | `float` | Cierres del primer y último miembro |

!!! tip "El filtrado de mitigados recorta miembros, no grupos"
    Si de 3 niveles iguales el primero ya fue mitigado, `include_mitigated=False`
    devuelve el grupo con los otros 2 — no lo descarta entero. Un nivel sigue siendo
    un imán de liquidez aunque uno de sus toques anteriores haya sido superado.

---

## `equal_low`

```python
df.smc.equal_low(...) -> list[pd.DataFrame] | list[dict]
```

Simétrico de [`equal_high`](#equal_high) sobre pivotes bajos. Mismos parámetros,
mismas columnas; en los records, `bullish=True`.

---

## `equal_high_low`

```python
df.smc.equal_high_low(...) -> tuple[list[pd.DataFrame], list[pd.DataFrame]]
```

Ejecuta los dos anteriores de una pasada y devuelve `(altos, bajos)`:

```python
altos, bajos = df.smc.equal_high_low(length=3)
```

Acepta los mismos parámetros que `equal_high` **excepto `as_records`** (si necesitas
registros, llama a los dos métodos por separado).

---

## `fractal`

```python
df.smc.fractal(length: int = 5, include_mitigated: bool = False) -> pd.DataFrame
```

**Qué hace.** Representa cada pivote como una **caja** en vez de como un punto: el
rango completo (`high`/`low`) de la vela de origen, extendido horizontalmente hasta la
vela donde el pivote se confirmó. Es la forma habitual de dibujar fractales y la base
sobre la que se construyen las [zonas de demanda](zonas.md#demand_zone).

**Requiere.** `length * 2 + 1` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `5` | Ventana de confirmación. El default es 5 (fractal clásico), no 50 |
| `include_mitigated` | `bool` | `False` | Incluir los fractales cuyo nivel ya fue superado |

**Devuelve.** Filas del df en las velas de origen, más:

| Columna | Tipo | Contenido |
|---|---|---|
| `top` | `float` | `high` de la vela de origen |
| `bottom` | `float` | `low` de la vela de origen |
| `confirm_time` | etiqueta del índice | Vela donde el pivote se confirmó (origen + `length`) |
| `direction` | `int` | `1` fractal alcista (sobre un swing low, actúa de **soporte**), `-1` bajista (sobre un swing high, **resistencia**) |
| `mitigated` | `bool` | Si el precio ya atravesó el nivel del pivote |

```python
df.smc.fractal(length=5)[["top", "bottom", "confirm_time", "direction", "mitigated"]].head(4)
```

```text
                top   bottom confirm_time  direction  mitigated
date
2017-09-15  3856.00  2817.00   2017-09-20          1      False
2018-12-15  3276.50  3156.26   2018-12-20          1      False
2019-01-29  3443.45  3349.92   2019-02-03          1      False
2019-02-14  3626.40  3568.11   2019-02-19          1      False
```

!!! info "`confirm_time - origen` es exactamente `length`"
    Verificado sobre los 28 fractales de la serie de prueba. Ese desfase constante es
    la prueba de que no hay look-ahead bias: la caja no se puede dibujar antes de
    `confirm_time`.

**Notas.** El contrato `top`/`bottom`/`confirm_time`/`direction` es deliberadamente el
mismo que el de [`ipda_fractal`](proyecciones.md#ipda_fractal) y el de las
[zonas](zonas.md), para que el código de dibujo sea intercambiable entre ellos.
