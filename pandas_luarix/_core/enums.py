from enum import Enum


class EqualLevelMethod(str, Enum):
    ATR_PIVOT = "atr_pivot"
    PCT_RANGE = "pct_range"


class ObMitigation(str, Enum):
    CLOSE = "close"
    HIGH_LOW = "high_low"


class VolatilityMethod(str, Enum):
    ATR = "atr"
    CUMULATIVE_MEAN_RANGE = "cumulative_mean_range"


class LiquidityLevels(str, Enum):
    SWINGS = "swings"
    EQUAL_HIGH_LOW = "equal_high_low"
    BOTH = "both"


class ZoneOrigin(str, Enum):
    """Which detected level a demand/supply zone (`_core/zones.py::build_zone`)
    is anchored to. Only FRACTAL is implemented today -- the extensibility
    seam for future origins (e.g. an Order-Block-anchored zone) is
    `build_zone`'s dispatch, not this enum growing alone."""

    FRACTAL = "fractal"


class ZoneSide(str, Enum):
    """Hacia qué lado se proyecta la banda de una zona (`build_zone`).

    SUPPORT (demanda) ancla el borde BAJO del origen y extiende hacia abajo;
    RESISTANCE (oferta) ancla el borde ALTO y extiende hacia arriba.
    """

    SUPPORT = "support"
    RESISTANCE = "resistance"


IPDA_LABELS = {
    "impulse": ("X", "1", "2", "3", "4", "5"),
    "correction": ("X", "A", "B", "C"),
}
