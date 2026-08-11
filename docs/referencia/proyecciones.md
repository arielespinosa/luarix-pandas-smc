# Proyecciones

Los dos métodos que no describen lo que **pasó** sino lo que la estructura **proyecta**:
objetivos de Fibonacci y patrones de expansión fractal.

Ambos consumen secuencias de swings alternados, así que dependen mucho del `length`: si
no aparece ningún patrón, casi siempre es porque la secuencia de pivotes no tiene la
forma requerida, no porque el detector falle.

---

## `fib_expansion`

```python
df.smc.fib_expansion(
    length: int = 50,
    ratios: tuple[float, ...] = (1.272, 1.414, 1.618),
) -> pd.DataFrame
```

**Qué hace.** Busca patrones A-B-C de tres swings consecutivos alternados y proyecta el
objetivo D para cada ratio de Fibonacci.

| Patrón | Secuencia | Fórmula de D |
|---|---|---|
| Alcista (`direction=1`) | low (A) → high (B) → low (C) | `D = C + (B - A) × ratio` |
| Bajista (`direction=-1`) | high (A) → low (B) → high (C) | `D = C - (A - B) × ratio` |

Se genera una fila **por cada combinación (patrón, ratio)**: con los 3 ratios por
defecto, 44 patrones producen 132 filas.

**Requiere.** `length * 2 + 1` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `50` | Ventana de confirmación de los pivotes |
| `ratios` | `tuple[float, ...]` | `(1.272, 1.414, 1.618)` | Los ratios a proyectar. Puedes pasar los tuyos: `(1.0, 1.618, 2.618)` |

