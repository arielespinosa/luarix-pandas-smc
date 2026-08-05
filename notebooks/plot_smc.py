"""Helpers de ploteo para verificar VISUALMENTE la salida de `pandas_luarix`.

Esto NO es parte de la librería (la librería no dibuja, solo calcula). Vive en
`notebooks/` porque su único propósito es la verificación manual: mirar un gráfico
y decidir si un order block quedó anclado en la vela correcta.

Convención de eje X
-------------------
Todo se dibuja sobre POSICIONES enteras (0..len(df)-1), no sobre fechas. Dos
razones: (1) elimina los huecos de fines de semana / velas faltantes, y (2) hace
que anclar cajas y líneas sea aritmética directa. Las etiquetas del eje se
rellenan con las fechas reales al final.

Uso típico
----------
    from plot_smc import chart, draw_boxes, mark_points

    fig, ax = chart(df, "Order Blocks — BTCUSDT 1d")
    draw_boxes(ax, df, df.smc.order_blocks(length=10), color_by="direction")
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

# Paleta: alcista/bajista + acentos. Pensada para leerse sobre fondo claro.
UP = "#26a69a"
DOWN = "#ef5350"
NEUTRAL = "#78909c"
ACCENT = "#5c6bc0"
WARN = "#ffa726"


def load_ohlc(symbol: str = "BTCUSDT", timeframe: str = "1d", tail: int | None = 260) -> pd.DataFrame:
    """Carga un CSV de `test_data/` con el formato que espera la librería.

    Los CSV traen `date` + `close_time`; la librería solo necesita OHLC(+volume)
    con el tiempo en el índice.
    """
    root = Path(__file__).resolve().parent.parent
    df = pd.read_csv(root / "test_data" / symbol / f"{timeframe}.csv",
                     parse_dates=["date"], index_col="date")
    df = df.drop(columns=[c for c in ("close_time",) if c in df.columns])
    return df.tail(tail) if tail else df


def positions(df: pd.DataFrame, rows: pd.DataFrame | pd.Index) -> np.ndarray:
    """Posiciones enteras de `rows` dentro de `df`.

    Toda la librería devuelve subconjuntos de filas del df original, así que el
    índice de cualquier resultado siempre se puede mapear de vuelta a posiciones.
    """
    idx = rows.index if isinstance(rows, (pd.DataFrame, pd.Series)) else rows
    return df.index.get_indexer(idx)


def chart(df: pd.DataFrame, title: str = "", figsize=(16, 7), volume: bool = False):
    """Velas japonesas sobre eje posicional. Devuelve (fig, ax)."""
    if volume:
        fig, (ax, axv) = plt.subplots(
            2, 1, figsize=figsize, sharex=True,
            gridspec_kw={"height_ratios": [4, 1], "hspace": 0.05},
        )
    else:
        fig, ax = plt.subplots(figsize=figsize)
        axv = None

    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    x = np.arange(len(df))
    up = c >= o

    # Mechas: una línea vertical por vela.
    ax.vlines(x[up], l[up], h[up], color=UP, linewidth=0.8, zorder=2)
    ax.vlines(x[~up], l[~up], h[~up], color=DOWN, linewidth=0.8, zorder=2)

    # Cuerpos: barras desde open hasta close. `bottom` + altura, con un mínimo
    # para que las velas doji sigan siendo visibles.
    height = np.maximum(np.abs(c - o), (h.max() - l.min()) * 0.0008)
    ax.bar(x[up], height[up], bottom=np.minimum(o, c)[up], width=0.7,
           color=UP, edgecolor=UP, linewidth=0.4, zorder=3)
    ax.bar(x[~up], height[~up], bottom=np.minimum(o, c)[~up], width=0.7,
           color=DOWN, edgecolor=DOWN, linewidth=0.4, zorder=3)

    if axv is not None and "volume" in df.columns:
        v = df["volume"].to_numpy(float)
        axv.bar(x[up], v[up], width=0.7, color=UP, alpha=0.6)
        axv.bar(x[~up], v[~up], width=0.7, color=DOWN, alpha=0.6)
        axv.set_ylabel("vol")
        axv.grid(alpha=0.15)

    ax.set_title(title, fontsize=13, loc="left", weight="bold")
    ax.grid(alpha=0.15)
    ax.set_xlim(-1, len(df))
    date_ticks(axv if axv is not None else ax, df)
    return fig, ax


def date_ticks(ax, df: pd.DataFrame, n: int = 10):
    """Reemplaza las posiciones del eje X por fechas legibles."""
    step = max(1, len(df) // n)
    ticks = np.arange(0, len(df), step)
    ax.set_xticks(ticks)
    if isinstance(df.index, pd.DatetimeIndex):
        ax.set_xticklabels([df.index[i].strftime("%Y-%m-%d") for i in ticks],
                           rotation=45, ha="right", fontsize=8)
    else:
        ax.set_xticklabels([str(df.index[i]) for i in ticks], rotation=45, ha="right", fontsize=8)


# --------------------------------------------------------------------------
# Overlays. Cada uno consume la salida TAL CUAL la devuelve el accessor.
# --------------------------------------------------------------------------

def mark_points(ax, df, rows, price_col="high", marker="v", color=ACCENT,
                label=None, size=90, offset_pct=0.01, text_col=None):
    """Marcadores sobre velas concretas (swings, sweeps, divergencias...)."""
    if len(rows) == 0:
        return
    x = positions(df, rows)
    y = rows[price_col].to_numpy(float)
    span = df["high"].max() - df["low"].min()
    dy = span * offset_pct * (1 if marker in ("v", "s") else -1)
    ax.scatter(x, y + dy, marker=marker, s=size, color=color, zorder=6,
               label=label, edgecolors="white", linewidths=0.6)
    if text_col is not None:
        for xi, yi, txt in zip(x, y, rows[text_col].astype(str)):
            ax.annotate(txt, (xi, yi + dy), fontsize=7, ha="center",
                        va="bottom" if dy > 0 else "top", color=color, weight="bold")


def draw_boxes(ax, df, rows, top_col="top", bottom_col="bottom",
               color_by=None, color=ACCENT, extend=None, alpha=0.18,
               label=None, dim_col=None):
    """Cajas rectangulares (order blocks, FVG, fractales, zonas).

    La fila de `rows` es la vela de ORIGEN de la caja. La librería no devuelve
    una vela de cierre, así que por defecto la caja se extiende hasta el borde
    derecho del gráfico -- igual que TradingView dibuja un OB vigente. Pasa
    `extend=N` para limitarla a N velas.

    `dim_col`: columna booleana (`mitigated` / `filled`) que atenúa las cajas ya
    consumidas en vez de ocultarlas -- así se ve que la librería las RETIENE con
    su flag en vez de borrarlas.
    """
    if len(rows) == 0:
        return
    xs = positions(df, rows)
    right = len(df) - 1
    for i, (x0, (_, r)) in enumerate(zip(xs, rows.iterrows())):
        top, bottom = float(r[top_col]), float(r[bottom_col])
        x1 = right if extend is None else min(right, x0 + extend)
        if color_by is not None:
            c = UP if r[color_by] > 0 else DOWN
        else:
            c = color
        dim = bool(r[dim_col]) if dim_col is not None and dim_col in rows.columns else False
        ax.add_patch(Rectangle(
            (x0, bottom), max(x1 - x0, 0.8), top - bottom,
            facecolor=c, edgecolor=c, alpha=alpha * (0.4 if dim else 1.0),
            linewidth=1.2, linestyle=":" if dim else "-", zorder=1,
            label=label if i == 0 else None,
        ))
        # Marca la vela de origen: es EL punto que hay que verificar a ojo.
        ax.plot([x0, x0], [bottom, top], color=c, linewidth=2.0,
                alpha=0.9 if not dim else 0.4, zorder=4)


def draw_level_groups(ax, df, groups, price_col="high", color=WARN, label=None):
    """Grupos de niveles iguales (`equal_high` / `equal_low` -> list[DataFrame]).

    Une con una horizontal los miembros del grupo y marca cada miembro. Verificar
    a ojo = los puntos marcados deben estar todos a la MISMA altura.
    """
    for gi, g in enumerate(groups):
        if len(g) == 0:
            continue
        x = positions(df, g)
        level = float(g[price_col].mean())
        ax.hlines(level, x.min(), x.max(), color=color, linewidth=1.6,
                  linestyle="--", zorder=5, label=label if gi == 0 else None)
        ax.scatter(x, g[price_col].to_numpy(float), marker="o", s=45, color=color,
                   zorder=6, edgecolors="white", linewidths=0.6)
        ax.annotate(f"{level:,.0f}", (x.max(), level), fontsize=7, color=color,
                    va="center", ha="left", weight="bold")


def draw_sweeps(ax, df, sweeps, label=None):
    """Liquidity sweeps: marca la vela del barrido y el nivel barrido."""
    if len(sweeps) == 0:
        return
    x = positions(df, sweeps)
    for i, (xi, (_, r)) in enumerate(zip(x, sweeps.iterrows())):
        lvl = float(r["swept_level"])
        c = DOWN if r["direction"] > 0 else UP
        ax.hlines(lvl, max(0, xi - 25), xi, color=c, linewidth=1.2, alpha=0.7, zorder=5)
        ax.scatter([xi], [lvl], marker="X", s=110, color=c, zorder=7,
                   edgecolors="white", linewidths=0.8,
                   label=label if i == 0 else None)


def draw_structure(ax, df, events, label=None):
    """BOS / CHoCH: etiqueta el evento en la vela donde se confirma la ruptura."""
    if len(events) == 0:
        return
    x = positions(df, events)
    span = df["high"].max() - df["low"].min()
    for i, (xi, (_, r)) in enumerate(zip(x, events.iterrows())):
        bull = r["direction"] > 0
        c = UP if bull else DOWN
        y = float(r["high"] if bull else r["low"])
        dy = span * 0.03 * (1 if bull else -1)
        ax.annotate(str(r["structure_type"]).upper(), (xi, y + dy),
                    fontsize=7.5, color=c, ha="center", weight="bold",
                    va="bottom" if bull else "top")
        ax.vlines(xi, min(y, y + dy), max(y, y + dy), color=c,
                  linewidth=1.0, linestyle=":", zorder=5,
                  label=label if i == 0 else None)


def legend(ax):
    """Leyenda solo si algún artista se registró con `label`."""
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
