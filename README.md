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
(minúsculas); ver `pandas_luarix/_core/validation.py`.

## Tests

```bash
.venv/Scripts/python -m pytest
```

Más detalle de arquitectura y convenciones en [AGENT.md](AGENT.md).
