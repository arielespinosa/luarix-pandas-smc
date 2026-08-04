# Análisis de la Estrategia — Nexora Trading Framework

> Estrategia LONG-only basada en Smart Money Concepts (SMC) sobre temporalidad 4H.
> Contexto macro: datos diarios (annual/semester high/low). Broker: Binance (spot/testnet).

---

## 1. Lógica de Señal — Sistema de Puntuación

La entrada se habilita cuando el score compuesto supera 50 puntos. Máximo alcanzable: 80.

| Condición | Puntos | Función en código |
|---|---|---|
| Equal Lows barridos (liquidez tomada) | 30 | `exist_equals()` → `strategy.py` |
| Order Block sin mitigar debajo del nivel | 20 | `exist_orderblock()` → `strategy.py` |
| Divergencia alcista en estocástico | 15 | `stochastic_oscillator_have_divergence()` |
| Precio ≤ banda inferior BB50 | 10 | `bb50_entry_exist()` |
| Estocástico en sobreventa (slow_k < 20) | 5 | `is_stochastic_oscillator_in_over_sell()` |
| **Máximo** | **80** | Umbral actual: **50** (hardcoded en `pipeline.py:107`) |

**Ventaja real:** La ventaja no viene de BB50 ni del estocástico — esos son filtros de confluencia. La ventaja viene de la liquidez (Equal Lows barridos → 30 pts) y la reacción institucional sobre el Order Block (20 pts). Sin ambos, no hay trade.

---

## 2. Gestión de Entrada — 3 Tranches

Cuando score ≥ 50, se colocan hasta 3 órdenes LIMIT simultáneas:

| Tranche | Capital | Precio de entrada |
|---|---|---|
| Tranche 1 (`entry_first_30`) | 30% | `order_block.top` |
| Tranche 2 (`entry_40`) | 40% | `ob.top - 50% del rango del OB` |
| Tranche 3 (`entry_last_30`) | 30% | `order_block.bottom` |

**Problema detectado:** El código actual en `pipeline.py` lanza las 3 entradas siempre que score ≥ 50. Según `puntuaciones.md`, con score 50-64 deberían usarse solo Tranche 1+2, y con score ≥ 80 la entrada completa. **Esta lógica no está implementada.**

---

## 3. Gestión de Salida — TP/SL

- **Take Profit:** `min(entry_price × 1.06, bb50_middle)` — el más conservador de los dos
- **Stop Loss:** `entry_price × (1 - 0.02)` — 2% debajo de la entrada
- **Stop Limit:** 2.2% debajo (buffer para slippage en órdenes de mercado)
- Implementado como **OCO** (`LIMIT_MAKER` + `STOP_LOSS_LIMIT`) vía Binance API
- El OCO se **actualiza en cada vela 4H** mientras la entrada está abierta (trailing dinámico del TP al BB50 middle)

---

## 4. Contexto IPDA y Estructura de Mercado

El `SMCIndicator` corre sobre datos 4H y calcula:
- **BOS / CHoCH** — cambios de estructura e impulsivos
- **Order Blocks** — zonas institucionales sin mitigar
- **Fair Value Gaps (FVG)**
- **Equal Highs/Lows** — zonas de liquidez
- **Trend Zones** — dirección de tendencia por estructura

El contexto macro (anual/semestral) viene de datos diarios:
- `annual_high / annual_low` — pivots del año en curso
- `semester_high / semester_low` — pivots del semestre

**Fractal de seguridad:** Si el precio rompe el fractal definido al inicio del ciclo, el pipeline aborta todas las entradas pendientes (`tick_broke_fractal()` en `strategy.py:31`).

---

## 5. Deuda Técnica Crítica

| Problema | Ubicación | Impacto |
|---|---|---|
| `get_trend()` devuelve BULLISH hardcoded | `strategy.py:~60` | En tendencia bajista el sistema entraría igualmente |
| Score threshold hardcoded a 50 | `pipeline.py:~107` | No configurable sin tocar código |
| Gestión por bloques según score no implementada | `pipeline.py` | Siempre se abren 3 tranches independientemente del score |
| Score máximo alcanzable es 80, no 100 | `strategy.py` | El sistema de puntuación de `puntuaciones.md` describe 100 pts |

---

## 6. Parámetros Configurables Actuales

Todos en `config/settings.py` y sobreescribibles por `.env`:

```
CAPITAL=1000             # Capital base en USDT
TAKE_PROFFIT_PERCENT=0.06  # 6% take profit
STOP_LOSS_PERCENT=0.02     # 2% stop loss
STOP_LIMIT_PERCENT=0.022   # 2.2% stop limit
ATR_FACTOR=1.2             # Multiplicador ATR para SL alternativo
PIPELINE_SYMBOL=BTCUSDT
PIPELINE_INTERVAL=4h
```

---

## 7. Conversión a TradingView (Pine Script v5)

### Dificultad: MEDIA-ALTA

No es trivial, pero es factible en 1-2 días de trabajo concentrado.

### Lo que ya existe en `docs/`

| Fichero | Estado |
|---|---|
| `docs/smc-luxalgo.pine` | SMC indicator completo (LuxAlgo) — **solo visualización**, no exporta variables |
| `docs/stochastic_oscillator.pine` | Oscilador en Pine Script — reutilizable |

### El problema central

El indicador SMC de LuxAlgo **solo dibuja** — no expone las variables de Order Blocks ni Equal Lows como señales programáticas. Para que `strategy.entry()` pueda actuar sobre ellas, hay que **reimplementar la lógica de detección dentro del script de estrategia**. Se puede copiar y adaptar la lógica de `smc-luxalgo.pine`, pero no es un simple copy-paste.

### Piezas a escribir en Pine Script

```
1. BB50           → ta.bb(close, 50, 2)             ← trivial, 1 línea
2. Estocástico    → ta.stoch(close, high, low, 14)  ← trivial, 2 líneas
3. Detección EQL  → buscar lows con threshold        ← 20-30 líneas
4. Detección OB   → identificar OB sin mitigar       ← 40-60 líneas (extraer de LuxAlgo)
5. Score system   → if/elseif aritmético             ← 20 líneas
6. Contexto IPDA  → request.security() diario/semanal ← 10 líneas
7. Entradas       → strategy.entry() × 3 con qty_percent ← 15 líneas
8. Salidas        → strategy.exit() con limit/stop   ← 10 líneas
```

**Total estimado:** ~200-250 líneas de Pine Script funcional.

### Qué necesitaría para crear el fichero

1. **Confirmar el par y temporalidad** de backtesting (BTCUSDT 4H presumiblemente)
2. **Definir el comportamiento cuando el OB está "mitigado"** — el código Python usa una lógica específica de mitigación que hay que replicar exactamente
3. **Decidir si usar señales de LuxAlgo vía alertas externas** (alternativa más rápida pero menos precisa) o reimplementar la detección internamente (más correcto)
4. Opcional: **Capital inicial y % de comisiones** para que el backtesting sea realista

### Camino más rápido al backtesting

La ruta más directa es un script Pine Script v5 con `strategy()` que:
- Usa `request.security()` para el contexto IPDA
- Reimplementa EQL y OB con la lógica extraída de `smc-luxalgo.pine`
- Usa los indicadores estándar de TradingView para BB50 y Estocástico
- Aplica el score system como condición de entrada
- Gestiona TP/SL con `strategy.exit()`

Este fichero sería **independiente del pipeline Python** — el propósito es validar la lógica de señales en backtesting histórico antes de confiar en el sistema en vivo.
