# API interna (`_core`)

!!! warning "Esto no es la API pública"
    `pandas_luarix._core` son los algoritmos puros sobre los que se apoyan los
    accessors. Se documentan porque son útiles para entender **cómo** se calcula cada
    cosa y para escribir tests, pero **no hay garantía de estabilidad**: sus firmas
    pueden cambiar sin aviso entre versiones. Para uso normal, quédate en
    [`df.smc` / `df.indicators` / `df.analysis`](referencia/index.md).

La regla de arquitectura que estructura el paquete: **`_core/` no conoce los accessors
de pandas; `*/accessor.py` no implementa algoritmos.** Las funciones de aquí reciben
Series y DataFrames y devuelven Series y DataFrames de eventos, así que son testeables
en aislamiento.

---

## Pivotes

::: pandas_luarix._core.pivots

---

## Volatilidad y ATR

::: pandas_luarix._core.volatility

---

## Estructura (BOS / CHoCH)

::: pandas_luarix._core.trend

---

## Niveles iguales

::: pandas_luarix._core.equal_levels

---

## Order blocks

::: pandas_luarix._core.order_blocks

---

## Fair value gaps

::: pandas_luarix._core.fair_value_gaps

---

## Liquidez

::: pandas_luarix._core.liquidity

---

## Divergencias

::: pandas_luarix._core.divergence

---

## Fractales IPDA

::: pandas_luarix._core.fractals

---

## Expansión de Fibonacci

::: pandas_luarix._core.expansion

---

## Zonas

::: pandas_luarix._core.zones

---

## Validación

::: pandas_luarix._core.validation

---

## Enums

::: pandas_luarix._core.enums
