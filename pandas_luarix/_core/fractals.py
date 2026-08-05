"""
Detección de expansiones fractales estilo IPDA sobre pivotes confirmados.

Dos patrones:
  - impulse  (X-1-2-3-4-5): tramo de 6 pivotes, 3 patas de impulso + 2 retrocesos.
  - correction (X-A-B-C):   tramo de 4 pivotes, 2 patas + 1 retroceso.

Ruleset híbrido (opción C):
  - La *estructura* (secuencia HH/HL alcista o LH/LL bajista) es el filtro DURO:
    solo se emiten expansiones estructuralmente válidas y objetivas.
  - Las reglas de Elliott (retroceso 2 < 100% de 1, onda 3 no la más corta,
    onda 4 sin solape con 1) y las proporciones de Fibonacci se anexan como
    METADATA de confianza (`compliance` 0..1 + flags), nunca como filtro.

Mismo criterio que `_core.expansion.fib_expansion`: recibe `pivot_high`,
`pivot_low` (salida de `find_pivots`, no-NaN en la vela de confirmación; la
vela de origen del swing es `confirm_pos - length`) y devuelve un DataFrame
plano con posiciones/precios por punto + metadata. El accessor añade los `*_time`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Bandas de Fibonacci típicas (solo puntúan; no filtran)
_W2_BAND = (0.382, 0.886)
_W3_MIN_EXT = 1.0
_W4_BAND = (0.236, 0.618)
_C_B_BAND = (0.382, 0.886)  # retroceso B de una corrección

_IMPULSE_COLS = [f"p{i}_pos" for i in range(6)] + [f"p{i}_price" for i in range(6)]
_META_COLS = [
    "pattern", "direction", "n_points",
    "wave2_retrace", "wave3_ext", "wave4_retrace",
    "rule2_ok", "rule3_ok", "rule4_ok",
    "compliance", "invalidation_level", "invalidated",
]


def _alternating_pivots(pivot_high: pd.Series, pivot_low: pd.Series, length: int):
    """Swings ordenados y estrictamente alternados como (origin_pos, price, kind).

    kind: +1 high, -1 low. Los pivotes consecutivos del mismo tipo se colapsan
    conservando el más extremo (máximo más alto / mínimo más bajo), que es la
    reducción tipo ZigZag estándar para obtener ondas limpias.
    """
    highs = pivot_high.to_numpy()
    lows = pivot_low.to_numpy()
    n = len(pivot_high)

    raw: list[tuple[int, float, int]] = []
    for confirm_pos in range(n):
        h = highs[confirm_pos]
        if not np.isnan(h):
            raw.append((confirm_pos - length, float(h), 1))
        lo = lows[confirm_pos]
        if not np.isnan(lo):
            raw.append((confirm_pos - length, float(lo), -1))
    # por origen; ante empate de origen, el low (-1) antes que el high (1)
    raw.sort(key=lambda t: (t[0], t[2]))

    out: list[tuple[int, float, int]] = []
    for op, price, kind in raw:
        if out and out[-1][2] == kind:
            _, prev_price, _ = out[-1]
            if (kind == 1 and price >= prev_price) or (kind == -1 and price <= prev_price):
                out[-1] = (op, price, kind)  # conservar el más extremo
        else:
            out.append((op, price, kind))
    return out


def _score_impulse(prices: list[float], s: int) -> dict:
    """Metadata Elliott/Fib de un impulso. s = +1 alcista / -1 bajista."""
    X, p1, p2, p3, p4, p5 = prices
    w1 = s * (p1 - X)
    len1, len3, len5 = abs(p1 - X), abs(p3 - p2), abs(p5 - p4)

    w2_ret = (s * (p1 - p2)) / w1 if w1 else np.nan
    w3_ext = (s * (p3 - p2)) / w1 if w1 else np.nan
    w4_ret = (s * (p3 - p4)) / (s * (p3 - p2)) if (p3 - p2) else np.nan

    rule2 = s * (p2 - X) > 0                       # retroceso de la 2 < 100% de la 1
    rule3 = not (len3 < len1 and len3 < len5)      # la 3 no es la más corta
    rule4 = s * (p4 - p1) > 0                       # la 4 no solapa territorio de la 1

    checks = [
        rule2,
        rule3,
        rule4,
        (_W2_BAND[0] <= w2_ret <= _W2_BAND[1]) if w2_ret == w2_ret else False,
        (w3_ext >= _W3_MIN_EXT) if w3_ext == w3_ext else False,
        (_W4_BAND[0] <= w4_ret <= _W4_BAND[1]) if w4_ret == w4_ret else False,
    ]
    return {
        "wave2_retrace": float(w2_ret) if w2_ret == w2_ret else np.nan,
        "wave3_ext": float(w3_ext) if w3_ext == w3_ext else np.nan,
        "wave4_retrace": float(w4_ret) if w4_ret == w4_ret else np.nan,
        "rule2_ok": bool(rule2),
        "rule3_ok": bool(rule3),
        "rule4_ok": bool(rule4),
        "compliance": sum(1 for c in checks if c) / len(checks),
    }


def _score_correction(prices: list[float], s: int) -> dict:
    """Metadata de una corrección X-A-B-C. Sin reglas 3/4 (no aplican)."""
    X, A, B, C = prices
    leg = s * (A - X)
    b_ret = (s * (A - B)) / leg if leg else np.nan
    c_ext = (s * (C - B)) / leg if leg else np.nan
    checks = [
        (_C_B_BAND[0] <= b_ret <= _C_B_BAND[1]) if b_ret == b_ret else False,
        (c_ext >= _W3_MIN_EXT) if c_ext == c_ext else False,
    ]
    return {
        "wave2_retrace": float(b_ret) if b_ret == b_ret else np.nan,
        "wave3_ext": float(c_ext) if c_ext == c_ext else np.nan,
        "wave4_retrace": np.nan,
        "rule2_ok": bool(s * (B - X) > 0),
        "rule3_ok": False,
        "rule4_ok": False,
        "compliance": sum(1 for c in checks if c) / len(checks),
    }


def _impulse_ok(p: list[float], s: int) -> bool:
    """Filtro estructural duro de un impulso (HH/HL alcista, LH/LL bajista)."""
    return (
        s * (p[1] - p[0]) > 0 and s * (p[2] - p[0]) > 0 and s * (p[1] - p[2]) > 0
        and s * (p[3] - p[1]) > 0 and s * (p[4] - p[2]) > 0 and s * (p[3] - p[4]) > 0
        and s * (p[5] - p[3]) > 0
    )


def _correction_ok(p: list[float], s: int) -> bool:
    """Filtro estructural duro de una corrección X-A-B-C direccional."""
    return (
        s * (p[1] - p[0]) > 0 and s * (p[2] - p[0]) > 0 and s * (p[1] - p[2]) > 0
        and s * (p[3] - p[1]) > 0 and s * (p[3] - p[2]) > 0
    )


def _invalidated(close_arr: np.ndarray, last_pos: int, x_price: float, s: int) -> bool:
    """True si, tras el último punto, el precio cierra más allá de X (expansión negada)."""
    if last_pos + 1 >= len(close_arr):
        return False
    seg = close_arr[last_pos + 1:]
    return bool((s * (seg - x_price) < 0).any())


def detect_ipda_expansions(
    pivot_high: pd.Series,
    pivot_low: pd.Series,
    close: pd.Series,
    length: int,
    *,
    mode: str = "impulse",
    direction: int = 0,
) -> pd.DataFrame:
    """
    Devuelve un DataFrame plano (una fila por expansión) con columnas:
      pattern, direction, n_points,
      p0_pos..p5_pos, p0_price..p5_price   (p0 = X; correction deja p4/p5 = NaN),
      wave2_retrace, wave3_ext, wave4_retrace,
      rule2_ok, rule3_ok, rule4_ok, compliance,
      invalidation_level, invalidated.

    mode: "impulse" (X12345) | "correction" (XABC) | "both".
    direction: 1 alcista | -1 bajista | 0 ambas.
    """
    pts = _alternating_pivots(pivot_high, pivot_low, length)
    close_arr = close.to_numpy()
    dirs = (1, -1) if direction == 0 else (int(direction),)
    modes = ("impulse", "correction") if mode == "both" else (mode,)

    records: list[dict] = []

    def emit(window, s, pattern):
        prices = [w[1] for w in window]
        positions = [w[0] for w in window]
        if pattern == "impulse":
            if not _impulse_ok(prices, s):
                return
            meta = _score_impulse(prices, s)
            n_points = 6
        else:
            if not _correction_ok(prices, s):
                return
            meta = _score_correction(prices, s)
            n_points = 4
        rec = {"pattern": pattern, "direction": int(s), "n_points": n_points}
        for i in range(6):
            if i < len(positions):
                rec[f"p{i}_pos"] = int(positions[i])
                rec[f"p{i}_price"] = float(prices[i])
            else:
                rec[f"p{i}_pos"] = np.nan
                rec[f"p{i}_price"] = np.nan
        rec.update(meta)
        rec["invalidation_level"] = float(prices[0])
        rec["invalidated"] = _invalidated(close_arr, positions[-1], prices[0], s)
        records.append(rec)

    for s in dirs:
        start_kind = -s  # alcista arranca en low; bajista arranca en high
        for pattern in modes:
            k = 6 if pattern == "impulse" else 4
            for i in range(len(pts) - k + 1):
                if pts[i][2] == start_kind:
                    emit(pts[i:i + k], s, pattern)

    if not records:
        empty = pd.DataFrame(columns=_META_COLS + _IMPULSE_COLS)
        return empty

    result = pd.DataFrame.from_records(records)
    # ordenar por la vela de origen X, como el resto de motores
    return result.sort_values("p0_pos").reset_index(drop=True)