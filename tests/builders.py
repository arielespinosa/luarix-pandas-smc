"""Builders de OHLC sintético con resultados esperados conocidos a mano.

Convenciones de este módulo:

- Cada builder devuelve ``(df, expected)`` donde ``expected`` es un dict con los
  eventos que CADA detector debe producir sobre ese df, expresados en POSICIONES
  (enteros 0-based) para que los tests no dependan del índice temporal.
- Todos los fixtures usan ``length=3`` (pivots compactos) y, cuando aplica ATR,
  ``atr_period=10`` — pásalos explícitamente en los tests, no uses los defaults.
- Las barras se definen solo con (high, low); close = punto medio y
  open = close anterior. Esto hace los cierres deterministas y fáciles de razonar:
  ningún cierre se acerca a los extremos, así que las roturas/mitigaciones solo
  ocurren donde el fixture las provoca a propósito.
- Verificado contra la implementación actual: los pivots, eventos de estructura y
  grupos EQH listados en cada ``expected`` son la salida real de
  ``find_pivots`` / ``track_structure_events`` / ``detect_equal_levels_atr_pivot``.
  Donde el código actual tiene un bug conocido (ventana de escaneo de sweeps),
  ``expected`` describe el comportamiento CORRECTO y el test correspondiente debe
  marcarse ``xfail(strict=True)`` hasta la Fase 3.1.
"""

import numpy as np
import pandas as pd

LENGTH = 3       # lookback de pivots para todos los fixtures de este módulo
ATR_PERIOD = 10  # periodo ATR para todos los fixtures de este módulo


def make_ohlc(bars: list[tuple[float, float]]) -> pd.DataFrame:
    """Construye un df OHLC desde una lista de (high, low).

    close = (high + low) / 2 ; open = close de la barra anterior
    (la primera barra abre en su propio close). Índice horario determinista.
    """
    idx = pd.date_range("2024-01-01", periods=len(bars), freq="1h")
    high = np.array([b[0] for b in bars], dtype=float)
    low = np.array([b[1] for b in bars], dtype=float)
    close = (high + low) / 2.0
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close}, index=idx
    )


def double_top() -> tuple[pd.DataFrame, dict]:
    """Dos pivot highs casi iguales (110 y 109.95) separados por un valle.

    Anatomía (length=3):
      bars 0-2   descenso inicial (el pivot high implícito del bar 0 NO debe
                 emitirse: es el primer flip de leg, sin leg previo — cubre la
                 corrección de asimetría de la Fase 2.1; el código actual tampoco
                 lo emite, por la vía del fillna(0)).
      bar 3      low 95  -> pivot LOW,  confirmado en bar 6
      bar 8      high 110 -> pivot HIGH, confirmado en bar 11   (top 1)
      bar 13     low 97  -> pivot LOW,  confirmado en bar 16    (valle)
      bar 18     high 109.95 -> pivot HIGH, confirmado en bar 21 (top 2)
      bars 22-23 cola sin tocar ningún nivel.

    Por qué es un EQH y nada más:
      - |110 - 109.95| = 0.05. Con atr_period=10 el ATR ronda 6-7, así que la
        tolerancia atr_pivot (0.1 * ATR ≈ 0.65) agrupa ambos tops. En pct sobre
        pivots: 0.05/110 ≈ 0.00045 < 0.003. Ambos métodos deben agrupar.
      - El top 2 queda POR DEBAJO del top 1 a propósito: si lo superara aunque
        cerrase de vuelta, sería además un sweep del nivel 110 y el fixture
        dejaría de ser "solo EQH".
      - Ningún close cruza ningún nivel rastreado -> cero BOS/CHoCH, cero
        mitigaciones, cero sweeps.
    """
    bars = [
        (105, 100), (104, 99), (103, 98),          # 0-2 descenso
        (102, 95),                                  # 3  pivot low (95)
        (103, 96), (104, 97), (105, 98),            # 4-6 confirma low en 6
        (108, 101),                                 # 7
        (110, 103),                                 # 8  pivot high (110), top 1
        (109, 102), (108, 101), (107, 100),         # 9-11 confirma high en 11
        (106, 99),                                  # 12
        (105, 97),                                  # 13 pivot low (97), valle
        (106, 98), (107, 99), (108, 100),           # 14-16 confirma low en 16
        (109, 102),                                 # 17
        (109.95, 103),                              # 18 pivot high (109.95), top 2
        (109, 102), (108, 101), (107, 100),         # 19-21 confirma high en 21
        (106, 99), (105, 98),                       # 22-23 cola limpia
    ]
    df = make_ohlc(bars)
    expected = {
        "pivot_highs": [
            {"origin_pos": 8, "confirmed_pos": 11, "level": 110.0},
            {"origin_pos": 18, "confirmed_pos": 21, "level": 109.95},
        ],
        "pivot_lows": [
            {"origin_pos": 3, "confirmed_pos": 6, "level": 95.0},
            {"origin_pos": 13, "confirmed_pos": 16, "level": 97.0},
        ],
        "structure_events": [],  # ningún close cruza ningún nivel
        "equal_highs": [
            {
                "member_origin_pos": [8, 18],
                "member_confirmed_pos": [11, 21],
                "group_confirmed_pos": 21,   # conocible al confirmar el 2º pivot
                "level_mean": 109.975,
                "mitigated": False,          # mitigated_at = NaT
            }
        ],
        "equal_lows": [],   # |95 - 97| = 2 >> tolerancia
        "sweeps": [],
        "fvgs": [],         # no hay gaps de 3 velas en la serie
    }
    return df, expected


