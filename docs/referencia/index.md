# Índice de métodos

Los 24 métodos públicos de la librería. Cada enlace lleva a su ficha completa:
qué hace, qué requiere, qué parámetros acepta y qué columnas devuelve.

## `df.smc` — Smart Money Concepts

### Estructura de mercado

| Método | Qué detecta | Devuelve |
|---|---|---|
| [`swings`](estructura.md#swings) | Todos los pivotes confirmados, high y low | Filas + `swing_type` |
| [`swing_high`](estructura.md#swing_high) | Solo pivotes altos, con estado de mitigación | Filas + `mitigated` |
| [`swing_low`](estructura.md#swing_low) | Solo pivotes bajos, con estado de mitigación | Filas + `mitigated` |
| [`bos_choch`](estructura.md#bos_choch) | Rupturas de estructura (BOS) y cambios de carácter (CHoCH) | Filas + `structure_type`, `direction` |
| [`equal_high`](estructura.md#equal_high) | Grupos de máximos al mismo nivel | `list[DataFrame]` |
| [`equal_low`](estructura.md#equal_low) | Grupos de mínimos al mismo nivel | `list[DataFrame]` |
| [`equal_high_low`](estructura.md#equal_high_low) | Ambos de una pasada | `tuple` de dos listas |
| [`fractal`](estructura.md#fractal) | Pivotes representados como caja con vela de confirmación | Filas + `top`, `bottom`, `confirm_time`, `direction`, `mitigated` |

### Zonas

| Método | Qué detecta | Devuelve |
|---|---|---|
| [`bullish_order_block`](zonas.md#bullish_order_block) | Última vela bajista antes de una ruptura alcista | Filas + `top`, `bottom`, `mitigated` |
| [`bearish_order_block`](zonas.md#bearish_order_block) | Última vela alcista antes de una ruptura bajista | Filas + `top`, `bottom`, `mitigated` |
| [`order_blocks`](zonas.md#order_blocks) | Los dos anteriores concatenados | Filas + `top`, `bottom`, `mitigated`, `direction` |
| [`fair_value_gaps`](zonas.md#fair_value_gaps) | Huecos de 3 velas sin negociar | Filas + `top`, `bottom`, `direction`, `filled` |
| [`demand_zone`](zonas.md#demand_zone) | Banda porcentual anclada a un fractal | Filas + `top`, `bottom`, `direction`, `mitigated` |

### Liquidez

| Método | Qué detecta | Devuelve |
|---|---|---|
| [`liquidity_sweep`](liquidez.md#liquidity_sweep) | Mecha que perfora un nivel y cierra de vuelta (stop hunt) | Filas + `swept_level`, `swept_level_type`, `direction` |

### Régimen de volatilidad

| Método | Qué detecta | Devuelve |
|---|---|---|
| [`expansion`](volatilidad.md#expansion) | Velas cuyo rango supera N × ATR | Filas del df |
| [`consolidation`](volatilidad.md#consolidation) | Ventanas contenidas dentro de N × ATR | Filas del df |

### Proyecciones

| Método | Qué detecta | Devuelve |
|---|---|---|
| [`fib_expansion`](proyecciones.md#fib_expansion) | Objetivos D de patrones A-B-C por ratio de Fibonacci | Tabla de patrones |
| [`ipda_fractal`](proyecciones.md#ipda_fractal) | Expansiones fractales X-1-2-3-4-5 y X-A-B-C | Filas + puntos y metadata de cumplimiento |

## `df.indicators` — Indicadores clásicos

| Método | Qué calcula | Columnas agregadas |
|---|---|---|
| [`bb50`](indicadores.md#bb50) | Bandas de Bollinger | `lower`, `middle`, `upper` |
| [`ema`](indicadores.md#ema) | Media móvil exponencial | `ema` |
| [`rsi`](indicadores.md#rsi) | Relative Strength Index | `rsi` |
| [`atr`](indicadores.md#atr) | Average True Range | `atr` |
| [`stochastic_oscillator`](indicadores.md#stochastic_oscillator) | Oscilador estocástico %K/%D | `slow_k`, `fast_d`, `upper_trigger`, `lower_trigger` |

Estos devuelven el **DataFrame completo** con las columnas agregadas, no un
subconjunto de filas.

## `df.analysis` — Análisis genérico

| Método | Qué detecta | Devuelve |
|---|---|---|
| [`divergence`](analisis.md#divergence) | Divergencias regulares y ocultas entre precio y **cualquier** serie | Filas + 7 columnas del evento |

## Cuánto devuelve cada uno en la práctica

Referencia rápida sobre BTCUSDT diario (3241 velas, 2017-08 a 2026-07), con los
parámetros por defecto salvo donde se indica:

| Llamada | Filas |
|---|---|
| `swings(length=50)` | 46 |
| `swing_high(length=50)` | 2 (sin mitigados) |
| `bos_choch(length=50)` | 19 |
| `equal_high()` | 1 grupo |
| `equal_low()` | 2 grupos |
| `order_blocks(length=50)` | 9 |
| `fair_value_gaps()` | 53 |
| `liquidity_sweep(length=50)` | 7 |
| `fractal(length=5)` | 45 |
| `expansion()` | 330 |
| `consolidation()` | 167 |
| `fib_expansion(length=50)` | 132 (44 patrones × 3 ratios) |
| `ipda_fractal(length=50, mode="both")` | 20 |

Los conteos bajos de `swing_high` no son un error: por defecto se excluyen los niveles
ya mitigados, y en una serie de 9 años casi todos los máximos históricos acabaron
superados. Con `include_mitigated=True` salen los 23.
