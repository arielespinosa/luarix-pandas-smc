# Re-arquitectura de docs/estrategia_nexora_v2.pine

## Contexto

`docs/estrategia_nexora_v2.pine` fallaba al compilar en TradingView (`Mismatched input ":=" expecting set "="`, línea 213 — reasignación de tupla con `:=`, que Pine no permite). Al revisar si el resto del fichero "se ajusta a la estrategia" real, aparecieron discrepancias arquitectónicas profundas frente a `pipeline.py` + `strategy.py` + `app/tradingview/smc_indicator.py`. Por decisión explícita del usuario, el alcance de esta tarea fue **replicación arquitectónica completa** del motor SMC (no solo el fix de sintaxis), manteniendo el script **LONG-only** (el lado SHORT existe en Python — commit "interpreta shorts" — pero queda fuera de alcance).

`app/tradingview/types.py` documenta que `smc_indicator.py` es una traducción 1:1 semántica del indicador Pine **LuxAlgo Smart Money Concepts**, cuyo código fuente real vive en `docs/smc-luxalgo.pine` (848 líneas). El nuevo `.pine` adapta esa lógica directamente (recortando todo lo visual) en vez de reinventar la detección de estructura desde cero.

> Nota: `docs/analisis_estrategia.md` (análisis previo) está **desactualizado** — describe pesos de score antiguos (máx. 80) y afirma que el motor SMC corre en 4H, cuando en realidad corre sobre **velas diarias**. No usarlo como referencia; este documento y el código son la fuente de verdad actual.

---

## Arquitectura implementada

### Motor SMC diario vía `request.security`

Todo el motor de detección de estructura (legs/pivots, BOS/CHoCH, Order Blocks, Equal Lows/Highs) vive dentro de `f_daily_engine()`, ejecutado vía `request.security(syminfo.tickerid, "D", f_daily_engine(), lookahead = barmerge.lookahead_off)`. El estado persistente (`var`, incluidos `array<float>`/`array<int>`) declarado dentro de esa función vive en el contexto de la vela **diaria**, no del chart 4H — exactamente el comportamiento de `initialize_ipda_target_elements()`, que solo se re-ejecuta cuando cierra una vela diaria nueva.

**Decisión de diseño clave — aplanado a escalares en el límite de `request.security`:** en vez de devolver arrays/UDTs (técnicamente soportado en Pine v6 pero con casuísticas de repintado/identidad documentadas como problemáticas), `f_daily_engine()` devuelve una tupla plana de 17 floats:
- `d_trend` (1 = alcista, -1 = bajista, 0 = sin tendencia aún)
- `d_bb50_mid` (BB50 middle diario, usado en el cálculo de TP)
- 5 pares `ob_top_N`/`ob_bot_N` — Order Blocks sin mitigar (internos + swing combinados), pre-ordenados por `top` descendente
- 5 `eql_N` — Equal Lows activos, más antiguo primero

Las funciones `f_store_ob`/`f_delete_mitigated` (helpers del motor diario) están declaradas en el **ámbito global del script**, no anidadas dentro de `f_daily_engine()` — Pine no permite funciones anidadas (confirmado contra `docs/smc-luxalgo.pine`, donde `storeOrdeBlock`/`deleteOrderBlocks` también están al nivel superior). `f_daily_engine()` las invoca pasando los arrays por referencia.

Internamente, dentro de `f_daily_engine()`, sí se usan `array<float>`/`array<int>` (primitivos) para la contabilidad de Order Blocks/Equal Levels — el aplanado a escalares solo ocurre al construir la tupla de retorno.

5 slots por categoría es un margen documentado, no una garantía matemática de paridad con las listas ilimitadas de Python — ampliable a 10 (2 floats más por slot) si en producción se observa que se llena.

### Piezas portadas desde `docs/smc-luxalgo.pine` (sin dibujo)