!!! warning "No devuelve filas del df"
    Es una de las dos excepciones al [contrato de salida](../guia/contratos.md#la-forma-general-filas-del-df-columnas-nuevas):
    el resultado es una **tabla de patrones** con su propio índice entero, no un
    subconjunto de velas. Un patrón no "ocurre" en una vela: abarca tres.

**Devuelve.**

| Columna | Tipo | Contenido |
|---|---|---|
| `a_pos`, `b_pos`, `c_pos` | `int` | Posiciones de los tres swings |
| `a_time`, `b_time`, `c_time` | etiquetas del índice | Sus timestamps |
| `a_price`, `b_price`, `c_price` | `float` | Sus precios |
| `ratio` | `float` | El ratio de esta fila |
| `d_price` | `float` | **El objetivo proyectado** |
| `direction` | `int` | `1` alcista, `-1` bajista |

```python
df.smc.fib_expansion(length=50)[
    ["a_price", "b_price", "c_price", "ratio", "d_price", "direction"]
].head(4)
```

```text
    a_price   b_price   c_price  ratio      d_price  direction
0   2817.00  19798.68   6000.01  1.272  27600.70696          1
1   2817.00  19798.68   6000.01  1.414  30012.10552          1
2   2817.00  19798.68   6000.01  1.618  33476.36824          1
3  19798.68   6000.01  11786.01  1.272  -5765.89824         -1
```

!!! danger "Los objetivos pueden ser absurdos, y eso es correcto"
    Fíjate en la fila 3: `d_price = -5765.89`. La proyección es aritmética pura sobre
    la amplitud del impulso; si el impulso fue enorme y el retroceso corto, el objetivo
    sale fuera de todo rango razonable, incluso negativo. **La librería no filtra
    nada**: te da la proyección y tú decides si tiene sentido. Filtra por
    `d_price > 0`, por distancia al precio actual o por lo que corresponda a tu
    estrategia.

**Notas.** Las tripletas se toman **solapadas**: los swings 1-2-3 forman un patrón,
2-3-4 el siguiente, etc. Como los pivotes alternan siempre, prácticamente toda tripleta
consecutiva cumple la condición de alternancia.

---

## `ipda_fractal`

```python
df.smc.ipda_fractal(
    length: int = 50,
    mode: str = "impulse",
    direction: int = 0,
    as_records: bool = False,
) -> pd.DataFrame | list[dict]
```

**Qué hace.** Detecta expansiones fractales estilo IPDA sobre pivotes confirmados. Dos
patrones:

| `pattern` | Puntos | Etiquetas | Qué describe |
|---|---|---|---|
| `"impulse"` | 6 | X, 1, 2, 3, 4, 5 | Tres patas de impulso con dos retrocesos |
| `"correction"` | 4 | X, A, B, C | Dos patas con un retroceso |

### El ruleset híbrido

Esta es la decisión de diseño central del método:

- **La estructura es el filtro DURO.** Solo se emiten patrones cuya secuencia sea
  objetivamente válida (HH/HL para los alcistas, LH/LL para los bajistas). Lo que sale
  del detector es estructuralmente correcto, sin margen de interpretación.
- **Elliott y Fibonacci son METADATA, nunca filtro.** Las reglas de Elliott (retroceso
  de la 2 menor que el 100 % de la 1, la 3 no es la más corta, la 4 no solapa con la 1)
  y las proporciones de Fibonacci se anexan como banderas y como un score
  `compliance` de 0 a 1. **No descartan nada.**

Así el detector no se pelea contigo: te da todos los patrones válidos y tú decides el
corte (`compliance >= 0.66`, `rule4_ok == True`, lo que quieras).

**Requiere.** `length * 2 + 1` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `length` | `int` | `50` | Ventana de confirmación de los pivotes |
| `mode` | `str` | `"impulse"` | `"impulse"`, `"correction"` o `"both"` |
| `direction` | `int` | `0` | `1` solo alcistas, `-1` solo bajistas, `0` ambas |
| `as_records` | `bool` | `False` | Devolver `list[dict]` con los puntos anidados |

**Devuelve (DataFrame).** Filas del df en la vela de origen de **X**, respetando el
contrato de caja de [`fractal`](estructura.md#fractal):

| Columna | Tipo | Contenido |
|---|---|---|
| `pattern` | `str` | `"impulse"` o `"correction"` |
| `direction` | `int` | `1` alcista, `-1` bajista |
| `n_points` | `int` | `6` o `4` |
| `p0_pos` … `p5_pos` | `int` | Posiciones de cada punto (`p0` = X). En correcciones, `p4`/`p5` son nulos |
| `p0_price` … `p5_price` | `float` | Precios de cada punto |
| `p0_time` … `p5_time` | etiquetas | Sus timestamps |
| `top` / `bottom` | `float` | `high` / `low` de la vela de X |
| `confirm_time` | etiqueta | Timestamp del **último** punto (p5 en impulsos, p3 en correcciones) |
| `wave2_retrace` | `float` | Retroceso de la onda 2 como fracción de la 1 (en correcciones: retroceso de B) |
| `wave3_ext` | `float` | Extensión de la onda 3 sobre la 1 (en correcciones: extensión de C) |
| `wave4_retrace` | `float` | Retroceso de la onda 4 sobre la 3 (`NaN` en correcciones) |
| `rule2_ok` | `bool` | La 2 no retrocede el 100 % de la 1 |
| `rule3_ok` | `bool` | La 3 no es la onda más corta |
| `rule4_ok` | `bool` | La 4 no solapa territorio de la 1 |
| `compliance` | `float` | Score 0–1 de cumplimiento (ver abajo) |
| `invalidation_level` | `float` | Precio de X: si el precio lo cruza, la expansión queda negada |
| `invalidated` | `bool` | `True` si algún cierre posterior al último punto ya cruzó ese nivel |

```python
ipda = df.smc.ipda_fractal(length=50, mode="both")
ipda[["pattern", "direction", "n_points", "compliance", "invalidation_level", "invalidated"]].head(4)
```

```text
               pattern  direction  n_points  compliance  invalidation_level  invalidated
date
2018-02-20  correction         -1         4    0.500000            11786.01         True
2018-07-25  correction         -1         4    1.000000             8491.77         True
2018-12-15  correction          1         4    1.000000             3156.26        False
2019-06-26     impulse         -1         6    0.666667            13970.00         True
```

### Cómo se calcula `compliance`

| Patrón | Comprobaciones que puntúan | Denominador |
|---|---|---|
| `impulse` | `rule2_ok`, `rule3_ok`, `rule4_ok`, `wave2_retrace` en [0.382, 0.886], `wave3_ext` ≥ 1.0, `wave4_retrace` en [0.236, 0.618] | 6 |
| `correction` | `wave2_retrace` (retroceso de B) en [0.382, 0.886], `wave3_ext` (extensión de C) ≥ 1.0 | 2 |

!!! warning "En correcciones, `rule3_ok`/`rule4_ok` valen `False` por 'no aplica'"
    Las reglas 3 y 4 de Elliott no tienen sentido en un patrón de 4 puntos, así que se
    reportan como `False` — pero eso significa **no aplicable**, no "la incumple". No
    filtres correcciones por `rule3_ok`. `rule2_ok` sí se calcula de verdad en
    correcciones, aunque no entra en el `compliance`.

**Devuelve (`as_records=True`).** Un formato más cómodo para dibujar, con los puntos
anidados y ya etiquetados:

```python
df.smc.ipda_fractal(length=50, mode="both", as_records=True)[0]
```

```text
{'pattern': 'correction', 'direction': -1, 'compliance': 0.5,
 'invalidated': True, 'invalidation_level': 11786.01,
 'bar_index': 187, 'timestamp': Timestamp('2018-02-20 00:00:00'),
 'points': [{'label': 'X', 'pos': 187, 'price': 11786.01, 'time': ...},
            {'label': 'A', 'pos': 227, 'price': 6430.0,  'time': ...},
            {'label': 'B', 'pos': 261, 'price': 10020.0, 'time': ...},
            {'label': 'C', 'pos': 311, 'price': 5750.0,  'time': ...}]}
```

Las etiquetas salen de `IPDA_LABELS`: `("X","1","2","3","4","5")` para impulsos,
`("X","A","B","C")` para correcciones.

**Notas.**

- **Los pivotes se reducen tipo ZigZag antes de buscar patrones**: dos pivotes
  consecutivos del mismo tipo se colapsan en el más extremo. Eso garantiza ondas
  limpias y alternancia estricta.
- **El índice puede repetirse**: varios patrones distintos pueden compartir la misma X
  (por ejemplo un impulso y una corrección que arrancan en el mismo punto). No uses
  `.loc` sobre el resultado esperando una única fila.
- **Con `length` alto puede devolver 0 filas** aunque haya estructura visible: un
  impulso necesita 6 pivotes alternados consecutivos, y con `length=50` sobre unos
  cientos de velas puede que sencillamente no existan. No es un fallo; baja el `length`.
- Sobre BTCUSDT diario con `length=50`: 5 impulsos y 15 correcciones.
