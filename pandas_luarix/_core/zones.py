"""Demand/supply zone construction: a percentage-offset band anchored to an
origin price level. Origin kinds are an extensible dispatch (`ZoneOrigin`) --
Fractal is the only one implemented today; a future Order-Block (or other)
origin plugs in by adding a branch to `build_zone`, not by writing a new
single-purpose zone function."""
from __future__ import annotations

import pandas as pd

from pandas_luarix._core.enums import ZoneOrigin, ZoneSide
from pandas_luarix._core.validation import check_positive_float, check_positive_int


def _zone_from_fractal_row(row: pd.Series, side: ZoneSide, offset_pct: float) -> tuple[float, float, int]:
    """`row` is one row of `.smc.fractal()` (already a top/bottom box).
    `side="support"` (bullish/demand) anchors the LOW edge, band extends
    further DOWN by `offset_pct`; `side="resistance"` (bearish/supply)
    anchors the HIGH edge, band extends further UP. `offset_pct` is a
    PERCENTAGE (0.5 == 0,5 % del precio ancla), no una fracción. Returns
    (bottom, top, direction)."""
    if side is ZoneSide.SUPPORT:
        level = float(row["bottom"])
        band = level * (offset_pct / 100.0)
        return level - band, level, 1
    level = float(row["top"])
    band = level * (offset_pct / 100.0)
    return level, level + band, -1


def build_zone(
    df: pd.DataFrame,
    *,
    origin: ZoneOrigin | str,
    length: int = 5,
    side: ZoneSide | str = ZoneSide.SUPPORT,
    offset_pct: float = 0.5,
    include_mitigated: bool = False,
) -> pd.DataFrame:
    """Dispatches on `origin` -- the extensibility seam for future zone
    origins. Returns the same box contract as `.smc.fractal()`/order
    blocks: rows indexed like `df`, columns `top`/`bottom`/`direction`/
    `mitigated` (plus the original candle columns, same convention as every
    other SMC box detector here).

    NOTE (documented simplification): `mitigated` is passed through
    unchanged from the underlying fractal row -- it reflects whether price
    already crossed the FRACTAL level, not a zone-edge-specific mitigation
    check. A zone-precise mitigation check is a reasonable future
    refinement, not required for this pass."""
    origin = ZoneOrigin(origin)
    # `side` era un str libre: cualquier valor distinto de "support" caía en
    # la rama `resistance` SIN error -- un typo ("suport", "long") devolvía
    # zonas del lado contrario en silencio. Ahora coacciona por Enum, igual
    # que el resto de los categóricos de la librería.
    side = ZoneSide(side)
    check_positive_int("length", length)
    check_positive_float("offset_pct", offset_pct)
    if origin is not ZoneOrigin.FRACTAL:
        raise NotImplementedError(f"Demand zone origin {origin!r} not implemented yet.")

    fractals = df.smc.fractal(length=length, include_mitigated=include_mitigated)
    if fractals.empty:
        result = df.iloc[0:0].copy()
        for col, dtype in (("top", float), ("bottom", float), ("direction", int), ("mitigated", bool)):
            result[col] = pd.Series(dtype=dtype)
        return result

    tops, bottoms, directions = [], [], []
    for _, row in fractals.iterrows():
        bottom, top, direction = _zone_from_fractal_row(row, side, offset_pct)
        bottoms.append(bottom)
        tops.append(top)
        directions.append(direction)

    result = fractals.copy()
    result["top"] = tops
    result["bottom"] = bottoms
    result["direction"] = directions
    return result
