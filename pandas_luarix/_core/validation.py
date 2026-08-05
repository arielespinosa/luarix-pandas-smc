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
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"'{name}' must be a positive int, got {value!r}.")


def check_positive_float(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"'{name}' must be a positive number, got {value!r}.")


def check_non_negative_float(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"'{name}' must be a non-negative number, got {value!r}.")