def stop_hunt() -> tuple[pd.DataFrame, dict]:
    """Un swing high confirmado y, más tarde, un wick que lo supera y cierra debajo.

    Anatomía (length=3):
      bar 3      low 95   -> pivot LOW,  confirmado en bar 6
      bar 8      high 112 -> pivot HIGH, confirmado en bar 11
      bars 12-13 deriva bajista
      bar 14     high 113, close 106.5  -> WICK por encima de 112 con cierre de
                 vuelta por debajo: SWEEP bajista (direction -1) del swing high.
      bars 15-16 cola limpia.

    Puntos clave:
      - El sweep ocurre en el bar 14, DESPUÉS de la confirmación del pivot
        (bar 11). Con el código actual (escaneo desde origin_pos + 1 con
        max_confirmation_bars=1) el detector devuelve 0 sweeps: este fixture es
        la demostración canónica del bug de la Fase 3.1. Marcar el test como
        xfail(strict=True) hasta ese fix.
      - El close del bar 14 (106.5) queda por debajo de 112 -> NO es BOS y NO
        mitiga el nivel. Sweep y break deben ser mutuamente excluyentes
        (tracker unificado de la Fase 2.2).
      - El bar 14 no genera pivots nuevos: su posible pivot high confirmaría en
        el bar 17, que no existe.
      - El swing low (95) nunca es barrido ni roto: exactamente 1 sweep total.
    """
    bars = [
        (105, 100), (104, 99), (103, 98),           # 0-2 descenso
        (102, 95),                                   # 3  pivot low (95)
        (103, 96), (104, 97), (105, 98),             # 4-6 confirma low en 6
        (108, 101),                                  # 7
        (112, 104),                                  # 8  pivot high (112)
        (110, 103), (109, 102), (108, 101),          # 9-11 confirma high en 11
        (107, 100), (106, 99),                       # 12-13 deriva
        (113, 100),                                  # 14 STOP HUNT: wick 113 > 112,
                                                     #    close 106.5 < 112
        (106, 99), (105, 98),                        # 15-16 cola limpia
    ]
    df = make_ohlc(bars)
    expected = {
        "pivot_highs": [{"origin_pos": 8, "confirmed_pos": 11, "level": 112.0}],
        "pivot_lows": [{"origin_pos": 3, "confirmed_pos": 6, "level": 95.0}],
        "structure_events": [],  # el close nunca supera 112 ni baja de 95
        "equal_highs": [],
        "equal_lows": [],
        "sweeps": [
            {
                "sweep_pos": 14,
                "swept_level": 112.0,
                "swept_level_type": "swing_high",
                "direction": -1,
                "level_origin_pos": 8,
                "level_confirmed_pos": 11,
            }
        ],
        "fvgs": [],
        "mitigations": [],  # el swing high sigue vivo tras el sweep
    }
    return df, expected
