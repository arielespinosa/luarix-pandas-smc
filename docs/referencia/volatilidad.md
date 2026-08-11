# Régimen de volatilidad

Dos métodos complementarios que responden a la misma pregunta —¿el precio está
expandiendo o contenido?— contra la **misma línea base de ATR**, uno vela a vela y el
otro sobre una ventana.

---

## `expansion`

```python
df.smc.expansion(atr_period: int = 200, multiplier: float = 2.0) -> pd.DataFrame
```

**Qué hace.** Devuelve las velas cuyo rango propio (`high - low`) es igual o mayor que
`multiplier` veces el ATR de Wilder. Son las velas de impulso: rupturas, capitulaciones,
reacciones a noticias.

**Requiere.** `atr_period + 1` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `atr_period` | `int` | `200` | Periodo del ATR que sirve de referencia |
| `multiplier` | `float` | `2.0` | Cuántos ATR de rango hacen falta para contar como expansión |

**Devuelve.** Un subconjunto de filas del df, **sin columnas nuevas** — la pertenencia
al resultado *es* la señal.

```python
df.smc.expansion()[["open", "high", "low", "close"]].head(4)
```

```text
               open     high      low    close
date
2018-10-15  6339.34  7680.00  6300.00  6752.50
2019-04-02  4144.54  4897.99  4140.54  4857.29
2019-05-11  6375.16  7343.99  6372.85  7076.22
2019-05-12  7076.24  7521.78  6750.00  6967.31
```

!!! note "Es la misma comparación que filtra los order blocks"
    `expansion` expone como concepto propio el `high_vol_bar` que
    [`bullish_order_block`](zonas.md#bullish_order_block) usa internamente para decidir
    si intercambia `high` y `low`. Con los mismos `atr_period` y `multiplier`, las
    velas marcadas son exactamente las mismas.

---

## `consolidation`

```python
df.smc.consolidation(
    window: int = 10,
    atr_period: int = 200,
    multiplier: float = 1.0,
) -> pd.DataFrame
```

**Qué hace.** Devuelve las velas en las que el recorrido **total** de las últimas
`window` velas (máximo de los `high` menos mínimo de los `low`) cabe dentro de
`multiplier` veces el ATR. El precio estuvo contenido, no tendencial: rango, acumulación,
compresión previa a la ruptura.

**Requiere.** `max(window, atr_period) + 1` filas.

| Parámetro | Tipo | Default | Qué controla |
|---|---|---|---|
| `window` | `int` | `10` | Cuántas velas mira hacia atrás la ventana móvil |
| `atr_period` | `int` | `200` | Periodo del ATR de referencia (el mismo que `expansion`) |
| `multiplier` | `float` | `1.0` | Cuántos ATR puede medir la ventana entera y seguir contando como consolidación |

**Devuelve.** Un subconjunto de filas del df, sin columnas nuevas. La fila marcada es
la **última** de la ventana contenida.

```python
df.smc.consolidation()[["open", "high", "low", "close"]].head(4)
```

```text
               open     high     low    close
date
2018-06-02  7521.01  7697.33  7437.0  7640.03
2018-06-03  7636.81  7786.69  7600.0  7714.26
2018-06-04  7714.26  7760.52  7446.5  7487.00
2018-06-05  7487.00  7679.49  7358.0  7625.00
```

Las consolidaciones salen en **rachas** de velas consecutivas, porque cada vela de un
tramo tranquilo arrastra una ventana igualmente tranquila. Para quedarte con los
tramos en vez de las velas, agrupa por continuidad:

```python
cons = df.smc.consolidation()
pos = df.index.get_indexer(cons.index)
tramos = (pos != pd.Series(pos).shift(1) + 1).cumsum()   # id de racha por fila
```

**Notas.**

- Las primeras `window - 1` velas nunca pueden marcarse: no tienen ventana completa.
- `expansion` y `consolidation` están pensados para leerse juntos, como dos regímenes
  del mismo eje. Con los defaults son mutuamente excluyentes en la práctica, pero no
  por construcción: si subes mucho `multiplier` en `consolidation` puedes hacer que se
  solapen.
