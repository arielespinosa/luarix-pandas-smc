# Contrato de entrada y salida

Todos los métodos de la librería respetan el mismo contrato. Vale la pena leerlo una
vez: hace que las 24 firmas se comporten de forma predecible.

## Entrada

### Columnas obligatorias

`open`, `high`, `low`, `close`, **en minúscula**. Se validan al construir el accessor
(`df.smc`, `df.indicators`, `df.analysis`), no al llamar al método:

```python
df.drop(columns=["close"]).smc
# ValueError: DataFrame is missing required column(s): ['close'].
#             Expected lowercase OHLC columns ('open', 'high', 'low', 'close').
```

`volume` puede estar o no; ningún detector la usa hoy, pero se conserva en la salida
como cualquier otra columna del df.

### Requisitos del DataFrame

| Requisito | Se valida | Qué pasa si no se cumple |
|---|---|---|
| No vacío | Sí | `ValueError: DataFrame is empty.` |
| Columnas OHLC en minúscula | Sí | `ValueError` con la lista de las que faltan |
| Filas suficientes para el `length`/`atr_period` pedido | Sí | `ValueError` con el mínimo exacto |
| Orden cronológico ascendente | **No** | Resultados sin sentido, sin error |
| Índice único | **No** | Las ramas `as_records` fallan con índice duplicado |
| Sin `NaN` en OHLC | **No** | Los eventos de esas velas simplemente no se emiten |

!!! danger "Los tres últimos son responsabilidad tuya"
    Ordenar y desduplicar el df es barato (`df.sort_index()`, `df[~df.index.duplicated()]`)
    y la librería no lo hace por ti para no ocultar problemas de datos.

### Tipos de parámetros

Los enteros aceptan tanto `int` de Python como enteros de numpy (`np.int64`, etc.).
Los parámetros categóricos son `Enum` de tipo `str`, así que aceptan indistintamente
el miembro o su cadena:

```python
from pandas_luarix import ObMitigation

df.smc.order_blocks(ob_mitigation="close")               # equivalentes
df.smc.order_blocks(ob_mitigation=ObMitigation.CLOSE)

df.smc.order_blocks(ob_mitigation="cierre")
# ValueError: 'cierre' is not a valid ObMitigation
```

Todo valor inválido produce `ValueError`, nunca un `KeyError` crudo ni un resultado
silenciosamente incorrecto. Ver [Enums y parámetros](../referencia/enums.md).

## Salida

### La forma general: filas del df + columnas nuevas

```python
result = df.smc.fair_value_gaps()

set(df.columns) <= set(result.columns)   # True: las originales siguen ahí
result.index.isin(df.index).all()        # True: son filas del df de entrada
df.loc[result.index]                     # el índice sirve para volver al original
```

Esto se cumple para **todos** los detectores de `df.smc` y para `df.analysis.divergence`.
Hay dos excepciones deliberadas, ambas porque su resultado no es "una vela detectada":

| Método | Qué devuelve en su lugar |
|---|---|
| `smc.equal_high` / `equal_low` | `list[DataFrame]` — un DataFrame por grupo de niveles iguales |
| `smc.equal_high_low` | `tuple[list[DataFrame], list[DataFrame]]` |
| `smc.fib_expansion` | Una tabla de patrones A-B-C (una fila por patrón × ratio), con índice propio |

`df.indicators.*` es distinto por naturaleza: devuelve el **DataFrame completo** con
las columnas del indicador agregadas, no un subconjunto de filas.

### El resultado vacío

Cuando no se detecta nada, la salida **no** es `None` ni un DataFrame pelado: es
`df.iloc[0:0]` con las columnas nuevas ya declaradas y con sus dtypes correctos.

```python
sweeps = serie_plana.smc.liquidity_sweep(length=20)
len(sweeps)                    # 0
list(sweeps.columns)           # ['open','high','low','close','swept_level','swept_level_type','direction']
sweeps["swept_level"].dtype    # float64
```

Eso significa que el código de consumo **no necesita un caso especial para "no hubo
señales"**: iterar, filtrar o concatenar sobre el resultado vacío funciona igual.

Las variantes `as_records=True` devuelven `[]` en el mismo caso.

### La columna `direction`

Convención única en toda la librería:

| Valor | Significado |
|---|---|
| `1` | Alcista / demanda / soporte / barrido de un mínimo |
| `-1` | Bajista / oferta / resistencia / barrido de un máximo |

### Las columnas `mitigated` / `filled`

Los elementos ya invalidados por el precio **nunca se borran**: se marcan con una
columna booleana y se retienen. Los parámetros `include_mitigated` / `include_filled`
solo filtran la vista devuelta.

```python
df.smc.order_blocks()                          # solo los vigentes (default)
df.smc.order_blocks(include_mitigated=True)    # también los ya mitigados, con el flag
```

Esto es a propósito: para un backtest necesitas saber **cuándo** un nivel dejó de
valer, no que desaparezca del resultado.

### El índice es opaco

La librería trabaja siempre por posición internamente y traduce a etiquetas con
`df.index[pos]` al final. Un `DatetimeIndex` es lo habitual, pero un `RangeIndex` o
un índice de strings funcionan igual. Las columnas `*_time` (`confirm_time`,
`prior_time`, `p0_time`…) contienen etiquetas del índice, sean del tipo que sean.
