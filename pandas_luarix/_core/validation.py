import numbers

import pandas as pd

REQUIRED_OHLC = ("open", "high", "low", "close")


def validate_ohlc_columns(df: pd.DataFrame, *, require_volume: bool = False) -> None:
    required = REQUIRED_OHLC + (("volume",) if require_volume else ())
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"DataFrame is missing required column(s): {missing}. "
            f"Expected lowercase OHLC{'V' if require_volume else ''} columns {required}."
        )
    if len(df) == 0:
        raise ValueError("DataFrame is empty.")


def require_min_rows(df: pd.DataFrame, needed: int, *, context: str) -> None:
    if len(df) < needed:
        raise ValueError(
            f"{context} requires at least {needed} rows, got {len(df)}."
        )


def check_positive_int(name: str, value: int) -> None:
    # `numbers.Integral` en vez de `int` a propósito: numpy escalares
    # (`np.int64`, el tipo que sale de `len()`-a-numpy, de `.astype(int)` o de
    # cualquier índice posicional calculado con numpy) NO son `int` de Python.
    # Rechazarlos obligaba al llamador a envolver todo en `int(...)` sin ningún
    # beneficio -- son enteros para todos los efectos de esta librería.
    # `bool` sí se rechaza (es `Integral`, pero `length=True` es un error).
    if isinstance(value, bool) or not isinstance(value, numbers.Integral) or value <= 0:
        raise ValueError(f"'{name}' must be a positive int, got {value!r}.")


def check_positive_float(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or value <= 0:
        raise ValueError(f"'{name}' must be a positive number, got {value!r}.")


def check_non_negative_float(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or value < 0:
        raise ValueError(f"'{name}' must be a non-negative number, got {value!r}.")


def check_aligned_series(name: str, series: pd.Series, df: pd.DataFrame) -> None:
    """La serie tiene que compartir EXACTAMENTE el índice del df.

    Sin esta comprobación, pasar una serie más corta (o con otro índice) a
    `analysis.divergence` no lanza nada: los pivotes se detectan sobre las
    posiciones de la SERIE y luego se usan para indexar el DF, así que el
    resultado son filas reales del df pero de las barras equivocadas --
    corrupción silenciosa, no un crash.
    """
    if not isinstance(series, pd.Series):
        raise ValueError(f"'{name}' must be a pandas Series, got {type(series).__name__}.")
    if len(series) != len(df):
        raise ValueError(
            f"'{name}' must be aligned to the DataFrame: got {len(series)} values for {len(df)} rows."
        )
    if not series.index.equals(df.index):
        raise ValueError(
            f"'{name}' must share the DataFrame's index (same labels, same order)."
        )