| Pine actual | Puerto de |
|---|---|
| `f_leg_*` (inline, 3 variantes: swing=50, internal=5, equal=3) | `leg(int size)` |
| Bloques de pivot bookkeeping (2.2–2.3) | `getCurrentStructure()` |
| Detección Equal Lows/Highs con umbral ATR (2.3, rama equal) | comparación `equalHighsLowsThresholdInput * atrMeasure` |
| Bloque BOS/CHoCH (2.5) | `displayStructure()` |
| `f_store_ob` | `storeOrdeBlock()` |
| `f_delete_mitigated` | `deleteOrderBlocks()` (modo High/Low) |

### Consumo en el lado 4H

- `f_exist_equals_4h`: replica el bucle Python que se detiene en el **primer** nivel que el `low` del tick rompe (aunque resulte en "falso quiebre" y devuelva `na`) — no sigue revisando los siguientes.
- `f_exist_orderblock_4h`: como los slots vienen pre-ordenados por `top` descendente, el primero que cumple `top < equal_price` es automáticamente el máximo (≡ `if ob.top > best.top` en Python).
- `f_calc_strategy_score_4h`: pesos corregidos (Equal Lows +35, Order Block +25, Divergencia +20, Sobreventa estocástico **+15** [antes +10], BB50 +15, bonus tendencia +10). Simplificado LONG-only: la rama BEARISH de Python (que solo alimenta señales SHORT) no se replica — el bloque de entradas se gatea directamente con `d_trend == 1`.
- `f_calc_take_profit`: usa `d_bb50_mid` (diario), no el BB50 del chart 4H — bug corregido respecto a la versión anterior.
- `f_calc_stop_loss`: sin cambios (ya era correcta).

### Piezas de comportamiento añadidas (no existían en ningún diseño previo)

1. **Fractal kill-switch** (Sección 5): inputs `i_fractal_high`/`i_fractal_low` (el usuario los fija manualmente, igual que `Fractal(high=..., low=...)` en `pipeline.py`). Flag persistente irreversible `fractal_broken`, activado si una vela 4H perfora el rango. Gatea todas las entradas nuevas.
2. **Ciclo de cancelación al primer TP** (Sección 6): `comment_profit="TP_HIT"`/`comment_loss="SL_HIT"` en `strategy.exit()`, detección de `strategy.closedtrades.exit_comment(...) == "TP_HIT"` → `strategy.cancel("L1"/"L2"/"L3")` de las tranches aún no llenadas, replicando `context.cancel_pending_entries()` + `context.reset()` de `on_order_status_change`. Ver `docs/plans/bugs.md` sobre la red de seguridad añadida (no es una réplica 1:1 de `all_closed`, ver razón ahí).
3. **`campaign_active`**: flag persistente que reemplaza el guard `strategy.opentrades == 0` (que solo cuenta posiciones llenas) por una semántica equivalente a `context.amount_of_entries > 0` (cuenta las 3 tranches en cuanto se colocan, lleguen o no a llenarse).

### Qué se mantuvo igual

- Declaración `strategy(...)`.
- 3 tranches 30/40/30% a `ob.top` / midpoint / `ob.bottom`.
- Fórmulas de SL/TP en porcentaje.
- Annual/semester high-low: ahora anclado al año/semestre **calendario** real (no rolling 252/126 barras como en una versión intermedia) — se calcula dentro de `f_daily_engine()` y viaja en la misma tupla de `request.security`, en vez de llamadas separadas.
- Estructura general de la visualización (caja OB, línea EQL, plots BB50/IPDA, label de score, bgcolor).

---

## Verificación

Pine Script solo se compila dentro de TradingView — no hay forma de validarlo en este entorno. **Pendiente para el usuario:** pegar `docs/estrategia_nexora_v2.pine` en el editor de Pine de TradingView y confirmar que compila sin errores antes de dar la tarea por cerrada. Ver `docs/plans/bugs.md` para la lista de puntos de mayor riesgo de fallo de compilación a revisar primero si algo falla.
