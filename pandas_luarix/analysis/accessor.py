import pandas as pd

from pandas_luarix._core.divergence import detect_divergence
from pandas_luarix._core.validation import check_positive_int, require_min_rows, validate_ohlc_columns

_RESULT_COLUMNS = [
    "divergence_type",
    "direction",
    "price",
    "prior_time",
    "prior_price",
    "indicator_value",
    "prior_indicator_value",
]


@pd.api.extensions.register_dataframe_accessor("analysis")
class AnalysisAccessor:
    """Herramientas de análisis genéricas, no atadas a un indicador concreto."""

    def __init__(self, df: pd.DataFrame):
        validate_ohlc_columns(df)
        self._df = df

    def divergence(self, indicator: pd.Series, length: int = 5) -> pd.DataFrame:
        """
        `indicator` es cualquier serie alineada al mismo índice que el df (RSI,
        MACD, Volume Oscillator, CVD, Momentum, el %K de Stochastic...). Compara
        sus pivotes confirmados contra el precio en esas mismas barras para
        detectar divergencias regulares/ocultas alcistas/bajistas.

        Columnas del resultado (fila = vela del segundo pivote de cada evento):
        `divergence_type` ("regular_bullish"/"hidden_bullish"/"regular_bearish"/
        "hidden_bearish"), `direction` (1 alcista/-1 bajista), `price`,
        `prior_time`, `prior_price`, `indicator_value`, `prior_indicator_value`.
        """
        check_positive_int("length", length)
        require_min_rows(self._df, length * 2 + 1, context=f"divergence(length={length})")
        df = self._df

        events = detect_divergence(df["high"], df["low"], indicator, length)

        if events.empty:
            result = df.iloc[0:0].copy()
            for column in _RESULT_COLUMNS:
                result[column] = pd.Series(dtype=object)
            return result

        positions = events["position"].to_numpy()
        result = df.iloc[positions].copy()
        result["divergence_type"] = events["divergence_type"].to_numpy()
        result["direction"] = events["direction"].to_numpy()
        result["price"] = events["price"].to_numpy()
        result["prior_time"] = df.index[events["prior_position"].to_numpy()]
        result["prior_price"] = events["prior_price"].to_numpy()
        result["indicator_value"] = events["indicator_value"].to_numpy()
        result["prior_indicator_value"] = events["prior_indicator_value"].to_numpy()
        return result
