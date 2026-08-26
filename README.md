# pandas-luarix

Accessors de `pandas.DataFrame` para análisis de mercado: Smart Money Concepts
(`df.smc`), indicadores técnicos clásicos (`df.indicators`) y análisis genérico
(`df.analysis`).

La librería **no descarga datos ni dibuja gráficos**: recibe un DataFrame OHLC y
devuelve otro DataFrame con las columnas/filas detectadas.

## Instalación

```bash
pip install pandas-luarix
```

Desde el repo, en modo editable:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Windows
```

## Uso

```python
import pandas as pd
import pandas_luarix  # noqa: F401 — el import registra los accessors

df = pd.read_csv("test_data/BTCUSDT/1d.csv", parse_dates=["date"], index_col="date")

df.smc.swings(length=50)                 # pivots HH/HL/LH/LL
df.smc.bos_choch(length=50)              # rupturas de estructura
df.smc.order_blocks()
df.smc.fair_value_gaps()
df.smc.liquidity_sweep()
df.smc.fractal(length=5)
df.smc.ipda_fractal(length=50, mode="impulse")

df.indicators.rsi(length=14)
df.indicators.bb50()
df.indicators.stochastic_oscillator()

rsi = df.indicators.rsi()["rsi"]
df.analysis.divergence(rsi, length=5)
```

El DataFrame de entrada debe tener las columnas `open`, `high`, `low`, `close`
(minúsculas) y estar ordenado cronológicamente.

## Documentación

El sitio completo —qué hace cada método, qué requiere, qué parámetros acepta y qué
columnas devuelve— se construye con MkDocs desde `docs/`:

```bash
.venv/Scripts/python -m pip install -e ".[docs]"
.venv/Scripts/python -m mkdocs serve     # http://127.0.0.1:8000
```

| Página | Qué encontrarás |
|---|---|
| [Primeros pasos](docs/guia/primeros-pasos.md) | De un CSV al primer detector |
| [Contrato de entrada y salida](docs/guia/contratos.md) | Qué se valida, qué devuelve, qué pasa cuando no hay señales |
| [Conceptos y gotchas](docs/guia/conceptos.md) | Asimetría del pivote, confirmación vs origen, mitigación, ATR |
| [Índice de métodos](docs/referencia/index.md) | Los 24 métodos públicos en una tabla |
| [Recetas](docs/recetas.md) | Combinaciones de uso real |

Puedes consultar nuestro notebook de playground [01_pandas_luarix](notebooks/01_pandas_luarix.ipynb). Consulta en el los ejemplos y como reproducirlos con otros activos.

## Tests

```bash
.venv/Scripts/python -m pytest
# 84 passed, 3 skipped
```

Los 3 que se saltan comparan bit a bit contra un port del indicador LuxAlgo que vive en
otro repo y se usa como oráculo; llevan `pytest.importorskip`.

Más detalle de arquitectura y convenciones internas en [AGENT.md](AGENT.md).
