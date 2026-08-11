# Instalación

## Como paquete

```bash
pip install pandas-luarix
```

Requiere **Python ≥ 3.11**. Instala tres dependencias de ejecución y nada más:

| Dependencia | Versión mínima | Para qué |
|---|---|---|
| `pandas` | 3.0 | El tipo de dato central y el registro de accessors |
| `numpy` | 2.4 | Todo el cálculo vectorizado y las máscaras booleanas |
| `pandas_ta_classic` | 0.5.44 | Bollinger, EMA, RSI y ATR de `df.indicators` |

!!! note "Ni matplotlib ni requests"
    La librería no dibuja ni descarga nada, así que no arrastra dependencias de
    ploteo ni de red. Eso es deliberado: ver [Qué es y qué no es](../index.md#que-es-y-que-no-es).

## Desde el repositorio (desarrollo)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Windows
.venv/Scripts/python -m pip install -e .
```

`requirements.txt` es solo runtime (espejo de `[project].dependencies`);
`requirements-dev.txt` agrega pytest, jupyterlab y matplotlib para los notebooks
de verificación visual.

Extras declarados en `pyproject.toml`:

```bash
pip install -e ".[dev]"    # tests + notebooks
pip install -e ".[docs]"   # MkDocs Material + mkdocstrings (este sitio)
```

## Verificar la instalación

```python
import pandas as pd
import pandas_luarix

print(pandas_luarix.__version__)

df = pd.DataFrame({
    "open":  [100, 101, 102],
    "high":  [101, 102, 103],
    "low":   [ 99, 100, 101],
    "close": [101, 102, 103],
})
print(hasattr(df, "smc"), hasattr(df, "indicators"), hasattr(df, "analysis"))
# True True True
```

## Tests

```bash
.venv/Scripts/python -m pytest
# 84 passed, 3 skipped
```

Los 3 tests que se saltan comparan bit a bit contra un port Python del indicador
LuxAlgo de Pine que vive en otro repositorio y se usa como **oráculo**. Llevan
`pytest.importorskip`, así que se saltan solos si ese repo no está en el `PYTHONPATH`.
No son deuda técnica: si tocas ATR, order blocks o equal levels, vale la pena correrlos
con el otro repo en el path.

## Construir esta documentación

```bash
.venv/Scripts/python -m pip install -e ".[docs]"
.venv/Scripts/python -m mkdocs serve    # http://127.0.0.1:8000 con recarga en vivo
.venv/Scripts/python -m mkdocs build    # HTML estático en site/
```
