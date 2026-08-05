import pandas as pd

from pandas_luarix._core.enums import (
    IPDA_LABELS,
    EqualLevelMethod,
    LiquidityLevels,
    ObMitigation,
    VolatilityMethod,
    ZoneOrigin,
)
from pandas_luarix._core.expansion import fib_expansion
from pandas_luarix._core.fair_value_gaps import detect_fair_value_gaps, mark_filled_fvgs
from pandas_luarix._core.fractals import detect_ipda_expansions
from pandas_luarix._core.liquidity import detect_liquidity_sweeps
from pandas_luarix._core.validation import (
    check_non_negative_float,
    check_positive_float,
    check_positive_int,
    require_min_rows,
    validate_ohlc_columns,
)
from pandas_luarix._core.equal_levels import detect_equal_levels_atr_pivot, detect_equal_levels_price_proximity
from pandas_luarix._core.order_blocks import build_order_blocks, mitigate_order_blocks
from pandas_luarix._core.pivots import find_pivots
from pandas_luarix._core.trend import track_structure_events
from pandas_luarix._core.volatility import consolidation_windows, expansion_bars, parsed_high_low
from pandas_luarix._core.zones import build_zone


@pd.api.extensions.register_dataframe_accessor("smc")
class SMCAccessor:
    """Concepts built on top of `structure` primitives: liquidity sweeps, fair value gaps."""

    def __init__(self, df: pd.DataFrame):
        validate_ohlc_columns(df)
        self._df = df

    def _levels_table(self, structure_rows: pd.DataFrame, price_col: str) -> pd.DataFrame:
        if structure_rows.empty:
            return pd.DataFrame({"level_price": [], "origin_pos": []})
        positions = self._df.index.get_indexer(structure_rows.index)
        return pd.DataFrame({"level_price": structure_rows[price_col].to_numpy(), "origin_pos": positions})

    def _levels_table_from_groups(self, groups: list[pd.DataFrame], price_col: str) -> pd.DataFrame:
        if not groups:
            return pd.DataFrame({"level_price": [], "origin_pos": []})
        level_prices = []
        origin_positions = []
        for g in groups:
            level_prices.append(float(g[price_col].mean()))
            last_idx = g.index[-1]
            origin_positions.append(int(self._df.index.get_indexer([last_idx])[0]))
        return pd.DataFrame({"level_price": level_prices, "origin_pos": origin_positions})

    def liquidity_sweep(
        self,
        length: int = 50,
        levels: LiquidityLevels = LiquidityLevels.SWINGS,
        method: EqualLevelMethod = EqualLevelMethod.ATR_PIVOT,
        equal_threshold: float = 0.1,
        atr_period: int = 200,
        tolerance_pct: float = 0.003,
        max_confirmation_bars: int = 50,
    ) -> pd.DataFrame:
        """
        Detects a wick beyond a swing/equal level whose close comes back
        inside it within `max_confirmation_bars` bars — a stop hunt /
        liquidity grab. Builds on `structure` primitives.
        """
        levels = LiquidityLevels(levels)
        check_positive_int("length", length)
        check_positive_int("max_confirmation_bars", max_confirmation_bars)
        df = self._df
        structure = self

        frames = []
        for is_high in (True, False):
            price_col = "high" if is_high else "low"

            if levels in (LiquidityLevels.SWINGS, LiquidityLevels.BOTH):
                rows = (
                    structure.swing_high(length=length, include_mitigated=True)
                    if is_high
                    else structure.swing_low(length=length, include_mitigated=True)
                )
                table = self._levels_table(rows, price_col)
                if not table.empty:
                    sweeps = detect_liquidity_sweeps(
                        df, table, level_price_col="level_price", origin_pos_col="origin_pos",
                        level_type="swing_high" if is_high else "swing_low",
                        is_high=is_high, start_offset=length,
                        max_confirmation_bars=max_confirmation_bars,
                    )
                    if not sweeps.empty:
                        frames.append(sweeps)

            if levels in (LiquidityLevels.EQUAL_HIGH_LOW, LiquidityLevels.BOTH):
                groups = (
                    structure.equal_high(
                        length=length, method=method, equal_threshold=equal_threshold,
                        atr_period=atr_period, tolerance_pct=tolerance_pct, include_mitigated=True,
                    )
                    if is_high
                    else structure.equal_low(
                        length=length, method=method, equal_threshold=equal_threshold,
                        atr_period=atr_period, tolerance_pct=tolerance_pct, include_mitigated=True,
                    )
                )
                table = self._levels_table_from_groups(groups, price_col)
                if not table.empty:
                    # `_levels_table_from_groups` guarda la posición de ORIGEN
                    # del último miembro del grupo (no su confirmación) para
                    # AMBOS métodos -- antes del rediseño de equal_high/low,
                    # el método pct_range comparaba velas crudas sin retraso
                    # de confirmación, así que `start_offset=0` tenía sentido
                    # para ese caso. Ahora Price Proximity (mismo enum
                    # pct_range) también opera sobre pivotes, con el mismo
                    # retraso `length` que ATR Pivot -- este offset condicional
                    # quedó desactualizado y generaba look-ahead bias: un
                    # sweep podía reportarse usando un nivel que el propio
                    # algoritmo todavía no había confirmado en ese momento.
                    # Verificado con un caso aislado antes de este fix.
                    sweeps = detect_liquidity_sweeps(
                        df, table, level_price_col="level_price", origin_pos_col="origin_pos",
                        level_type="equal_high" if is_high else "equal_low",
                        is_high=is_high, start_offset=length,
                        max_confirmation_bars=max_confirmation_bars,
                    )
                    if not sweeps.empty:
                        frames.append(sweeps)

        if not frames:
            return pd.DataFrame(columns=["swept_level", "swept_level_type", "direction"])

        combined = pd.concat(frames).sort_index()
        result = df.loc[combined.index].copy()
        result["swept_level"] = combined["swept_level"].to_numpy()
        result["swept_level_type"] = combined["swept_level_type"].to_numpy()
        result["direction"] = combined["direction"].to_numpy()
        return result

    def fair_value_gaps(
        self,
        min_gap_atr_multiple: float = 0.0,
        atr_period: int = 200,
        include_filled: bool = False,
        as_records: bool = False,
    ) -> pd.DataFrame | list[dict]:
        """
        Classic 3-candle gap. `min_gap_atr_multiple` (default 0.0, i.e. no
        size filter) discards gaps smaller than `min_gap_atr_multiple * ATR(atr_period)`.
        If `as_records=True` returns a list of dicts with keys: top, bottom,
        direction, left_index, right_index, filled, left_time.
        """
        check_non_negative_float("min_gap_atr_multiple", min_gap_atr_multiple)
        check_positive_int("atr_period", atr_period)
        df = self._df
        needed = max(3, atr_period + 1) if min_gap_atr_multiple > 0 else 3
        require_min_rows(df, needed, context="fair_value_gaps")

        fvgs = detect_fair_value_gaps(df, min_gap_atr_multiple=min_gap_atr_multiple, atr_period=atr_period)
        fvgs = mark_filled_fvgs(df, fvgs)

        if fvgs.empty:
            if as_records:
                return []
            result = df.iloc[0:0].copy()
            result["top"] = pd.Series(dtype=float)
            result["bottom"] = pd.Series(dtype=float)
            result["direction"] = pd.Series(dtype=int)
            result["filled"] = pd.Series(dtype=bool)
            return result

        if not include_filled:
            fvgs = fvgs[~fvgs["filled"]]

        if as_records:
            date_index = df.index
            records = []
            for _, row in fvgs.iterrows():
                pos = int(date_index.get_indexer([row.name])[0])
                records.append({
                    "top": row["top"],
                    "bottom": row["bottom"],
                    "direction": int(row["direction"]),
                    "left_index": pos,
                    "right_index": pos,
                    "filled": bool(row["filled"]),
                    "left_time": row.name,
                })
            return records

        result = df.loc[fvgs.index].copy()
        result["top"] = fvgs["top"].to_numpy()
        result["bottom"] = fvgs["bottom"].to_numpy()
        result["direction"] = fvgs["direction"].to_numpy()
        result["filled"] = fvgs["filled"].to_numpy()
        return result

    # ---- Swings ----

    def swings(self, length: int = 50) -> pd.DataFrame:
        """Rows at every confirmed pivot's origin bar (high and low), with a `swing_type` column."""
        check_positive_int("length", length)
        require_min_rows(self._df, length * 2 + 1, context=f"swings(length={length})")
        df = self._df
        pivot_high, pivot_low = find_pivots(df["high"], df["low"], length)

        high_origins = pivot_high.notna().to_numpy().nonzero()[0] - length
        low_origins = pivot_low.notna().to_numpy().nonzero()[0] - length
        high_rows = df.iloc[high_origins].copy()
        high_rows["swing_type"] = "high"
        low_rows = df.iloc[low_origins].copy()
        low_rows["swing_type"] = "low"
        return pd.concat([high_rows, low_rows]).sort_index()

    def _swing_side(self, length: int, is_high: bool, include_mitigated: bool) -> pd.DataFrame:
        check_positive_int("length", length)
        side = "high" if is_high else "low"
        require_min_rows(self._df, length * 2 + 1, context=f"swing_{side}(length={length})")
        df = self._df
        pivot_high, pivot_low = find_pivots(df["high"], df["low"], length)
        pivot = pivot_high if is_high else pivot_low
        confirm_positions = pivot.notna().to_numpy().nonzero()[0]
        close = df["close"].to_numpy()

        rows_idx = []
        mitigated_flags = []
        for confirm_pos in confirm_positions:
            origin_pos = confirm_pos - length
            level = pivot.iloc[confirm_pos]
            seg = close[origin_pos + 1 :]
            mit = (bool((seg > level).any()) if is_high else bool((seg < level).any())) if len(seg) else False
            rows_idx.append(origin_pos)
            mitigated_flags.append(mit)

        if not rows_idx:
            result = df.iloc[0:0].copy()
            result["mitigated"] = pd.Series(dtype=bool)
            return result

        result = df.iloc[rows_idx].copy()
        result["mitigated"] = mitigated_flags
        if not include_mitigated:
            result = result[~result["mitigated"]]
        return result

    def swing_high(self, length: int = 50, include_mitigated: bool = False) -> pd.DataFrame:
        """Rows at confirmed pivot highs; `mitigated`=True once price later closes above the level."""
        return self._swing_side(length, True, include_mitigated)

    def swing_low(self, length: int = 50, include_mitigated: bool = False) -> pd.DataFrame:
        """Rows at confirmed pivot lows; `mitigated`=True once price later closes below the level."""
        return self._swing_side(length, False, include_mitigated)

    # ---- Volatility regime (expansion / consolidation) ----

    def expansion(self, atr_period: int = 200, multiplier: float = 2.0) -> pd.DataFrame:
        """Rows where THIS bar's range (high-low) spiked >= `multiplier` times
        the Wilder ATR of `atr_period` -- a genuine volatility/range
        expansion bar. Same comparison already used internally by Order
        Block filtering, exposed here as its own standalone concept."""
        check_positive_int("atr_period", atr_period)
        check_positive_float("multiplier", multiplier)
        df = self._df
        require_min_rows(df, atr_period + 1, context=f"expansion(atr_period={atr_period})")
        mask = expansion_bars(df["high"], df["low"], df["close"], atr_period=atr_period, multiplier=multiplier)
        return df[mask]

    def consolidation(self, window: int = 10, atr_period: int = 200, multiplier: float = 1.0) -> pd.DataFrame:
        """Rows where the last `window` bars stayed within a total range <=
        `multiplier` times the Wilder ATR of `atr_period` -- price contained,
        not trending. Same ATR baseline as `expansion`, measured over a
        window instead of a single bar."""
        check_positive_int("window", window)
        check_positive_int("atr_period", atr_period)
        check_positive_float("multiplier", multiplier)
        df = self._df
        require_min_rows(
            df, max(window, atr_period) + 1, context=f"consolidation(window={window}, atr_period={atr_period})"
        )
        mask = consolidation_windows(
            df["high"], df["low"], df["close"], window=window, atr_period=atr_period, multiplier=multiplier
        )
        return df[mask]

    # ---- Fibonacci Expansion ----

    def fib_expansion(
        self,
        length: int = 50,
        ratios: tuple[float, ...] = (1.272, 1.414, 1.618),
    ) -> pd.DataFrame:
        """
        Proyecta objetivos de take-profit (D) a partir de patrones A-B-C de
        swings consecutivos.  Cada tripleta alternada (low→high→low o
        high→low→high) genera una expansion por cada `ratio`.

        Devuelve columnas: a_pos, a_price, b_pos, b_price, c_pos, c_price,
        ratio, d_price, direction (1 alcista / -1 bajista).
        """
        check_positive_int("length", length)
        require_min_rows(self._df, length * 2 + 1, context=f"fib_expansion(length={length})")
        df = self._df
        pivot_high, pivot_low = find_pivots(df["high"], df["low"], length)
        result = fib_expansion(pivot_high, pivot_low, length, ratios=ratios)
        if not result.empty:
            date_index = df.index
            result["a_time"] = date_index[result["a_pos"].to_numpy()]
            result["b_time"] = date_index[result["b_pos"].to_numpy()]
            result["c_time"] = date_index[result["c_pos"].to_numpy()]
        return result

    # ---- Equal highs / lows ----

    def _equal_side(
        self,
        length: int,
        method: EqualLevelMethod,
        equal_threshold: float,
        atr_period: int,
        tolerance_pct: float,
        include_mitigated: bool,
        is_high: bool,
        search_window: int | None = None,
    ) -> list[pd.DataFrame]:
        method = EqualLevelMethod(method)
        check_positive_int("length", length)
        check_positive_float("equal_threshold", equal_threshold)
        check_positive_int("atr_period", atr_period)
        check_positive_float("tolerance_pct", tolerance_pct)
        df = self._df
        side = "high" if is_high else "low"
        pivot_high, pivot_low = find_pivots(df["high"], df["low"], length)
        pivot = pivot_high if is_high else pivot_low

        if method is EqualLevelMethod.ATR_PIVOT:
            require_min_rows(
                df, max(length * 2 + 1, atr_period + 1), context=f"equal_{side}(method=atr_pivot)"
            )
            groups = detect_equal_levels_atr_pivot(
                df, pivot, length, atr_period=atr_period, equal_threshold=equal_threshold, is_high=is_high
            )
        else:
            # El nombre histórico del enum (PCT_RANGE) quedó desactualizado --
            # ya no compara velas crudas por pares, agrupa pivotes por
            # cercanía de precio (ver `detect_equal_levels_price_proximity`).
            require_min_rows(df, length * 2 + 1, context=f"equal_{side}(method=price_proximity)")
            groups = detect_equal_levels_price_proximity(
                df, pivot, length, tolerance_pct=tolerance_pct, search_window=search_window, is_high=is_high
            )

        if not include_mitigated:
            # Se recorta por MIEMBRO, no por grupo entero: si de 3 niveles
            # iguales el primero ya fue mitigado antes de que se formara el
            # segundo, el grupo que sigue vigente es el de los otros dos, no
            # "nada" -- ver `detect_equal_levels_price_proximity`.
            trimmed = []
            for g in groups:
                kept = g[~g["mitigated"]]
                if len(kept) >= 2:
                    trimmed.append(kept)
            groups = trimmed
        return groups

    def _groups_to_records(
        self, groups: list[pd.DataFrame], is_high: bool,
    ) -> list[dict]:
        """Convierte grupos de iguales a registros planos."""
        date_index = self._df.index
        price_col = "high" if is_high else "low"
        records = []
        for g in groups:
            records.append({
                "first_index": int(date_index.get_indexer([g.index[0]])[0]),
                "second_index": int(date_index.get_indexer([g.index[-1]])[0]),
                "price": float(g[price_col].mean()),
                "bullish": not is_high,
                "first_time": g.index[0],
                "second_time": g.index[-1],
                "c1": float(g.iloc[0]["close"]),
                "c2": float(g.iloc[-1]["close"]),
            })
        return records

    def equal_high(
        self,
        length: int = 3,
        method: EqualLevelMethod = EqualLevelMethod.ATR_PIVOT,
        equal_threshold: float = 0.1,
        atr_period: int = 200,
        tolerance_pct: float = 0.003,
        include_mitigated: bool = False,
        as_records: bool = False,
        search_window: int | None = None,
    ) -> list[pd.DataFrame] | list[dict]:
        """
        One DataFrame per matched equal-high group, or (if `as_records=True`)
        a list of dicts with keys: first_index, second_index, price, bullish,
        first_time, second_time, c1, c2. `search_window` only applies to
        `method="pct_range"` (see `detect_equal_levels_price_proximity`) --
        `None` (default) searches the entire available history.
        """
        groups = self._equal_side(
            length, method, equal_threshold, atr_period, tolerance_pct, include_mitigated, True,
            search_window=search_window,
        )
        return self._groups_to_records(groups, True) if as_records else groups

    def equal_low(
        self,
        length: int = 3,
        method: EqualLevelMethod = EqualLevelMethod.ATR_PIVOT,
        equal_threshold: float = 0.1,
        atr_period: int = 200,
        tolerance_pct: float = 0.003,
        include_mitigated: bool = False,
        as_records: bool = False,
        search_window: int | None = None,
    ) -> list[pd.DataFrame] | list[dict]:
        """Symmetric to `equal_high`, bearish tolerance direction."""
        groups = self._equal_side(
            length, method, equal_threshold, atr_period, tolerance_pct, include_mitigated, False,
            search_window=search_window,
        )
        return self._groups_to_records(groups, False) if as_records else groups

    def equal_high_low(
        self,
        length: int = 3,
        method: EqualLevelMethod = EqualLevelMethod.ATR_PIVOT,
        equal_threshold: float = 0.1,
        atr_period: int = 200,
        tolerance_pct: float = 0.003,
        include_mitigated: bool = False,
        search_window: int | None = None,
    ) -> tuple[list[pd.DataFrame], list[pd.DataFrame]]:
        return (
            self.equal_high(
                length, method, equal_threshold, atr_period, tolerance_pct, include_mitigated,
                search_window=search_window,
            ),
            self.equal_low(
                length, method, equal_threshold, atr_period, tolerance_pct, include_mitigated,
                search_window=search_window,
            ),
        )

    # ---- BOS / CHoCH ----

    def bos_choch(
        self, length: int = 50, confluence_filter: bool = False, as_records: bool = False,
    ) -> pd.DataFrame | list[dict]:
        """
        Rows at each bar where a BOS or CHoCH fires; columns `structure_type`, `direction`.
        If `as_records=True` returns a list of dicts with keys: structure_type, direction,
        broken_bar_index, broken_time, pivot_bar_index, pivot_level.
        """
        check_positive_int("length", length)
        require_min_rows(self._df, length * 2 + 1, context=f"bos_choch(length={length})")
        df = self._df
        pivot_high, pivot_low = find_pivots(df["high"], df["low"], length)
        events = track_structure_events(df, pivot_high, pivot_low, length, confluence_filter=confluence_filter)

        if events.empty:
            if as_records:
                return []
            result = df.iloc[0:0].copy()
            result["structure_type"] = pd.Series(dtype=object)
            result["direction"] = pd.Series(dtype=int)
            return result

        if as_records:
            date_index = df.index
            records = []
            for _, ev in events.iterrows():
                bi = int(ev["broken_bar_index"])
                records.append({
                    "structure_type": ev["structure_type"],
                    "direction": int(ev["direction"]),
                    "broken_bar_index": bi,
                    "broken_time": date_index[bi],
                    "pivot_bar_index": int(ev["pivot_bar_index"]),
                    "pivot_level": float(ev["pivot_level"]),
                })
            return records

        positions = events["broken_bar_index"].to_numpy()
        result = df.iloc[positions].copy()
        result["structure_type"] = events["structure_type"].to_numpy()
        result["direction"] = events["direction"].to_numpy()
        return result

    # ---- Order blocks ----

    def _order_block_side(
        self,
        length: int,
        ob_mitigation: ObMitigation,
        atr_period: int,
        high_vol_multiplier: float,
        volatility_method: VolatilityMethod,
        confluence_filter: bool,
        include_mitigated: bool,
        direction_wanted: int,
    ) -> pd.DataFrame:
        ob_mitigation = ObMitigation(ob_mitigation)
        volatility_method = VolatilityMethod(volatility_method)
        check_positive_int("length", length)
        check_positive_int("atr_period", atr_period)
        check_positive_float("high_vol_multiplier", high_vol_multiplier)
        df = self._df
        require_min_rows(
            df, max(length * 2 + 1, atr_period + 1), context=f"order_block(length={length}, atr_period={atr_period})"
        )

        pivot_high, pivot_low = find_pivots(df["high"], df["low"], length)
        events = track_structure_events(df, pivot_high, pivot_low, length, confluence_filter=confluence_filter)
        events = events[events["direction"] == direction_wanted]

        parsed_high, parsed_low = parsed_high_low(
            df["high"],
            df["low"],
            df["close"],
            atr_period=atr_period,
            high_vol_multiplier=high_vol_multiplier,
            volatility_method=volatility_method,
        )
        obs = build_order_blocks(df, events, parsed_high, parsed_low)
        obs = mitigate_order_blocks(df, obs, mitigation=ob_mitigation)

        if obs.empty:
            result = df.iloc[0:0].copy()
            result["top"] = pd.Series(dtype=float)
            result["bottom"] = pd.Series(dtype=float)
            result["mitigated"] = pd.Series(dtype=bool)
            return result

        positions = obs["ob_bar_index"].to_numpy()
        result = df.iloc[positions].copy()
        result["top"] = obs["top"].to_numpy()
        result["bottom"] = obs["bottom"].to_numpy()
        result["mitigated"] = obs["mitigated"].to_numpy()
        if not include_mitigated:
            result = result[~result["mitigated"]]
        return result

    def bullish_order_block(
        self,
        length: int = 50,
        ob_mitigation: ObMitigation = ObMitigation.HIGH_LOW,
        atr_period: int = 200,
        high_vol_multiplier: float = 2.0,
        volatility_method: VolatilityMethod = VolatilityMethod.ATR,
        confluence_filter: bool = False,
        include_mitigated: bool = False,
    ) -> pd.DataFrame:
        """Row at the origin (extremum) bar of each bullish order block; columns `top`, `bottom`, `mitigated`."""
        return self._order_block_side(
            length, ob_mitigation, atr_period, high_vol_multiplier, volatility_method,
            confluence_filter, include_mitigated, 1,
        )

    def bearish_order_block(
        self,
        length: int = 50,
        ob_mitigation: ObMitigation = ObMitigation.HIGH_LOW,
        atr_period: int = 200,
        high_vol_multiplier: float = 2.0,
        volatility_method: VolatilityMethod = VolatilityMethod.ATR,
        confluence_filter: bool = False,
        include_mitigated: bool = False,
    ) -> pd.DataFrame:
        """Row at the origin (extremum) bar of each bearish order block; columns `top`, `bottom`, `mitigated`."""
        return self._order_block_side(
            length, ob_mitigation, atr_period, high_vol_multiplier, volatility_method,
            confluence_filter, include_mitigated, -1,
        )

    def order_blocks(
        self,
        length: int = 50,
        ob_mitigation: ObMitigation = ObMitigation.HIGH_LOW,
        atr_period: int = 200,
        high_vol_multiplier: float = 2.0,
        volatility_method: VolatilityMethod = VolatilityMethod.ATR,
        confluence_filter: bool = False,
        include_mitigated: bool = False,
        as_records: bool = False,
    ) -> pd.DataFrame | list[dict]:
        """
        Bullish + bearish order blocks concatenated, with an added `direction` column.
        If `as_records=True` returns a list of dicts with keys: top, bottom, timestamp,
        bar_index, direction, mitigated.
        """
        bullish = self.bullish_order_block(
            length, ob_mitigation, atr_period, high_vol_multiplier, volatility_method, confluence_filter, include_mitigated
        ).copy()
        if not bullish.empty:
            bullish["direction"] = 1
        bearish = self.bearish_order_block(
            length, ob_mitigation, atr_period, high_vol_multiplier, volatility_method, confluence_filter, include_mitigated
        ).copy()
        if not bearish.empty:
            bearish["direction"] = -1

        if as_records:
            df = self._df
            date_index = df.index
            records = []
            for part in (bullish, bearish):
                for _, row in part.iterrows():
                    records.append({
                        "top": row["top"],
                        "bottom": row["bottom"],
                        "timestamp": row.name,
                        "bar_index": int(date_index.get_indexer([row.name])[0]),
                        "direction": row["direction"],
                        "mitigated": row["mitigated"],
                    })
            return records

        return pd.concat([bullish, bearish]).sort_index()

    # ---- Fractal ----

    def fractal(self, length: int = 5, include_mitigated: bool = False) -> pd.DataFrame:
        """
        Fractales (swing highs/lows) representados como caja: `top`/`bottom` =
        high/low de la vela de origen del pivote; horizontal desde esa vela hasta
        la vela de confirmación (`confirm_time`). `direction`: 1 (fractal alcista,
        sobre un swing low — soporte) / -1 (fractal bajista, sobre un swing high —
        resistencia). Pensado como base para representar más adelante fractales
        estilo IPDA sin romper este contrato (top/bottom/horizontal/direction).
        """
        check_positive_int("length", length)
        require_min_rows(self._df, length * 2 + 1, context=f"fractal(length={length})")
        df = self._df
        pivot_high, pivot_low = find_pivots(df["high"], df["low"], length)
        close = df["close"].to_numpy()
        index = df.index

        frames = []
        for is_high, pivot in ((True, pivot_high), (False, pivot_low)):
            confirm_positions = pivot.notna().to_numpy().nonzero()[0]
            rows = []
            for confirm_pos in confirm_positions:
                origin_pos = confirm_pos - length
                level = pivot.iloc[confirm_pos]
                seg = close[origin_pos + 1 :]
                mitigated = (
                    (bool((seg > level).any()) if is_high else bool((seg < level).any())) if len(seg) else False
                )
                origin_row = df.iloc[origin_pos]
                rows.append(
                    {
                        "origin_pos": origin_pos,
                        "top": origin_row["high"],
                        "bottom": origin_row["low"],
                        "confirm_time": index[confirm_pos],
                        "direction": -1 if is_high else 1,
                        "mitigated": mitigated,
                    }
                )
            if rows:
                frames.append(pd.DataFrame(rows))

        if not frames:
            result = df.iloc[0:0].copy()
            result["top"] = pd.Series(dtype=float)
            result["bottom"] = pd.Series(dtype=float)
            result["confirm_time"] = pd.Series(dtype=object)
            result["direction"] = pd.Series(dtype=int)
            result["mitigated"] = pd.Series(dtype=bool)
            return result

        events = pd.concat(frames).sort_values("origin_pos")
        if not include_mitigated:
            events = events[~events["mitigated"]]

        positions = events["origin_pos"].to_numpy()
        result = df.iloc[positions].copy()
        result["top"] = events["top"].to_numpy()
        result["bottom"] = events["bottom"].to_numpy()
        result["confirm_time"] = events["confirm_time"].to_numpy()
        result["direction"] = events["direction"].to_numpy()
        result["mitigated"] = events["mitigated"].to_numpy()
        return result

    def demand_zone(
        self,
        origin: ZoneOrigin | str = ZoneOrigin.FRACTAL,
        length: int = 5,
        side: str = "support",
        offset_pct: float = 0.5,
        include_mitigated: bool = False,
    ) -> pd.DataFrame:
        """Percentage-offset zone band anchored to an origin price level
        (Fractal today; extensible -- see `_core/zones.py::build_zone`)."""
        return build_zone(
            self._df, origin=origin, length=length, side=side,
            offset_pct=offset_pct, include_mitigated=include_mitigated,
        )

    def _attach_point_times(self, result, date_index):
        """Añade p{i}_time por cada p{i}_pos no-NaN (correction deja p4/p5 = NaT)."""
        for i in range(6):
            pos_col = f"p{i}_pos"
            time_col = f"p{i}_time"
            times = pd.Series(pd.NaT, index=result.index, dtype="datetime64[ns]")
            mask = result[pos_col].notna()
            if mask.any():
                pos = result.loc[mask, pos_col].astype(int).to_numpy()
                times.loc[mask] = date_index[pos]
            result[time_col] = times
        return result
 
 
    def ipda_fractal(self, length: int = 50, mode: str = "impulse", direction: int = 0, as_records: bool = False) -> pd.DataFrame:
        """
        Detecta expansiones fractales estilo IPDA sobre pivotes confirmados.
    
        Patrones:
        - impulse    (X-1-2-3-4-5): 6 pivotes, 3 patas de impulso + 2 retrocesos.
        - correction (X-A-B-C):     4 pivotes, 2 patas + 1 retroceso.
    
        Ruleset híbrido: la estructura (HH/HL alcista, LH/LL bajista) es el filtro
        duro; las reglas de Elliott y las proporciones de Fibonacci se anexan como
        metadata de confianza (`compliance` 0..1 + `rule2_ok`/`rule3_ok`/`rule4_ok`),
        nunca como filtro.
    
        Args:
            length: ventana de `find_pivots`.
            mode: "impulse" | "correction" | "both".
            direction: 1 alcista | -1 bajista | 0 ambas.
            as_records: si True devuelve list[dict] con `points` anidado.
    
        DataFrame (fila en la vela de origen de X, respetando el contrato caja de
        `fractal`: top/bottom/confirm_time/direction), columnas añadidas:
            pattern, direction, n_points,
            p0_pos..p5_pos, p0_price..p5_price, p0_time..p5_time  (p0 = X),
            top, bottom, confirm_time,
            wave2_retrace, wave3_ext, wave4_retrace,
            rule2_ok, rule3_ok, rule4_ok, compliance,
            invalidation_level, invalidated.
    
        as_records -> dicts con: pattern, direction, compliance, invalidated,
            invalidation_level, bar_index (X), timestamp (X), y
            points=[{label, pos, price, time}, ...].
        """
        mode = str(mode)
        if mode not in ("impulse", "correction", "both"):
            raise ValueError(f"mode inválido: {mode!r}")
        if direction not in (-1, 0, 1):
            raise ValueError(f"direction inválido: {direction!r}")
        
        print(mode)
        
        check_positive_int("length", length)
        require_min_rows(self._df, length * 2 + 1, context=f"ipda_fractals(length={length})")
        df = self._df
    
        pivot_high, pivot_low = find_pivots(df["high"], df["low"], length)
       
        result = detect_ipda_expansions(
            pivot_high, pivot_low, df["close"], length, mode=mode, direction=direction
        )

    
        if result.empty:
            if as_records:
                return []
            empty = df.iloc[0:0].copy()
            for col, dtype in (
                ("pattern", object), ("direction", int), ("n_points", int),
                ("top", float), ("bottom", float), ("confirm_time", object),
                ("compliance", float), ("invalidation_level", float), ("invalidated", bool),
            ):
                empty[col] = pd.Series(dtype=dtype)
            return empty
    
        date_index = df.index
        result = self._attach_point_times(result, date_index)
    
        if as_records:
            records = []
            for _, row in result.iterrows():
                labels = IPDA_LABELS[row["pattern"]]
                points = [
                    {
                        "label": labels[i],
                        "pos": int(row[f"p{i}_pos"]),
                        "price": float(row[f"p{i}_price"]),
                        "time": row[f"p{i}_time"],
                    }
                    for i in range(len(labels))
                ]
                records.append({
                    "pattern": row["pattern"],
                    "direction": int(row["direction"]),
                    "compliance": float(row["compliance"]),
                    "invalidated": bool(row["invalidated"]),
                    "invalidation_level": float(row["invalidation_level"]),
                    "bar_index": int(row["p0_pos"]),
                    "timestamp": row["p0_time"],
                    "points": points,
                })
            return records
    
        # Fila en la vela de origen de X, con OHLC (contrato caja de `fractal`)
        x_pos = result["p0_pos"].astype(int).to_numpy()
        out = df.iloc[x_pos].copy()
        out["top"] = df.iloc[x_pos]["high"].to_numpy()
        out["bottom"] = df.iloc[x_pos]["low"].to_numpy()
        for col in result.columns:
            out[col] = result[col].to_numpy()
        
        # confirm_time = cierre del patrón (último punto): p5 en impulse, p3 en correction
        last_time = result["p5_time"].where(result["pattern"].eq("impulse"), result["p3_time"])
        out["confirm_time"] = last_time.to_numpy()
        return out
    