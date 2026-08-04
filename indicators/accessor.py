import pandas as pd
import pandas_ta_classic as ta

from pandas_luarix._core.validation import (
    check_positive_float,
    check_positive_int,
    require_min_rows,
    validate_ohlc_columns,
)


@pd.api.extensions.register_dataframe_accessor("indicators")
class IndicatorsAccessor:
    """Indicadores técnicos clásicos (no-SMC): bandas de volatilidad, osciladores."""

    def __init__(self, df: pd.DataFrame):
        validate_ohlc_columns(df)
        self._df = df

    def bb50(self, length: int = 50, std: float = 2.0) -> pd.DataFrame:
        """Bollinger Bands sobre el cierre. Agrega columnas `upper`, `middle`, `lower`."""
        check_positive_int("length", length)
        check_positive_float("std", std)
        require_min_rows(self._df, length, context=f"bb50(length={length})")
        df = self._df
        bb = ta.bbands(df["close"], length=length, std=std)
        result = df.copy()
        result["lower"] = bb.iloc[:, 0]
        result["middle"] = bb.iloc[:, 1]
        result["upper"] = bb.iloc[:, 2]
        return result

    def ema(self, length: int = 20, source: str = "close") -> pd.DataFrame:
        """Media Móvil Exponencial. Agrega columna `ema`. `source` es la
        columna OHLC de entrada (catálogo NodeDefinition "ema" expone
        close/open/high/low)."""
        check_positive_int("length", length)
        require_min_rows(self._df, length, context=f"ema(length={length})")
        df = self._df
        result = df.copy()
        result["ema"] = ta.ema(df[source], length=length)
        return result

    def rsi(self, length: int = 14) -> pd.DataFrame:
        """Relative Strength Index sobre el cierre. Agrega columna `rsi`."""
        check_positive_int("length", length)
        require_min_rows(self._df, length, context=f"rsi(length={length})")
        df = self._df
        result = df.copy()
        result["rsi"] = ta.rsi(df["close"], length=length)
        return result

    def atr(self, length: int = 14) -> pd.DataFrame:
        """Average True Range. Agrega columna `atr`."""
        check_positive_int("length", length)
        require_min_rows(self._df, length, context=f"atr(length={length})")
        df = self._df
        result = df.copy()
        result["atr"] = ta.atr(df["high"], df["low"], df["close"], length=length)
        return result

    def stochastic_oscillator(
        self,
        length: int = 14,
        d_length: int = 3,
        upper_trigger: float = 80.0,
        lower_trigger: float = 20.0,
    ) -> pd.DataFrame:
        """Stochastic Oscillator (%K/%D). Agrega columnas `slow_k`, `fast_d`, `upper_trigger`, `lower_trigger`."""
        check_positive_int("length", length)
        check_positive_int("d_length", d_length)
        require_min_rows(self._df, length + d_length, context=f"stochastic_oscillator(length={length})")
        df = self._df

        low_val = df["low"].rolling(length).min()
        high_val = df["high"].rolling(length).max()
        slow_k = ((df["close"] - low_val) / (high_val - low_val)) * 100
        fast_d = slow_k.rolling(d_length).mean()

        result = df.copy()
        result["slow_k"] = slow_k
        result["fast_d"] = fast_d
        result["upper_trigger"] = upper_trigger
        result["lower_trigger"] = lower_trigger
        return result
