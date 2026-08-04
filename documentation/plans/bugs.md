# Bugs y hallazgos importantes

> Cosas ya analizadas — leer antes de volver a investigar el código para no repetir trabajo.

---

## Hero de rendimiento en `/strategy/[id]/backtesting`: progreso grande + "Backtest Performance Score" + botón morado sólido (sesión actual)

El usuario pidió 3 ajustes sobre `/strategy/38/backtesting`: (1) confirmar que las métricas/progreso realmente se muestren bien, (2) el botón Start no encajaba con el diseño (gradiente inventado) — debía ser morado sólido, (3) copiar la estructura de `performance-analytics.html` (template SignalAIX): una fila grande de progreso por encima del grafo de workflow con los elementos más importantes, inspirada en el "Portfolio Performance Score" del template, sacando el gráfico de equity de dentro del panel de tabs.

### Diagnóstico del pedido #1 — no era un bug de backend

`paper_runner.py` (envío de `backtest_progress`/`backtest_trade` por `channel_layer.group_send`) no fue tocado en ninguna sesión reciente — mismo código ya verificado end-to-end (145 mensajes progress, 34 keys, coincide con `BacktestRun` persistido). El problema era de PROMINENCIA visual: el progreso vivía en una barra fina de 4px y las métricas detrás de un click de tab. Solución real: una fila hero grande, imposible de no ver, antes de cualquier tab.

### Investigación del template (agente de exploración sobre `performance-analytics.html`, 1921 líneas)

Hallazgo clave: el template NO tiene un concepto de progreso en vivo (es una página de analytics ya completada) — su "ancla visual" es directamente la card "Portfolio Performance Score": gradiente `emerald-600→teal-700→emerald-800`, `rounded-2xl`, capas decorativas (2 blobs difuminados + grilla de puntos al 6% opacidad), icon-chip + score grande (87.6/100) + badge de rango + subtítulo + chip de tendencia + 4 tiles de ratios (Sharpe/Sortino/Calmar/Recovery Factor, cada uno con ícono/valor/tier/barrita) + un anillo SVG a la derecha duplicando el score + barra de percentil. Todo el texto usa opacidades de blanco (`/90`,`/85`,`/80`,`/75`) en vez de colores separados. El score, el rango ("Top 15%") y la tendencia ("+3.2 vs last month") están **hardcodeados en el HTML del template**, sin cálculo real detrás — ni siquiera ahí son datos reales.

### `lib/backtest/performance-score.ts` (nuevo) — score compuesto propio

`computePerformanceScore(progress: RunProgress | null)`, función pura sin llamada a backend (mismo espíritu que `derived-series.ts`). Sharpe/Sortino/Calmar/Recovery Factor no existen en `BacktestStats` — se reemplazaron por 4 métricas reales que sí tenemos y cumplen el mismo rol de "factor de calidad": Win Rate, Profit Factor, Max Drawdown %, APR, cada una normalizada 0-100 (`barPct`) con su propia fórmula y umbrales de tier (Excellent/Good/Fair/Needs Work); el score final es el promedio de los 4 `barPct`. El sentinel `-100` del bug ya conocido de `avg_monthly_return`/`apr` cae naturalmente en "Needs Work" con barra vacía, sin caso especial. El badge "Top 15%" del template se reemplazó por un tier real derivado del score compuesto; el chip de tendencia fabricado se reemplazó por el Total PnL % real de la corrida.

### `components/builder/workspace/charts/performance-score-ring.tsx` (nuevo)

Mismo patrón Recharts `RadialBarChart`/`ChartContainer` que `risk-gauge.tsx` (sesión anterior), pero círculo completo (`startAngle=90 endAngle=-270`) en vez de semicírculo, en blanco sobre el gradiente morado del hero. A diferencia del semicírculo de `risk-gauge.tsx` (cuyo centro visual cae en la base de su caja, necesitando un `-mt` para el texto superpuesto), un círculo completo es concéntrico con su propia caja — el overlay usa `absolute inset-0` centrado sin necesidad de offset manual.

### `components/builder/workspace/backtest-hero-panel.tsx` (nuevo)

`BacktestHeroPanel({ runStatus, runProgress, equitySeries })` — `return null` si `runStatus === "idle"` (nada que mostrar antes de la primera corrida). Si no, apilado verticalmente dentro de un `@container` (mismo mecanismo de container queries de Tailwind v4 que ya usa esta app en `card.tsx`/`field.tsx`, para que colapse a 1 columna en el panel angosto del builder según el ancho del CONTENEDOR, no del viewport): barra de progreso grande (`h-3`, solo si no completó) → card "Backtest Performance Score" (gradiente morado propio, 3 stops del mismo hue 280 en distinta luminosidad — mismo criterio que el template de variar tono dentro de la MISMA familia de color, no multi-hue) con los 4 factor-tiles + el anillo → `LiveEquityChart` en su propia card, sacado de `LiveBacktestDashboard`.

### `components/builder/workspace/live-backtest-dashboard.tsx` (editado)

Se quitó la barra de progreso fina y el `ElevatedCard` con `LiveEquityChart` que vivían arriba de los tabs — ese contenido se mudó a `BacktestHeroPanel`. El componente pasa a ser solo: badge+executing-label + los 4 tabs (Overview/Returns/Trades/Risk), sin cambios internos en los tabs. `equitySeries` se mantiene en las props (lo siguen usando `monthlyReturns`/`drawdownSeries` dentro de Returns/Risk).

### Montaje del hero (3 lugares, mismos datos que ya recibía cada caller)

- `backtesting-live-workspace.tsx`: insertado entre el header (badge+botones) y el grid `lg:grid-cols-2` (PriceChart|Graph) — literalmente por encima del grafo de workflow.
- `backtesting-workspace.tsx` (Results): insertado arriba del `PriceChart`, con `runStatus="completed"`.
- `builder-info-panel.tsx` (panel docked del builder): insertado al inicio del `TabsContent value="backtesting"` (que pasó de `"min-h-0 flex-1"` a `"flex min-h-0 flex-1 flex-col"`, mismo patrón que el tab "output"), en un `div shrink-0` antes de `LiveBacktestDashboard`.

### Botón Start — morado sólido

Se quitó el `className` con degradado (`bg-gradient-to-r from-accent-primary to-accent-blue ...`). `--primary`/`--accent-primary` en `app/globals.css` YA SON el morado de marca de la app (`oklch(0.54 0.23 280)`) — el `<Button>` por defecto (`variant="default"`) ya renderiza `bg-primary text-primary-foreground`, el mismo morado sólido que el resto de botones primarios del repo (confirmado por grep: ningún otro botón usa gradiente). Se dejó `size="lg"` para mantenerlo grande/prominente.

### Verificado

`npx tsc --noEmit` limpio. `eslint` limpio en los 7 archivos nuevos/tocados — los 2 hallazgos que aparecen (`backtesting-workspace.tsx`, `builder-info-panel.tsx`) son el mismo patrón preexistente `react-hooks/set-state-in-effect` ya documentado en sesiones anteriores, no líneas tocadas por este cambio. Django (puerto 8000) y Next.js (puerto 3000) confirmados alcanzables.

**Pendiente**: sin navegador/Playwright disponible en este entorno, no se pudo hacer un recorrido real en vivo (click en Start, ver la barra grande avanzar, la card del score actualizarse con valores reales, el anillo, el chip de Total PnL %, el equity creciendo) — verificado solo por tipos/código (todos los `BacktestHeroPanel` reciben exactamente `runner.progress`/`runner.equitySeries` o los equivalentes adaptados de una corrida completa, sin discrepancia de forma). Recomendado que el usuario haga una corrida real y confirme visualmente.

---

## Fix: el tab Live "lanzaba" un backtest solo con entrar a la página (sesión actual)

Tras hacer Live el tab por defecto y siempre visible (sección anterior), el usuario reportó que entrar a `/strategy/[id]/backtesting` ya mostraba un backtest corriendo, sin haber tocado Start.

**Causa real**: no era un lanzamiento nuevo (ningún `launchBacktest()` se disparaba solo) — era el efecto de auto-attach en `components/builder/workspace/backtesting-view-toggle-panel.tsx` (construido en una sesión anterior para reflejar una corrida lanzada desde el builder): al montar, buscaba en `useBacktestRunsList` cualquier run `running`/`paused` YA EXISTENTE en la BD para esa estrategia (por ejemplo, una corrida vieja de pruebas de sesiones anteriores que nunca se detuvo explícitamente) y se auto-conectaba a ella (`runner.attach(...)`) sin ninguna acción del usuario. Antes de que Live fuera el tab por defecto esto pasaba desapercibido (había que cambiar de tab manualmente para verlo); al quedar siempre visible, se veía indistinguible de "la página lanza un backtest sola".

**Fix**: se eliminó por completo el efecto de auto-attach (y el `useBacktestRunsList`/`useBuilderStore.nodes` que solo existían para él, y el efecto de auto-switch-a-Live que dependía de `isLive`, ya redundante con Live siendo el tab por defecto). También se eliminó `attach()` de `hooks/useBacktestRun.ts` (quedó sin ningún caller tras el fix — se confirmó con grep antes de borrar). Ahora una corrida solo empieza cuando el usuario hace click explícito en el botón Start; si hay una corrida ya activa en la BD para esta estrategia (lanzada en otra pestaña/sesión), esta página ya no la refleja automáticamente — limitación conocida, aceptada explícitamente por el pedido del usuario de que nada corra sin click directo.

Verificado: `npx tsc --noEmit` y `eslint` limpios en los 3 archivos tocados (`backtesting-view-toggle-panel.tsx`, `hooks/useBacktestRun.ts`, sin cambios adicionales en `backtesting-live-workspace.tsx`) — sin ningún hallazgo, ni siquiera el `react-hooks/set-state-in-effect` preexistente (el efecto que lo disparaba, resolución de `backendStrategyId`, se eliminó por completo junto con el auto-attach que lo necesitaba).

---

## Backtesting page: tab Live primero + botón Start/Pause/Resume/Stop unificado

Dos pedidos sobre `/strategy/[id]/backtesting`:

1. El orden de tabs pasa de Results/Graph/Live a **Live / Graph / Results** — Live ahora es el primero y ya no está gateado a que haya una corrida activa (antes `showLive` solo agregaba el tab si `runner.status !== "idle"`). `components/builder/workspace/backtesting-view-toggle-panel.tsx`: `VIEWS` reemplaza a `BASE_VIEWS`/`LIVE_VIEW`, `BacktestViewToggle` perdió el prop `showLive` (siempre muestra los 3), `view` arranca en `"live"` en vez de `"results"`. (El efecto de auto-switch-a-Live-en-flanco-de-subida que originalmente se mantuvo aquí se terminó eliminando poco después — ver la sección siguiente, "el tab Live lanzaba un backtest solo con entrar a la página".)

2. El botón "Run backtest" del header (CTA grande, sesión anterior) y los botones Pause/Resume/Stop (que vivían dentro de `BacktestingLiveWorkspace`, solo visibles cuando `isLive`) estaban separados en dos componentes distintos. Se unificaron en un solo control de un botón que cambia de label/acción según `runner.status` — mismo patrón ya usado en `builder-toolbar.tsx` (Run→Pause+Stop→Resume+Stop): idle/completed/failed/cancelled → **Start** (gradiente, abre el `BacktestConfigForm` inline, igual que antes); running/pending → **Pause**; paused → **Resume**; running/paused → **Stop** además. Todo movido a `components/builder/workspace/backtesting-live-workspace.tsx` (que ahora también posee el estado `configOpen` y el `ElevatedCard` con el form, antes en el panel padre) — `backtesting-view-toggle-panel.tsx` quedó solo con el toggle de vista, sin lógica de control de la corrida.

Como Live ya no está gateado a `isLive`, el tab siempre muestra algo razonable: `LiveBacktestDashboard` ya renderizaba un estado idle explícito ("Run the strategy to see live backtest progress here") cuando `runStatus === "idle"`, así que no hizo falta un placeholder nuevo.

Verificado: `npx tsc --noEmit` limpio; `eslint` limpio salvo el mismo hallazgo preexistente `react-hooks/set-state-in-effect` en el efecto de `backendStrategyId` (ya documentado como patrón replicado deliberadamente en este subsistema, no una regresión).

---

## Rediseño visual del dashboard de backtesting (SignalAIX) + botón Run + skill

El usuario pidió: (1) un botón para correr el backtest desde `/strategy/[id]/backtesting` (ya existía, pero pasaba desapercibido — outline, chico); (2) mejorar sustancialmente la UI inspirándose en el template ThemeForest SignalAIX (tabs Overview/Returns/Trades/Risk, más tipos de gráfico — velas, pastel, línea, burbuja); (3) analizar el código fuente real del template (`C:\Users\Ariel\Downloads\buyer-file\main-file`, no solo el preview) para tenerlo como referencia futura, opcionalmente como Skill.

### Investigación del template real (3 agentes en paralelo, ~33k líneas CSS/JS/HTML)

- Librería de gráficos: **Chart.js 4.x**, no Recharts — se reimplementó con Recharts (stack ya establecido en este repo), no se portó nada literal.
- Pese a tener iconos "candlestick"/"bubble"/"scatter" en su set de iconos, **ningún gráfico real de esos tipos existe en el template** — son solo SVGs decorativos sin chart detrás. El gráfico de burbujas (riesgo/recompensa por operación) y el de retornos mensuales (el template solo tiene un stub con un `toast`, nunca lo construyó) se diseñaron desde cero en esta sesión.
- Paleta (verde `#10b981` profit/win, rojo `#ef4444` loss, ámbar riesgo moderado) mapea 1:1 con los tokens OKLCH que la app ya tenía (`--profit`/`--loss`/`--chart-1..5`/`--accent-primary/blue/gold/magenta` en `app/globals.css`) — no se importó paleta nueva.
- Arquitectura de tabs para un análisis de una sola corrida: **Overview / Returns / Trades / Risk** (el template usa también Strategies/Assets, pero esos aplican a un portfolio multi-estrategia, fuera de alcance aquí).

### Frontend — nuevos archivos

- `lib/backtest/derived-series.ts`: `monthlyReturns(series)` y `drawdownSeries(series)`, funciones puras sobre `EquityPoint[]` (ya disponible en vivo por WS o reconstruida desde `equity_curve` de una corrida completa) — sin ningún cambio de backend, son transformaciones client-side de datos que ya viajaban.
- `lib/backtest/trade-adapter.ts`: 4 adaptadores nuevos — `tradeToLiveTrade`, `equityCurveToPoints`, `parseDrfDuration` (parsea el formato `"[DD ]HH:MM:SS[.ffffff]"` de un DRF `DurationField` a segundos), y `backtestRunToProgress(run): RunProgress` — el pegamento clave: mapea un `BacktestRun` persistido a la MISMA forma canónica (`RunProgress`) que ya produce el WebSocket en vivo, permitiendo que un solo componente renderice tanto una corrida en curso como una ya terminada.
- `components/builder/workspace/charts/`: 6 componentes Recharts nuevos, todos vía el `ChartContainer`/`ChartConfig` ya establecido — `win-loss-donut-chart.tsx`, `long-short-donut-chart.tsx`, `monthly-returns-bar-chart.tsx`, `drawdown-chart.tsx` (área invertida, relleno `--loss`), `risk-gauge.tsx` (semicírculo `RadialBarChart` 180°, color verde→ámbar→rojo según `maxDrawdownPct`), `trade-risk-reward-chart.tsx` (scatter/burbuja: x=horas en posición, y=PnL%, tamaño=|PnL| absoluto — sin precedente en el template, diseño propio).
- `.claude/skills/signalaix-design/SKILL.md`: referencia condensada (paleta→tokens, receta de KPI-tile/badge/tabla, tabla "qué chart usar para qué dato", convención de tabs), con puntero al código fuente real del template para consultas futuras más profundas. Alcance: cualquier página futura con espíritu de dashboard financiero, no solo backtesting.

### `components/builder/workspace/live-backtest-dashboard.tsx` — reestructurado en 4 tabs

Las 5 `MetricsSection` planas (Overview/Trades/Risk/Streaks/Returns, sesión anterior) se reagruparon en 4 tabs (`Tabs`/`TabsList`/`TabsTrigger`/`TabsContent`, mismo componente ya usado en `builder-info-panel.tsx`) — Streaks se fusionó dentro de Risk:
- **Overview**: `LiveEquityChart` (hero) + KPIs (capital final/PnL/fees/trades) + `WinLossDonutChart` + `LongShortDonutChart` lado a lado + Open Positions (oculto si `runStatus === "completed"`).
- **Returns**: KPIs (avg monthly return/APR/trades per day) + `MonthlyReturnsBarChart`.
- **Trades**: los 12 tiles ya existentes + `TradeRiskRewardChart` + tabla de entradas.
- **Risk**: KPIs de riesgo + rachas (fusionadas) + `DrawdownChart` + `RiskGauge`.

Cada tab tiene un acento de color propio vía `StatWidget.accent` (antes sin usar en este componente): Overview→`primary`, Returns→`gold`, Trades→`blue`, Risk→`magenta` — mismo espíritu que los icon-chips en gradiente del template, con los tokens propios de la app. Cada tile ganó también un ícono Hugeicons acorde a la métrica.

**Caveat sin verificar visualmente** (sin navegador/Playwright disponible en este entorno): el offset `-mt-14` del texto superpuesto en `RiskGauge` es una aproximación de código, no confirmada contra un render real — revisar si el número se ve descentrado.

### Botón "Run backtest" — CTA prominente

`components/builder/workspace/backtesting-view-toggle-panel.tsx`: mismo botón, mismo lugar (header), pero ahora `bg-gradient-to-r from-accent-primary to-accent-blue`, texto blanco, ícono `PlayIcon`, sombra de color (`shadow-md shadow-accent-primary/30`) — ya no pasa desapercibido.

### Unificación del modo Results

`components/builder/workspace/backtesting-workspace.tsx`: reemplazado `BacktestSummaryFromRun` + tabla de trades plana con búsqueda, por el mismo `LiveBacktestDashboard` (alimentado con `backtestRunToProgress(run)` + `equityCurveToPoints(run.equity_curve)` + trades mapeados vía `tradeToLiveTrade`, `runStatus="completed"` para ocultar la barra de progreso y Open Positions). El `PriceChart` (velas + marcadores) arriba no se tocó. Con `BacktestSummaryFromRun` sin ningún otro consumidor, se borró `components/builder/workspace/backtest-summary.tsx` (confirmado sin imports restantes antes de borrar).

### Verificado

`npx tsc --noEmit` limpio. `eslint` limpio en todos los archivos nuevos/tocados de esta sesión — los 4 hallazgos de `react-hooks/set-state-in-effect` en el árbol `components/builder/workspace/` son preexistentes (confirmado con `git stash`+`eslint` que uno de ellos, en `backtesting-workspace.tsx`, ya estaba antes de esta sesión — mismo patrón "resolved after mount" replicado deliberadamente en varios archivos de este subsistema, no una regresión). Servidores Django (puerto 8000) y Next.js (puerto 3000) confirmados alcanzables (`curl`) al cierre de la sesión.

**Pendiente**: verificación visual real en navegador (sin Playwright disponible en este entorno) — confirmar que los 4 tabs y los 6 gráficos nuevos rinden bien tanto en la página standalone como en el panel docked angosto del builder (`builder-info-panel.tsx`), y que el modo Results se ve estructuralmente igual al modo Live.

---

## docs/estrategia_nexora_v2.pine — re-arquitectura SMC (sesión actual)

### Discrepancias encontradas entre el Pine original (pre-rewrite) y el pipeline Python real

| # | Tema | Pine original (incorrecto) | Python real (`pipeline.py`/`strategy.py`/`smc_indicator.py`) |
|---|---|---|---|
| 1 | Tendencia | `close > ta.sma(close, 200)` en 4H | `context.trend` = última `TrendZone`, motor SMC (BOS/CHoCH) sobre velas **diarias**, estructura **interna** (`internal_length=5`, no la swing de 50) |
| 2 | Equal Lows | Ventanas `ta.lowest` en 4H, umbral 0.25% relativo | Pivots de 3 barras sobre diario, umbral **ATR**: `abs(nivel_prev - nivel_nuevo) < 0.1 * ATR` |
| 3 | Order Blocks | Patrón de una vela bajista antes de impulso, en 4H | Motor LuxAlgo completo (pivots, BOS/CHoCH, parsed bars, mitigación High/Low) en diario, internos(5)+swing(50) combinados |
| 4 | Peso score sobreventa estocástico | `+10` | `+15` |
| 5 | TP — BB50 middle | BB50 en 4H | BB50 middle del **daily_candle_df** |
| 6 | Ventana de divergencia | Fija `i_div_len=20` | Python parte el buffer `candle_df` (~500 velas, cargado una vez en `_setup()`, nunca refrescado) por la mitad — **artefacto accidental, no diseño deliberado**. Decisión: no replicar, se mantuvo la ventana fija en Pine. |

Pesos reales (`strategy.py:292-354`, rama LONG): Equal Lows +35, Order Block +25, Divergencia +20, Sobreventa +15, BB50 +15, bonus tendencia +10. Umbral: score ≥ 50. Máximo teórico: 120 (no 80 como decía `docs/analisis_estrategia.md`, que está desactualizado).

### Dos piezas de comportamiento que no estaban en ningún diseño previo

1. **Kill-switch del Fractal** (`tick_broke_fractal` en `strategy.py:35-36`, usado en `pipeline.py::on_4h_kline` primera línea): si una vela rompe el rango high/low de un `Fractal` marcado **manualmente** (`app/core/models/market.py`), el pipeline se detiene para siempre (`feed.stop()`). Implementado en el Pine como inputs `i_fractal_high`/`i_fractal_low` + flag irreversible `fractal_broken`.

2. **Cancelación de tranches pendientes + reset al primer TP** (`models.py::StrategyContext.cancel_pending_entries`/`.reset()`, invocado en `pipeline.py::on_order_status_change` cuando `amount_taked_entries == 1` o `all_closed`): en cuanto UNA tranche toca TP, se cancelan las órdenes límite de las que no se llenaron y se resetea el ciclo. El diseño anterior dejaba correr las 3 `strategy.exit()` para siempre, sin cancelar hermanas.

   **Nota sobre la condición `all_closed` de Python**: en la práctica es casi inalcanzable, porque `context.entries` incluye las 3 entries desde que se crean (estado `WAITING` si no se han llenado), y `all_closed` exige que TODAS estén en `(TAKED, STOP_LOSS_BROKEN)` — una entry `WAITING` nunca cumple eso. Si ninguna tranche llega a TP (p. ej. las 3 terminan en SL tras llenarse), el pipeline Python se quedaría sin disparar `reset()` nunca más, bloqueado. En el Pine se añadió una **red de seguridad** deliberada (no es una réplica 1:1): una vez que todo lo que llegó a llenarse ya cerró (`strategy.opentrades == 0` tras haber tenido posiciones abiertas), se libera el ciclo igual, aunque nunca haya disparado un TP. Esto es una mejora intencional sobre el comportamiento Python literal, documentada para que quede claro que es una decisión de diseño y no un error de transcripción.

### Decisión de diseño: aplanado a escalares en el límite de `request.security`

Pine v6 puede técnicamente devolver arrays/UDTs vía `request.security()`, pero con casuísticas de repintado/identidad documentadas como problemáticas. Se optó por devolver una tupla plana de 17 floats (trend, BB50 diario, 5 Order Blocks top/bottom, 5 Equal Lows) en vez de arrays — ver `docs/plans/pine-strategy-rearchitecture.md` para el detalle completo. Los 5 slots por categoría son un margen documentado, no una garantía de paridad con las listas ilimitadas de Python.

### Puntos de mayor riesgo de fallo de compilación (sin poder validar fuera de TradingView)

Estos son los lugares con más probabilidad de necesitar un ajuste si TradingView reporta un error al pegar el fichero:

1. **Tupla de 17 elementos en `request.security()`** (`f_daily_engine()` → destructure de `d_trend, d_bb50_mid, ob_top_1..5, ob_bot_1..5, eql_1..5`). No hay un límite documentado bajo que recordemos para esto, pero es la construcción menos común del fichero.
2. **Parámetros de array tipados explícitamente** en `f_store_ob`/`f_delete_mitigated` (`array<float>`, `array<int>`). Se tipó explícitamente para evitar problemas de inferencia, pero no se pudo compilar para confirmar.
3. **Funciones de nivel superior usadas dentro de `request.security()`**: `f_store_ob`/`f_delete_mitigated` se llaman desde dentro de `f_daily_engine()`, que a su vez se invoca vía `request.security()`. El patrón de `var`/arrays persistentes dentro de una función pasada a `request.security()` es un patrón Pine documentado y de uso común para correr lógica de un timeframe superior, pero no se pudo compilar para confirmar en este entorno.
4. **`strategy.closedtrades.exit_comment(...)`**: función usada para detectar si el cierre fue por TP o SL. Si esta función no existe con ese nombre exacto en la versión de Pine del usuario, es el primer lugar a revisar.

**Acción pendiente para el usuario**: pegar el fichero en el editor de Pine de TradingView y compilar. Si hay errores, son más probables en estos 4 puntos que en el resto del fichero (que reutiliza patrones ya usados en el fichero original que sí compilaba salvo la línea 213).

### `docs/analisis_estrategia.md` está desactualizado

No usar como referencia para trabajo futuro sobre esta estrategia: describe pesos de score viejos (máx. 80, en vez de 120) y afirma que el `SMCIndicator` corre sobre datos 4H, cuando en el código actual corre sobre velas **diarias** (`context.daily_candle_df`). La fuente de verdad es `strategy.py`/`pipeline.py`/`smc_indicator.py` directamente.

### Annual/Semester high-low — valor correcto pero render incorrecto, luego corregido

**Primer fix (valor)**: la versión inicial usaba `ta.highest(high, 252)`/`ta.lowest(low, 252)` (252/126 barras rolling) como aproximación de "annual/semester high-low". Se corrigió para anclarse al año/semestre **calendario** real (igual que `strategy.py`: `year_start = Timestamp(current_dt.year, 1, 1)`), reseteando el máximo/mínimo solo cuando cambia el año o el semestre (H1=Ene-Jun, H2=Jul-Dic), dentro de `f_daily_engine()`. Se devuelven en la misma tupla del motor diario (no `request.security` calls separados).

**Segundo fix (render)**: aun con el valor corregido, seguía viéndose como una escalera de muchos segmentos. Causa: `plot()` dibuja un punto por CADA barra de toda la historia — aunque el valor ya estaba bien calculado por año, `plot()` seguía generando un escalón nuevo en cada cambio de año a lo largo de todo el histórico. El usuario pidió específicamente: una sola línea (con texto) por el año/semestre **en curso**, extendida de 1/1 a 31/12 (o medio año), sin marcar nada de años anteriores. Fix: se reemplazó `plot()` por objetos `line.new()`/`label.new()` con `xloc=xloc.bar_time` y coordenadas de tiempo explícitas (`timestamp(year, month, day, hour, minute)`), redibujados (delete + new, mismo patrón que la caja del Order Block) solo cuando cambia el valor o el año/semestre — así nunca se acumulan líneas de períodos pasados, solo existe el objeto del período actual.

### Pine invierte la dirección del `for` cuando `from > to` (ya corregido)

`RE10045: index 1 is out of bounds, array size is 0` en `f_daily_engine()`, en el loop de insertion sort (`for i = 1 to n_ob - 1`). Causa: a diferencia de lo que asumí al escribirlo, Pine **no** se salta el cuerpo del loop cuando `from > to` sin un `by` explícito — invierte automáticamente la dirección y lo recorre descendiendo (p. ej. `for i = 1 to -1` ejecuta con `i = 1, 0, -1`). Con `n_ob` 0 o 1 (arrays de Order Blocks vacíos, normal en las primeras barras), `n_ob - 1` es -1 o 0, y el loop igual ejecutaba con `i = 1`, intentando `array.get` fuera de rango.

**Fix aplicado**: envolver el for con `if n_ob > 1` antes de entrar (un array de 0 o 1 elementos ya está "ordenado", no necesita el insertion sort). Lección general para cualquier `for` en Pine de este repo: si los límites pueden depender de un tamaño que empieza en 0, envolver explícitamente con un `if` en vez de confiar en que `from > to` no ejecute nada.

Revisados los otros 3 `for` del fichero: los dos loops de `f_store_ob` (scan entre `pivot_bar_idx+1` y `bar_index-1`) son seguros porque el tamaño mínimo de pivot (5 internal, 50 swing) garantiza `from <= to` siempre; el loop de `strategy.opentrades` ya estaba envuelto en `if strategy.opentrades > 0`.

### `strategy.entry()` no tiene parámetro `qty_percent` (ya corregido)

El fichero original (antes de esta reescritura) usaba `strategy.entry("L1", strategy.long, qty_percent=30, ...)` — `qty_percent` **no existe** como argumento de `strategy.entry()` en Pine (`CE10120`). Solo se reportó después de arreglar el bug de la línea 213, porque TradingView se detiene en el primer error de compilación. Como la estrategia ya declara `default_qty_type = strategy.percent_of_equity` en `strategy(...)`, el parámetro correcto es `qty=` — Pine interpreta automáticamente ese valor como porcentaje de equity gracias al `default_qty_type`. No hace falta calcular el porcentaje aparte. Si aparece este mismo patrón en otros `.pine` del repo, aplicar el mismo fix.

### El bug de sintaxis original (ya corregido)

Línea 213 del fichero anterior: `[ob_top, ob_bot, ob_valid] := f_exist_orderblock(...)`. Pine no permite reasignar una tupla de variables existentes con `:=` — solo se puede declarar con `=`; la reasignación de variables ya existentes debe hacerse una por una con `:=`. Lección general para cualquier código Pine futuro en este repo.

---

## docs/salva/nexora_strategy_v3.pine — construcción incremental sobre LuxAlgo intacto

Enfoque distinto a v2: en vez de reconstruir el motor SMC, se parte de una copia intacta de `docs/smc-luxalgo.pine` y se le van agregando elementos de la estrategia uno por uno (ver `docs/plans/pine-strategy-rearchitecture.md`... nota: ese documento es de v2, v3 no tiene su propio doc de referencia todavía, solo este `bugs.md` y el historial del plan mode).

### `request.security` con timeframe `'12M'` no es fiable — Annual se calcula a mano

Al agregar el nivel Annual reusando `drawLevels()` (mecanismo nativo de Daily/Weekly/Monthly) con timeframe `'12M'`, la barra sintética de 12 meses no avanzaba de forma fiable con el tiempo real — quedaba "pegada" a un año viejo (2024) aunque el chart mostrara 2025/2026. Se reemplazó por cálculo manual: `annualHigh`/`annualLow`/`annualYear` acumulados bar a bar en el timeframe del chart (reset cuando cambia `year(time)`), dibujado con `drawAnnualLevel()`. Lección: no usar `'12M'`/`'1Y'` como timeframe de `request.security` para niveles "anuales" — no es fiable en TradingView.

### El mismo gate de `barstate` que usa Daily/Weekly/Monthly congela el nivel Annual al detener Replay

`drawAnnualLevel()` se llamaba dentro de `if barstate.islastconfirmedhistory or (barstate.isrealtime and newBar)` (el mismo gate de Daily/Weekly/Monthly, pensado para no redibujar cada barra histórica por eficiencia). Ese gate solo es `true` al cargar histórico o con barras nuevas en tiempo real/replay — al **detener** el Replay no se vuelve a cumplir, así que la línea quedaba congelada en el último año donde sí se había dibujado. Fix: sacar la llamada del gate y ejecutarla sin condición en cada barra. Daily/Weekly/Monthly probablemente tengan el mismo problema latente (no reportado, no tocado).

### `input.time()` con `defval = timestamp(...)` rompe la compilación — segunda aparición de la limitación const/simple

`Cannot call 'input.time' with argument 'defval'='call timestamp (simple int)'. An argument of 'simple int' type was used but a 'const int' is expected.` — misma clase de problema que `ta.bb()`'s `mult` (ver más abajo, sección de `estrategia_nexora_v2.pine`... bueno, en realidad reportado primero acá en v3): varios parámetros de funciones built-in de Pine exigen **"const"** (literal, conocido en compilación), no solo "simple" — y una llamada a función como `timestamp(2020, 1, 1, 0, 0)`, aunque todos sus argumentos sean literales, Pine la califica como "simple int" como máximo, nunca "const". `input.time()` específicamente exige `defval` "const int".

**Fix**: usar un literal numérico directo (timestamp UNIX en milisegundos) en vez de `timestamp(...)`: `input.time(1577836800000, 'Start', ...)` (= 2020-01-01 00:00:00 UTC). **Lección general, reafirmada**: antes de pasar el resultado de una función built-in de Pine (no solo `ta.*`, también `timestamp()`, posiblemente otras) como argumento de un `input.*` u otra función que exija "const"/"simple", verificar primero si acepta llamadas a función o si hace falta un literal — no asumir que "todos los argumentos son literales" implica que el resultado de la función también lo es.

### Stochastic Oscillator no puede compartir panel con un script `overlay=true`

Pine no permite que un mismo script mande unos `plot()` al panel principal (overlay) y otros a un panel aparte — es todo-o-nada por script. Como `nexora_strategy_v3.pine` es `overlay=true` (para dibujar la estructura SMC sobre el precio), el Stochastic Oscillator (0-100) no se puede graficar en su propio panel ahí. Decisión tomada con el usuario: la función `stochasticOscillator()` queda disponible para la lógica de la estrategia (igual que `is_stochastic_oscillator_in_over_sell` en `strategy.py`), y en pantalla se muestran solo marcadores compatibles con overlay (`plotshape` triángulos al entrar en sobrecompra/sobreventa) en vez del oscilador completo. Si se necesita el oscilador completo en su panel, habría que crear un `.pine` separado con `overlay=false`.

### Caja del Fractal con valores por defecto absurdos tiñe todo el fondo del chart

Al agregar `FRACTAL_GROUP`, `showFractalInput` quedó en `true` por defecto, con `fractalHighInput=1.000.000.000` / `fractalLowInput=0` como placeholders (esperando que el usuario los reemplace por su fractal real). Con esos defaults, la caja semitransparente cubre TODO el rango de precio visible en pantalla (el high real de cualquier activo está muy por debajo de mil millones, y el low por encima de cero), así que el `bgcolor` translúcido de la caja termina tiñendo el fondo completo del chart — el usuario lo confirmó visualmente (fondo "azulado", coincide con `GRAY = #878b94`, un gris con tinte azul, al 90% de transparencia). **Fix**: `showFractalInput` por defecto `false` — mismo criterio que ya se había aplicado en `estrategia_nexora_v2.pine` por la misma razón (`i_show_fractal` también default `false` ahí), pero no se replicó en v3 al construirlo. **Lección**: cualquier input con un rango de placeholder deliberadamente absurdo (para forzar al usuario a configurarlo) debe tener su toggle de visibilidad en `false` por defecto, no solo el valor en sí.

### RESUELTO: motor de estructura (EQL/OB/tendencia interna) ahora corre en diario vía `dailyEngine()`

Lo que estaba documentado como "pendiente" arriba (el motor nativo seguía corriendo en el timeframe del chart) **ya está implementado**. `dailyEngine()` (sección "MOTOR SMC DIARIO" del fichero) adapta la lógica de `leg`/`getCurrentStructure`/`displayStructure`/`storeOrdeBlock`/`deleteOrderBlocks` — el mismo algoritmo LuxAlgo sin modificar, solo sin las llamadas de dibujo — corriendo vía `request.security(syminfo.tickerid, "D", dailyEngine())`, con su propio juego de variables `var` dedicado (sufijo `D`), separado del motor nativo a nivel de script (que ya no se invoca para estructura: se quitaron las llamadas a `getCurrentStructure`/`displayStructure`/`deleteOrderBlocks` del bloque de ejecución).

**Decisiones de diseño tomadas**:
- **Tupla de retorno de `request.security`**: 31 escalares planos — `dTrend` (tendencia interna, 1/-1/0) + 5 Equal Lows (precio+timestamp diario) + 5 Order Blocks internos+swing combinados, ordenados por `top` descendente (precio top/bottom/timestamp/bias). Mismo principio de "5 slots, margen documentado" que `estrategia_nexora_v2.pine`. EQH se calcula internamente (hace falta para que la comparación de umbral ATR del próximo pivot sea correcta) pero no se expone — LONG-only no lo usa.
- **Mitigación de Order Blocks hardcodeada a modo "High/Low"** (el default de `orderBlockMitigationInput`) dentro de `deleteObDaily()`, usando `high`/`low` directo en vez de las variables globales `bearishOrderBlockMitigationSource`/`bullishOrderBlockMitigationSource` — había duda real sobre en qué contexto (diario vs chart) se resolverían esas variables si se referenciaran desde dentro de una función llamada por `request.security`, así que se evitó la ambigüedad por completo. Si el usuario cambia `orderBlockMitigationInput` a "Close", el motor diario NO lo reflejará (limitación conocida, no implementada).
- ~~**Alcance visual reducido**: solo se dibuja el Order Block / Equal Low **activo**~~ — **SUPERADO, ver sección siguiente**: se restauró la visualización completa (EQL/EQH, HH/HL/LH/LL, BOS/CHoCH, Order Blocks internos+swing) acotada a un cupo fijo de eventos recientes.

### RESUELTO: visualización completa de estructura restaurada (EQL/EQH, HH/HL/LH/LL, BOS/CHoCH, Order Blocks internos/swing)

El usuario reportó que tras desactivar el motor nativo (sección anterior) ya no veía ninguna estructura en el chart — solo quedaba el Order Block/Equal Low "activo" (el que alimenta la señal). Se restauró la riqueza visual original, pero alimentada por `dailyEngine()` en vez del motor nativo, para que siga sin cambiar de valor al subir/bajar de timeframe. Decisiones confirmadas con el usuario antes de implementar: **profundidad histórica acotada** (no arrays completos vía `request.security`) y **restaurar tanto la estructura Interna (5 velas) como la Swing (50 velas)**, igual que el indicador original.

**Diseño**:
- Las primeras 31 posiciones de la tupla de `dailyEngine()`/`request.security` **no se tocaron** (mismo orden, mismo contenido) — todo lo nuevo se agregó **al final** de la tupla, que pasó de 31 a **120 escalares**: EQH (10, antes solo se trackeaba el nivel sin guardar historial), Order Blocks crudos internos+swing sin fusionar (40, 5 cada uno — la lista fusionada de 5 que alimenta el score/`existOrderblock4h` **no se tocó**, esto es 100% aditivo), eventos de estructura BOS/CHoCH internos+swing con cupo **3** cada uno (30 — tag/bias/level/originTime/breakTime), puntos swing HH/HL/LH/LL con cupo **3** (9). Pendiente de compilar en TradingView — ver "Riesgo no confirmado" más abajo.
- **Helper nuevo `pushEventD()`** (función top-level, no anidada en `dailyEngine()` — mismo motivo que `storeObDaily`/`deleteObDaily`) para el push+cupo-3 de los eventos de estructura. El tag CHOCH/BOS se decide comparando contra el **trend previo a la reasignación** (capturado en una variable local justo antes de `...TrendD := ...`), mismo criterio que el nativo `displayStructure()`.
- **Hallazgo clave**: todos los inputs/toggles necesarios (`showInternalsInput`, `showStructureInput`, `showSwingsInput`, `showEqualHighsLowsInput`, `showInternalOrderBlocksInput`, `showSwingOrderBlocksInput`, sus colores/tamaños, los filtros `showInternalBullInput`/`showInternalBearInput`/`showSwingBullInput`/`showSwingBearInput`) ya existían en el fichero — quedaron huérfanos cuando se desactivó el motor nativo. Esta restauración **re-cablea esos inputs**, no crea controles nuevos. `internalOrderBlocksBoxes`/`swingOrderBlocksBoxes` (los arrays de `box` ya pre-creados en `barstate.isfirst` para el motor nativo, nunca alimentados) también se reutilizaron tal cual.
- **4 helpers de dibujo top-level** (reciben arrays por parámetro, igual patrón que `storeObDaily`): `drawObBoxSetD` (Order Blocks crudos, interno y swing comparten la función), `drawLevelSetD` (EQL/EQH, línea punteada con `extend.right` desde el origen — mismo estilo que `activeEqlLine`, NO el segmento fijo del nativo), `drawStructEventSetD` (BOS/CHoCH, línea FIJA sin extend desde `originTime` hasta `breakTime`, sí respeta el filtro ALL/BOS/CHOCH), `drawSwingPointSetD` (HH/HL/LH/LL, solo aplica a estructura swing). Todos con guard `n = math.min(array.size(destino), array.size(datos))` antes del `for` — necesario en `drawObBoxSetD` porque `internalOrderBlocksSizeInput`/`swingOrderBlocksSizeInput` son configurables 1-20 pero el cupo del motor diario es fijo en 5; sin el `min`, un usuario con el size input >5 rompería con índice fuera de rango.
- **`modeInput` (Historical/Present) no se conectó** a esta nueva visualización — su semántica original (borrar+recrear un único objeto) no aplica al modelo de "ventana acotada de N eventos". Queda sin repurposing por ahora; si hace falta, ver la "Propuesta" descartada en el plan de esta sesión (P RESENT = solo el evento más reciente).
- Las llamadas dead `drawOrderBlocks(true)`/`drawOrderBlocks()` (leían de los arrays `orderBlock` nativos, nunca poblados) se **reemplazaron** por `drawObBoxSetD(...)` sobre los mismos `box` ya creados, alimentados con los datos crudos del diario.

**Riesgo no confirmado**: el tamaño final de 120 escalares en la tupla de `request.security` — compiló bien en la sesión anterior con 31, este es terreno nuevo (~4x más grande). Si TradingView lo rechaza, el primer ajuste a probar es bajar el cupo de eventos de estructura/puntos swing de 3 a 2 (ver plan de esta sesión, archivado).
- **FVG y Premium/Discount zones no se tocaron** — siguen en el timeframe del chart, ya que son independientes de `leg`/`getCurrentStructure` y `strategy.py` no las usa para el score.
- **Señal de entrada (`entrySignal4h`) es VISUAL ÚNICAMENTE** — un `label.new` con el score y los 3 niveles hipotéticos de tranche. No hay `strategy.entry()`, el fichero sigue siendo `indicator()`. Dispara solo en flanco de subida (`canEnter4h and not canEnter4h[1]`) para no repetir la misma señal mientras la condición se mantiene.
- **Pesos de score**: Equal Lows +35, Order Block +25, Divergencia +20, Sobreventa +15, BB50 +15, tendencia +10 (umbral default 50) — mismos que `estrategia_nexora_v2.pine`, confirmados contra `strategy.py`.

**Riesgos no confirmados por compilación** (validar en TradingView):
1. ~~Tamaño de la tupla de `request.security` (31 escalares)~~ — **confirmado OK**: el fichero compiló y corrió, el error real reportado fue en runtime, no en la tupla.
2. ~~`storeObDaily`/`deleteObDaily` como funciones top-level llamadas dentro de `dailyEngine()`~~ — **confirmado OK**: el patrón resuelve correctamente el contexto diario.
3. Cada pieza nueva (`existEquals4h`, `existOrderblock4h`, `stochDivergence`, `calcScore4h`) es candidata a los mismos errores de calificación "const/simple" ya vistos varias veces en esta sesión — sin reportes de error en esta categoría hasta ahora.

### RESUELTO (runtime): `array.get()` index out of bounds dentro de `dailyEngine()` — Pine NO hace cortocircuito en `and`/`or`

**Error real reportado**: `Error on bar 35: In 'array.get()' function. Index -1 is out of bounds, array size is 2. at dailyEngine():1071`.

**Causa raíz** (gotcha de Pine no documentado de forma prominente, pero real y reproducible): a diferencia de la mayoría de lenguajes, **Pine Script evalúa SIEMPRE ambos operandos de `and`/`or`**, incluso cuando el primer operando ya decide el resultado. En el insertion-sort del aplanado de Order Blocks (combinar `internalObTopD`+`swingObTopD`, ordenar por `top` descendente):

```pine
while j >= 0 and array.get(workTopD, j) < keyTop
    ...
    j -= 1
```

Cuando `j` llega a `-1`, Pine evalúa igualmente `array.get(workTopD, -1)` aunque `j >= 0` ya sea `false` — no hay cortocircuito que evite la segunda mitad de la expresión. Esto rompe con índice negativo fuera de rango.

**Fix aplicado** (`dailyEngine()`, ~línea 1063): separar el chequeo de límites en su propia rama `if` ANTES de tocar el array — las ramas `if`/`else if`/`else` sí cortan en seco (solo se ejecuta la rama que matchea), a diferencia de una expresión `and` compuesta:

```pine
keepGoing = true
while keepGoing
    if j < 0
        keepGoing := false
    else if array.get(workTopD, j) < keyTop
        ...
        j -= 1
    else
        keepGoing := false
```

**Fix preventivo relacionado**: el mismo riesgo existía (sin haber producido error aún, pero por el mismo motivo estructural) en `storeObDaily()` — el guard era `not na(pivotBarIdx) and pivotBarIdx < bar_index`, sin chequear `pivotBarIdx >= 0`. `pivotBarIdx` (`bar_index - 5` interno o `bar_index - 50` swing) puede ser negativo en las primeras barras del histórico diario, y como SÍ se usa después en `array.get(parsedHighsArr, pivotBarIdx)`, se agregó `pivotBarIdx >= 0` al guard por seguridad.

**Lección general para todo el fichero**: cualquier `while`/`if` que combine con `and`/`or` un chequeo de límites (`j >= 0`, `i < size`, `not na(x)`) con un acceso a array/objeto que depende de ese límite (`array.get(arr, j)`, `arr.get(i)`) **debe separarse en ramas `if` anidadas**, nunca en una sola expresión booleana compuesta — Pine evaluará el acceso igual aunque el límite ya lo descarte.

### RESUELTO (visual): geometría de EQL/EQH mal dibujada — faltaba el tiempo de ORIGEN del pivot

**Reporte del usuario**: tras restaurar la visualización (sección anterior), comparó `Nexora v3` contra el indicador nativo `SMC` (LuxAlgo) superpuestos en el **mismo gráfico de 1D** y encontró 3 síntomas: (1) EQL/EQH "solo muestra el elemento" (no se ve como línea), (2) algunos elementos coinciden con el SMC nativo y otros no, (3) el texto de las etiquetas se ve descentrado ("en SMC es como centrado, pero acá se ha corrido").

**Causa raíz (confirmada por inspección de código, no especulación)**: el nativo `drawEqualHighLow()` dibuja un **segmento fijo** entre el pivot ANTERIOR (`p_ivot.barTime`, el último pivot bajo/alto visto, sea o no "equal") y el pivot ACTUAL (`time[size]`), con el label centrado a la mitad. El port a `dailyEngine()` solo guardaba **un** timestamp por evento (el de confirmación) — nunca declaró el equivalente a `p_ivot.barTime` (el tiempo de origen). Para compensar esa falta de dato, `drawLevelSetD()` dibujaba una línea **degenerada** (mismo punto en `x1`/`x2`) con `extend.right`, imitando el patrón de `activeEqlLine` (que es para el nivel "activo", no para historial) — eso no es lo que muestra el nativo, y explica los 3 síntomas a la vez.

**Fix aplicado**:
- Se agregó `var int equalLowTimeD = na` / `var int equalHighTimeD = na` (equivalente a `p_ivot.barTime`), actualizados en **cada** formación de pivot equal (no solo en match), justo antes de la línea donde el nivel se actualiza.
- Se agregaron arrays capados `eqlOrgTimeArrD`/`eqhOrgTimeArrD` (cupo 5 c/u) que guardan el tiempo de origen (`equalLowTimeD`/`equalHighTimeD` **antes** de actualizarse) junto al de confirmación ya existente — **+10 campos al final de la tupla de `request.security`, que pasa de 120 a 130 escalares**.
- `drawLevelSetD()` ahora recibe también el array de tiempos de origen; dibuja `set_first_point(origin)`/`set_second_point(confirm)` (sin `extend` — se quitó `extend.right` de la creación de las líneas en `barstate.isfirst`) y centra el label en el **tiempo medio** (`org + (tm-org)/2`, vía `xloc.bar_time` — no `xloc.bar_index` como el nativo, porque acá el dato es diario y el chart puede estar en otro timeframe).
- Mismo fix de centrado aplicado a `drawStructEventSetD()` (eventos BOS/CHoCH): el nativo `drawStructure()` también centra su label (`math.round(0.5*(p_ivot.barIndex+bar_index))`), y el port lo anclaba al tiempo de quiebre sin centrar — menos notorio visualmente pero mismo tipo de error.
- **Gotcha de tipos nuevo encontrado al implementar el centrado**: el operador `/` en Pine devuelve **`float` aunque ambos operandos sean `int`** (p. ej. `(tm - org) / 2` con `tm`/`org` tipo `int` da `float`, no división entera). `chart.point.new()` exige `series int` para el parámetro de tiempo — sin un cast explícito con `int(...)` alrededor de todo el cálculo del punto medio, esto rompe con `"series float" was used but "series int" was expected`. Mismo tipo de error de calificación de tipo que `ta.bb`'s `mult`/`input.time`'s `defval`, pero por una razón distinta (operador aritmético, no parámetro de función) — **lección nueva**: cualquier aritmética con valores `int` de tiempo que vaya a un parámetro `int` (`chart.point.new`, etc.) debe envolverse en `int(...)` si involucra `/`, incluso si "debería" dar un entero.

**Causa raíz adicional encontrada en la misma revisión — tamaños de ventana hardcodeados en vez de usar los inputs del usuario**: el nativo llama `getCurrentStructure(equalHighsLowsLengthInput, true)` (equal, default 3) y `getCurrentStructure(swingsLengthInput, false)` (swing, default 50) — ambos con el tamaño de ventana como **input configurable**. El port a `dailyEngine()` tenía esos tamaños **hardcodeados como literales `3` y `50`** (coincide con los defaults, por eso no se notaba hasta que se compara con cuidado o el usuario cambia el input). Si el usuario alguna vez cambia `equalHighsLowsLengthInput`/`swingsLengthInput`, el motor diario divergiría silenciosamente del nativo. **Fix**: reemplazados todos los usos (`high[N]`, `low[N]`, `ta.highest(N)`, `ta.lowest(N)`, `time[N]`, `bar_index - N`) por las referencias a los inputs correspondientes. La estructura **interna** (5 velas) sí está correctamente hardcodeada en ambos lados — el nativo también la llama con el literal `5` (`getCurrentStructure(5, false, true)`), así que ahí no había bug.

### RESUELTO (diseño): cupo de visualización subido de 5/3 a 20/10 — el SMC nativo no "mitiga" EQL/estructura

**Reporte del usuario tras el fix de geometría anterior**: "ya dibuja bien" (la geometría quedó correcta) pero "sigue sin marcar las mismas estructuras que SMC nativo... algunos que en teoría deberían estar mitigados, como algunos EQL, los pone" — comparando ambos indicadores en el mismo gráfico de 1D.

**Causa raíz (no era un bug de posición)**: el indicador SMC nativo **no tiene ningún concepto de "EQL/EQH mitigado"**. En su modo por defecto (`Mode = Historical`), `drawEqualHighLow()`/`drawStructure()` nunca borran las líneas/labels que crean — solo reasignan la variable de referencia a un objeto nuevo, dejando el anterior dibujado para siempre. Esto significa que el nativo muestra **TODO el historial** de EQL/EQH/BOS-CHoCH del chart simultáneamente, incluyendo marcas "viejas" que visualmente parecen ya quebradas por el precio actual (pero el nativo nunca las quita — eso no es mitigación, es que nunca hubo lógica de borrado para empezar). Nexora, por decisión ya acordada con el usuario ("profundidad histórica acotada", para evitar arrays sin límite vía `request.security`), solo mostraba los últimos 5 EQL/EQH y los últimos 3 eventos de estructura — así que al comparar 1:1, el nativo siempre mostraba más marcas (las antiguas que Nexora ya había descartado del cupo). Confirmado con el usuario: subir el cupo bastante, sin pasar al patrón de arrays sin límite (más riesgoso, no confirmado en este proyecto).

**Fix**: cupos subidos de 5→20 (EQL, EQH, Order Blocks internos/swing crudos) y de 3→10 (eventos de estructura BOS/CHoCH interno/swing, puntos swing HH/HL/LH/LL). La tupla de `request.security` pasó de 130 a **431 escalares**. Decisiones de implementación:
- Las primeras 31 posiciones (score: `dTrend`, `eql1..5`/`eqlT1..5`, `ob1..5`) **siguen sin tocarse** — el cupo más grande es 100% aditivo, no cambia el comportamiento del score/señal de entrada.
- Nuevos helpers `getF(array<float>,i)`/`getI(array<int>,i)`/`getS(array<string>,i)` (top-level, junto a `pushEventD`) para acortar el patrón `i < array.size(a) ? array.get(a,i) : na`, repetido ~400 veces.
- `pushEventD()` ahora recibe el cupo como parámetro (`cap`) en vez de tenerlo hardcodeado a 3, para poder reusarlo con 10.
- `internalOrderBlocksSizeInput`/`swingOrderBlocksSizeInput` (inputs ya existentes, rango 1-20) se subieron de default 5 a default **20** — coincide exactamente con el nuevo cupo del motor diario, así el usuario ve el cupo completo sin tener que tocar nada.
- `drawObBoxSetD`/`drawLevelSetD`/`drawStructEventSetD`/`drawSwingPointSetD` no cambiaron de firma (ya recibían arrays por parámetro) — solo los `array.from(...)` en los call-sites pasaron de 5/3 elementos a 20/10.
- Verificación hecha con `diff` línea por línea (no solo visual) entre la tupla de retorno y el destructure de `request.security`, normalizando espacios — confirmado **431 campos, orden idéntico en ambos lados**.

**Riesgo no confirmado**: 431 escalares es ~3.3x el tamaño ya confirmado-OK de 130 — sin precedente conocido en este proyecto a esta escala. Si TradingView lo rechaza, el ajuste más simple es bajar el cupo (p. ej. 20→12, 10→6) antes de reconsiderar la arquitectura — los cupos son constantes literales fáciles de cambiar (`> 20`/`> 10`/`for index = 1 to 20`/`for index = 1 to 10`), no requieren tocar la lógica.

### `ta.bb()` con el parámetro `mult` pasado por función definida por el usuario rompe la compilación

`Cannot call 'ta.bb' with argument 'mult'='mult'. An argument of 'series float' type was used but a 'simple float' is expected.` — `ta.bb()` exige que su parámetro `mult` sea "simple float" (calificador fijo, no puede variar barra a barra). Al envolverlo en una función propia (`bb50(int length, float mult) => ta.bb(close, length, mult)`), Pine eleva el parámetro `mult` a "series float" dentro de la función — **los parámetros de funciones definidas por el usuario en Pine se tratan como "series" para fines de calificación de tipo, sin importar el calificador del argumento real en el sitio de la llamada**. `length` no tuvo este problema (acepta "series int"), solo `mult`.

**Fix**: no envolver `ta.bb()` en una función propia cuando se le pasan inputs configurables — llamarlo directo en el sitio de uso: `ta.bb(close, bb50LengthInput, bb50MultInput)`. Esto explica por qué en v2 `f_bb50() => ta.bb(close, 50, 2)` funcionaba: usaba constantes literales, nunca parámetros de función. **Lección general**: cualquier función `ta.*` de Pine con un parámetro que exija "simple"/"const" (no solo `ta.bb`'s `mult` — revisar la documentación de cada una antes de envolverla) no se debe envolver en una función propia si ese parámetro viene de un input configurable; llamarla directo.

## `pandas_luarix` — gotchas del port `SMCIndicator`/LuxAlgo (`app/tradingview/`) que la nueva librería NO debe repetir

Contexto: `pandas_luarix/` (accessors `.smc`/`.structure` sobre `pd.DataFrame`) es una librería nueva e independiente — NO importa `app/tradingview/`. El código de `app/tradingview/smc_indicator.py` (port bar-a-bar de Pine LuxAlgo) se usó solo como referencia algorítmica para el primer batch de indicadores (swings, equal highs/lows, BOS/CHoCH, order blocks, fair value gaps, liquidity sweeps). Hallazgos de esa referencia que se evitaron deliberadamente en el diseño nuevo:

1. **Campos muertos en `SMCConfig`** (`app/tradingview/types.py:309-322`): `max_swing_obs`, `max_internal_obs`, `detect_trailing` se declaran pero nunca se leen en `smc_indicator.py`. El cap real de order blocks es un literal hardcodeado `100` en `_store_order_block` (línea 684), no controlado por config. → En `pandas_luarix` todo parámetro expuesto se consume realmente en la implementación; no hay cap de retención de order blocks (se retienen todos, mitigados incluidos, con flag).
2. **Default de ATR inconsistente**: `_compute_atr(..., period=200)` es el default interno de `SMCIndicator.run()` (`smc_indicator.py:97`), pero el caller real (`contexts.py:216`) precalcula `ta.atr(..., 100)` y lo inyecta vía `precomputed_atr`, pisando silenciosamente el default de 200. → `pandas_luarix` usa `atr_period=14` como único default explícito en todo helper que consuma ATR (`_core/volatility.py`), siempre como kwarg explícito, nunca heredado de un objeto de config compartido.
3. **Borrado destructivo de order blocks/FVG mitigados en vez de flag**: `_delete_order_blocks` (líneas 710-720) hace `ob.mitigated = True` y ACTO SEGUIDO `obs.pop(idx)` — el flag queda en un objeto ya removido de la única lista que lo referencia. Mismo patrón en `_delete_fair_value_gaps`. → `pandas_luarix` retiene SIEMPRE las filas mitigadas/filled con su columna booleana (`mitigate_order_blocks`, `mark_filled_fvgs` en `_core/`); `include_mitigated`/`include_filled` solo filtran la vista devuelta.
4. **Threshold de FVG nunca implementado**: `threshold = 0.0` hardcodeado (líneas 758-759), simulando una feature que nunca se calculó de verdad. → `pandas_luarix.smc.fair_value_gaps()` implementa un filtro de tamaño mínimo real y funcional (`min_gap_atr_multiple`, comparado contra `ATR(atr_period)`), no un parámetro decorativo.
5. **Dos algoritmos de Equal High/Low incompatibles conviviendo sin resolver**: el ATR/pivot-based (dentro de `_get_current_structure`) y el pct-based (`find_equals_in_ohvl`/`_group_equal_pct`) son funciones separadas, hay que invocar la segunda a mano y pisar `result.equal_highs/equal_lows`. → `pandas_luarix.structure.equal_high/equal_low` exponen ambos vía `method: EqualLevelMethod = ATR_PIVOT | PCT_RANGE`, con default explícito y documentando qué parámetros aplican a cada rama.
6. **Multiplicador de alta volatilidad hardcodeado**: `high_vol_bar = (h - l) >= 2 * vol` (línea 130), el `2` es literal. → `pandas_luarix` lo expone como `high_vol_multiplier` explícito en `_core/volatility.py::parsed_high_low`.
7. **Bug propio encontrado durante la implementación (no viene de la referencia)**: al construir `structure.swing_high()`/`swing_low()`/`swings()`, la primera versión devolvía la fila de la vela de **confirmación** del pivot (posición `i`, donde el algoritmo de detección "se entera" de que hubo un pivot) en vez de la vela de **origen** (posición `i - length`, donde realmente ocurrió el extremo de precio). Como el valor del pivot (`pivot_high`/`pivot_low`) se guarda en `find_pivots` en la posición de confirmación pero representa el precio de `length` barras atrás, usar `df.loc[pivot_high.notna()]` directamente selecciona la vela equivocada — el contenido de esa fila (open/high/low/close de la vela de confirmación) no coincide con el nivel de precio que describe. Fix: restar `length` a las posiciones de confirmación antes de indexar (`pivot_high.notna().to_numpy().nonzero()[0] - length`). Lección: cuando una serie "sparse" (NaN salvo en el bar de confirmación) representa un valor que en realidad pertenece a una barra anterior (por `shift(length)`), hay que propagar ese desfase a cualquier indexación posicional derivada de ella, no solo al valor.
8. **Categóricos como `Enum`, no strings sueltos**: la referencia usa strings mágicos (`ob_filter="Atr"`, `ob_mitigation="High/Low"`) sin validación. → `pandas_luarix._core.enums` define `EqualLevelMethod`, `ObMitigation`, `VolatilityMethod`, `LiquidityLevels` como `class X(str, Enum)`; cada método coacciona el valor recibido con `EnumType(value)`, dando `ValueError` automático ante valores inválidos.
9. **Bug propio, encontrado por un reporte del usuario (`equal_high` devolvía `[]`) — dos causas reales apiladas, no solo un parámetro mal pasado**:
   - **Defaults mal elegidos**: `equal_high`/`equal_low`/`equal_high_low` heredaban `length=50` de `swings`/`bos_choch`/`order_blocks`, pero en `SMCConfig` el lookback de equal-highs/lows es un campo independiente y mucho más corto (`equal_length`, default `3`). Fix: `length` default bajado a `3` en esos tres métodos (el resto de `structure` mantiene `50`, que sí coincide con `swing_length`).
   - **Bug de cómputo real en `compute_atr`**: usaba `tr.ewm(alpha=1/period, adjust=False, min_periods=period)`, que arranca la recursión de Wilder desde la primera barra de la serie. La referencia (`SMCIndicator._compute_atr`) en cambio **siembra el ATR con el promedio simple (SMA) de las primeras `period` barras** y solo desde ahí aplica la recursión de Wilder — son fórmulas matemáticamente distintas (no solo una reimplementación equivalente) que divergen sistemáticamente por cientos de barras (medido: ATR(200) en la barra 450 daba 455.48 vs 508.87 de la referencia, ~10% de diferencia), suficiente para que pares de equal-highs/lows caigan del lado equivocado del umbral `equal_threshold * ATR`. Fix: `compute_atr` ahora siembra con `tr.iloc[:period].mean()` y aplica `.ewm(adjust=False)` solo sobre la cola, arrancando la recursión en ese punto — validado bit-a-bit (diferencia máxima 0.0) contra la referencia en una serie de 3241 barras.
   - También se corrigió `detect_equal_levels_atr_pivot` para usar comparación estricta `<` (la referencia usa `abs(...) < threshold`, `pandas_luarix` tenía `<=`).
   - Con ambos fixes + defaults alineados (`length=3`, `atr_period=200` — el default real de `SMCIndicator._compute_atr` cuando no se pasa `precomputed_atr`), `equal_high`/`equal_low` con **cero argumentos explícitos** replican exactamente (23/23 y 21/21 grupos, mismos índices) a `SMCIndicator(SMCConfig()).run(df)` con config y ATR puramente por defecto. Test de regresión: `test_equal_high_low_matches_reference_smc_indicator` en `test_pandas_luarix.py`.
   - **Lección general**: al portar un indicador con ATR/Wilder u otro suavizado recursivo, "misma fórmula en teoría" no basta — hay que validar bit-a-bit contra la referencia, porque el manejo del arranque/warmup (SMA-seed vs EMA-cold-start) puede divergir silenciosamente por cientos de barras sin lanzar ningún error, solo produciendo resultados sutilmente distintos (grupos/eventos de menos, no un crash).

Es documentación, no código del que `pandas_luarix` dependa.

---

## `fastapi_server/` — API HTTP sobre `pandas_luarix` (sesión actual)

### Bug real encontrado y corregido: `BinanceMarketDataProvider.get_historical_candles` crasheaba con rango de fechas sin velas

`app/brokers/market_data/binance.py:34` (ahora eliminado) tenía un `print(len(klines), klines[-1])` de debug dejado en el código. Cuando `client.get_historical_klines(...)` devuelve una lista vacía — rango de fechas anterior al listing del símbolo en Binance, o `start_date > end_date` — ese `klines[-1]` lanza `IndexError: list index out of range`, y la excepción se propaga sin capturar hasta un `500 Internal Server Error` en cualquier endpoint de `/indicators/*` o `/smc/*`, saltándose por completo el `if df.empty: raise NoDataError` de `fastapi_server/services/market_data_service.py` (nunca se llega a ejecutar esa línea).

Fix: se eliminaron los dos `print` de debug (`Downloading historical candles...` y `print(len(klines), klines[-1])`); `get_historical_candles` ahora devuelve un DataFrame vacío en ese caso, que `market_data_service.fetch_ohlcv` convierte correctamente en un `404` (`NoDataError`).

Verificado tras el fix con `curl` real contra el servidor: `start_date=2005-01-01` (antes del listing de BTCUSDT) y `start_date > end_date` ahora devuelven `404 {"detail": "No data returned from Binance for ..."}` en vez de `500`. También se probaron símbolos inválidos (`ZZZZZZ`, `btcusdt` en minúscula) — esos SÍ lanzan `BinanceAPIException` antes de llegar al bug (ya estaba cubierto por el `except BinanceAPIException` existente), así que el `IndexError` solo se disparaba en el caso específico de "símbolo válido pero cero velas en el rango".

**Lección**: cualquier código que llame a `get_historical_candles`/`get_historical_klines` con un rango de fechas arbitrario (elegido por un usuario final vía API, no un desarrollador en un notebook) debe asumir que la lista de klines puede venir vacía sin que Binance lance excepción — no solo "symbol inválido" dispara el `except`, un rango sin datos es un camino silencioso distinto.

### Decisión de diseño: taxonomía de grupos de la API (`indicator`/`smc`) vs. accessors de Python (`.structure`/`.smc`/`.indicators`)

La API solo expone **2 grupos** al cliente web (`group: "indicator" | "smc"`, rutas `/indicators/*` y `/smc/*`), pero internamente `pandas_luarix` ahora tiene **3 accessors** de Python: `.structure` (pivots/BOS/CHoCH/order blocks), `.smc` (liquidity sweeps/fair value gaps) y `.indicators` (nuevo — indicadores técnicos clásicos: BB50, Stochastic Oscillator). Tanto `.structure` como `.indicators` caen dentro del grupo API `"indicator"`; solo `.smc` mapea al grupo `"smc"`. Esto es intencional: la agrupación del catálogo (`fastapi_server/catalog/indicators.py`) es una taxonomía de cara al cliente, no un espejo 1:1 del namespace interno de Python.

`pandas_luarix/indicators/accessor.py` (`IndicatorsAccessor`, registrado como `df.indicators`) portó `bb50` (usa `pandas_ta_classic.bbands` directamente, igual que la referencia `app/tradingview/bbands.py`, para no reintroducir el tipo de bug de reimplementación manual documentado arriba con ATR/Wilder) y `stochastic_oscillator` (rolling min/max + SMA, puerto directo de `app/tradingview/stochastic_oscillator.py`, sin dependencias externas). A diferencia de `.structure`/`.smc` (que devuelven un subconjunto disperso de filas — eventos detectados), estos dos devuelven **una fila por cada vela del rango pedido** (con `null` en las columnas del indicador durante su período de warm-up).

**Actualización (sesión posterior): `.structure` fue eliminado, todo vive en `.smc`.**
El usuario consolidó `pandas_luarix/structure/` dentro de `pandas_luarix/smc/accessor.py` — la carpeta `structure/` ya no existe, y `SMCAccessor` ahora expone los 12 métodos (los 10 que antes eran de `.structure` + `liquidity_sweep` + `fair_value_gaps`). `df.structure` ya no existe (confirmado con `hasattr`). La taxonomía de grupos de la API (`"indicator"`/`"smc"`) NO cambió — sigue siendo una capa de cara al cliente independiente del namespace de Python; ambos grupos ahora se sirven desde el mismo accessor `df.smc` (más `df.indicators` para bb50/stochastic).

**2 bugs reales que la consolidación introdujo (encontrados ejecutando cada método directamente, corregidos en la misma sesión):**
1. `pandas_luarix/smc/accessor.py` no importaba `check_positive_float` de `_core.validation` tras el merge — rompía con `NameError` a 6 de los 12 métodos (`equal_high`, `equal_low`, `equal_high_low`, `bullish_order_block`, `bearish_order_block`, `order_blocks`). Fix: agregar el import faltante.
2. `liquidity_sweep` seguía instanciando `structure = StructureAccessor(df)` (clase ya eliminada) para llamar a `.swing_high()`/`.equal_high()`/etc. Como esos métodos ahora viven en la misma clase, el fix fue `structure = self`.

De paso se limpiaron un `__init__` duplicado y un import duplicado de `EqualLevelMethod` que quedaron del merge (ambos inocuos, pero confusos). **Lección**: al consolidar dos clases/módulos en uno, revisar explícitamente (a) que todos los imports usados por el código movido sigan resueltos en el nuevo archivo, y (b) que ninguna referencia interna (`self`, nombres de clase) quede apuntando a la estructura vieja — un merge que "solo mueve código" puede romper silenciosamente varias rutas si no se ejecuta cada método afectado tras el cambio.

### Contrato de "elementos visuales" (`{"elements": [...]}`) — reemplazo completo de `{"data": [...], "count": N}`

El frontend Next.js (`/markets/chart`) solo dibuja 5 tipos de objeto (`marker`, `line`, `box`, `line_series`, `multiline_series`); antes de este cambio, cada uno de los 12 endpoints de indicador devolvía filas crudas de pandas y el frontend tenía un conversor a mano por indicador. Se movió esa conversión al backend (`fastapi_server/services/visual_elements.py`, funciones `convert_<indicador>`), reemplazando por completo el envelope viejo — no coexisten los dos formatos, no hay query param de compatibilidad. `fastapi_server/services/serialization.py` se recortó (se eliminaron `groups_to_rows`/`grouped_rows_response`/`grouped_rows_pair_response`, ya sin uso) pero se mantuvo `rows_response`/`dataframe_to_rows` porque `/brokers/candles` (velas OHLCV crudas, endpoint no relacionado con indicadores) sigue usándolas sin cambios.

Detalles no obvios de la conversión (para no tener que re-derivarlos):
- `direction` solo viaja en `order_blocks`/`fair_value_gaps` (los combinados); `bos_choch` y `liquidity_sweep` NO lo llevan aunque su fila cruda sí tenga una columna de dirección — decisión explícita del contrato, no un olvido.
- `bullish_order_block`/`bearish_order_block` (rutas de un solo lado) llevan `direction` **fijo** (`1`/`-1`, no leído de columna, porque esas rutas no tienen columna `direction`); solo `order_blocks` combinado lo lee de la fila.
- `equal_high_low` cambió de comportamiento: antes devolvía `{"equal_high":[...], "equal_low":[...]}`, ahora es una sola lista `elements` plana con ambos `sub_kind` mezclados.
- `bb50` usa claves `lower`/`middle`/`upper`; `stochastic_oscillator` usa `slowK`/`fastD` (camelCase, distinto a propósito) + `upper_trigger`/`lower_trigger` como campos raíz del elemento (constantes, no series) — coincide con `INDICATOR_VISUAL_SCHEMAS` del frontend.
- `IndicatorMetadataOut.output_kind` fue reemplazado por `kind` (mismos 5 valores que arriba, más eliminado `"rows"`/`"grouped_rows"`/`"grouped_rows_pair"`/`"series"` que ya no describen nada real).

### Divergencia genérica (`df.analysis.divergence`) y Fractal (`df.smc.fractal`) — nuevo grupo API `"analysis"`, nuevo accessor `df.analysis`

**Divergencia**: en vez de "divergencia RSI"/"divergencia MACD" por separado, un único detector (`pandas_luarix/_core/divergence.py::detect_divergence`) que compara pivotes CONFIRMADOS de **cualquier serie** (`indicator: pd.Series`, se le pasa lo que sea — hoy solo existe Stochastic en `df.indicators`, pero funciona igual con RSI/MACD/CVD/etc. el día que existan) contra el precio en esas mismas barras. Decisión clave: los pivotes se detectan **solo sobre el indicador** (reusando `find_pivots(indicator, indicator, length)` — pasar la misma serie dos veces pivota una serie única, mismo truco que ya usaba `stochastic_oscillator` internamente), no se intenta emparejar pivotes de precio y de indicador detectados por separado (eso sí sería ambiguo — ¿qué pasa si no hay un pivote de precio cercano a uno del indicador?). Las 4 clasificaciones (regular/hidden × bullish/bearish) son comparaciones directas de signo entre `price[p2] vs price[p1]` y `indicator[p2] vs indicator[p1]` en los pares de pivotes consecutivos.

**Gotcha real al construir el fixture de test**: la primera versión del fixture sintético fallaba silenciosamente (devolvía `EMPTY`) porque confundí "pivote bajo del indicador" con "valor bajo/alcista del indicador" — puse SPIKES HACIA ARRIBA pensando que servirían como pivotes bajos, cuando `find_pivots` los detectó (correctamente) como pivotes ALTOS. Un pivote bajo de una serie es un mínimo local de esa serie, sin importar qué signifique semánticamente ese valor para el indicador. Además, un fixture con solo 2 picos aislados sobre una meseta plana no basta — `compute_leg` necesita que la serie vuelva a formar un pivote alto claro ENTRE los dos pivotes bajos para "resetear" el estado del leg y confirmar el segundo como un evento nuevo; con una meseta plana entre medio, el algoritmo no confirma el segundo pivote. Fix: fixture con una onda real (meseta alta → valle → meseta alta → valle más alto/bajo → meseta alta), igual que ya advertía `pandas_luarix/tests/builders.py` sobre construir fixtures con pivots "compactos" y verificados a mano.

**Fractal**: reutiliza literalmente la misma primitiva (`find_pivots`) y el mismo patrón origen/confirmación que `_swing_side`, pero en vez de devolver un marker de una vela, devuelve una caja (`top`/`bottom` = high/low de la vela de origen, horizontal hasta la vela de confirmación `length` barras después). No hay lógica nueva de detección, solo una forma de salida distinta sobre el mismo cálculo — decisión explícita para no duplicar el algoritmo de pivots una tercera vez.

### `id` estable en elementos "SMC" — para un futuro tab "Propiedades" 100% frontend

El frontend va a agregar un tab de edición manual de valores (no de estilo) a cada elemento SMC (pivots/equal levels/BOS-CHoCH/order blocks/liquidity sweep/FVG/fractal/divergence — no a bb50/stochastic, que son series densas sin "vela de origen" reasignable). Esa edición vive 100% client-side (sin base de datos nueva en el backend); lo único que necesitaba el backend era un `id` determinístico por elemento para que el frontend pueda reasociar un override guardado tras recalcular. Implementado como un parámetro opcional `indicator_id` en `elements_response()` (`fastapi_server/services/visual_elements.py`) que estampa `id = f"{indicator_id}:{sub_kind}:{anchor}"` (anchor = `time` en marker, `time1` en line/box — la vela de ORIGEN, la parte estable entre repintados) — cada router pasa su propio `indicator_id` del catálogo. Verificado que dos llamadas idénticas devuelven los mismos `id` byte a byte, y que `bb50`/`stochastic-oscillator` quedan sin `id` (no se les pasa `indicator_id`), tal como se decidió.

---

## Rearquitectura de las condiciones de la estrategia de Luis (IPDA) — `app/strategy/`

### `exist_equals` no verifica "existen iguales" — es un detector de liquidity sweep

Al revisar `strategy_conditions.py::exist_equals` con el usuario surgió la confusión de nombre: la función **no calcula** si hay altos/bajos iguales (eso ya lo hace el `SMCIndicator` antes y lo deja en `context.equal_highs`/`context.equal_lows`). Lo que hace es comprobar si el tick actual **barrió con la mecha** un nivel ya marcado como igual y si el **cierre lo recuperó** (sweep válido, se opera) o lo **rompió** (falso quiebre / continuación de tendencia, se descarta). Renombrada conceptualmente a `LiquiditySweepCondition` en la nueva arquitectura (`app/strategy/conditions.py`), sin cambiar la lógica original — solo el nombre y el encapsulamiento.

### Bug real en el gate crítico IPDA original: vetaba también los SHORTs alineados con la tendencia

`calc_strategy_score` (versión anterior a la migración) tenía este gate al principio:

```python
if context.trend == Trend.BEARISH and not equal:
    return 0, structure
```

Esto se ejecuta **antes** de calcular `is_buy`, así que vetaba CUALQUIER entrada (BUY o SELL) en tendencia BEARISH sin sweep — incluyendo los SHORTs, que según `docs/Estrategia Luis.md` (sección 5: "En contexto bajista: Prioridad a ventas; Compras solo tras barridas de liquidez") son la dirección **prioritaria** y no deberían necesitar una barrida de liquidez obligatoria. Solo los LONG contra-tendencia (sección 7) exigen el sweep.

**Fix aplicado**: `CounterTrendRequiresSweepCondition` (`app/strategy/conditions.py`), simétrica y consciente del lado — solo vetea `(BUY en BEARISH sin sweep)` o `(SELL en BULLISH sin sweep)`; si el lado está alineado con la tendencia, pasa automáticamente sin exigir sweep. Test de regresión: `test_strategy_conditions.py::TestIPDAScoreCalculator::test_aligned_sell_in_bearish_without_sweep_is_not_vetoed`.

### Arquitectura nueva: `StrategyCondition` (ABC) en vez de funciones sueltas + dict `structure` armado a mano

Decisión tomada con el usuario (estilo Django serializer fields — un field por regla, con su propio `evaluate`): cada condición de la estrategia de Luis es ahora una clase que hereda de `StrategyCondition` (`app/strategy/base.py`), con `key` (nombre estable para el dict de salida), `score`, `applies_to` (lado al que aplica, o `None` para ambos) y `required` (si falla, vetea el score total — usado solo por `CounterTrendRequiresSweepCondition`). `evaluate(market: MarketState) -> ConditionResult` recibe un objeto que empaqueta `tick`+`df`+`context` más los resultados ya calculados de condiciones anteriores en `market.results`, para que una condición pueda reusar el resultado de otra (p. ej. `OrderBlockConfluenceCondition` lee `market.results["equal"].detail` en vez de recalcular el sweep) — el orden de la lista en `build_ipda_conditions()` importa por esto.

`IPDAScoreCalculator` (`app/strategy/scoring.py`) reemplaza a `calc_strategy_score`: agrega los `ConditionResult` de la lista en un score total y un dict `structure` con las mismas claves que antes (`equal`, `order_block`, `divergence`, `stochastic_in_over_sell`, `stochastic_in_over_buy`, `bb50_entry`, `side`, `ema_value`), verificado contra los consumidores reales (`trade_journal.py:101-110`, `strategies.py`).

`strategy_conditions.py` (root) quedó solo con los helpers que no son condiciones de score: `calc_quantity`, `tick_broke_fractal`, `get_swings`, `create_entries`, `calc_take_proffit`, `calc_stop_loss`. `IPDAStrategy.__init__` (`strategies.py`) ahora recibe `conditions: List[StrategyCondition]` y construye `self.scorer = IPDAScoreCalculator(conditions)`; `backtester.py` pasa `conditions=build_ipda_conditions()` al instanciarla.

**Nota de sesión**: a mitad de esta migración el usuario cambió de rama de git y se perdió una primera versión de estos cambios (nunca se habían commiteado) que además tenía dos bugs propios introducidos por esa sesión anterior (doble conteo de `bb50_entry`, +30 en vez de +15; el gate crítico comentado por completo) — esos bugs específicos **no existían** en el código base real de `deploy_indicators_smc` (el gate estaba activo, sin comentar, y sin duplicación de `bb50_entry`). Esta entrada documenta únicamente el bug que sí estaba presente en el código commiteado: el gate asimétrico de arriba.

---

### BUG #10 (CORREGIDO): `StochasticDivergenceCondition` partía el array por la mitad — no era divergencia real

**Archivo**: `app/strategy/conditions.py:StochasticDivergenceCondition.evaluate`

**Síntoma**: la condición comparaba `min/max` de la primera mitad del buffer contra la segunda mitad. Esto no detecta divergencias reales, solo diferencias arbitrarias entre dos segmentos.

**Causa raíz**: `mid = len(k) // 2` seguido de `close.iloc[:mid].min()` vs `close.iloc[mid:].min()` — el código asumía que partir por la mitad capturaba "primer pivote" vs "segundo pivote", pero no detectaba pivotes en absoluto.

**Fix aplicado**:
- Se reemplazó por detección real de pivotes usando `pandas_luarix._core.divergence.detect_divergence(high, low, indicator, length=5)`.
- El detector identifica swing highs/lows sobre el Stochastic K con el algoritmo leg-based (`find_pivots`), luego compara pares consecutivos de pivotes del mismo tipo (low→low, high→high) contra el precio en esas mismas barras para clasificar las 4 divergencias (regular/hidden × bullish/bearish).
- Se limita a las últimas 60 velas 4h (`df.tail(60)`) para mantener relevancia reciente.
- Se eliminó la importación de `numpy` que habría sido necesaria para la implementación manual — se usa `detect_divergence` directamente.

**Verificación**: probado con datos sintéticos que contienen divergencia real (price LL + indicator HL → regular_bullish) y con datos sin divergencia (price LL + indicator LL → sin evento). También probado que el backtest end-to-end sigue funcionando.

---

## `luarix_rest_api` — motor de backtesting (brokers, ejecución de órdenes, pausa/resume, websocket, endpoints)

Implementado según `docs/plans` (plan aprobado por el usuario, ver historial de plan mode) — `marketdata/services.py`, campos nuevos en `BacktestRun`, `ExecutionState.broker`, `workflows/execution/nodes/execution.py` (Market/Limit Order, Stop Loss, Take Profit), `backtesting/execution/paper_runner.py`, `backtesting/tasks.py`, `backtesting/consumer.py` + `routing.py`, endpoints REST de `brokers`/`backtesting`. Verificado de punta a punta contra sqlite (ver más abajo) con un grafo sintético `on-candle → detector → market-order → stop-loss → take-profit`: `BacktestRun` termina `COMPLETED`, 1 `Trade` con TP real, métricas no nulas, 10 mensajes `backtest_progress` + 1 `backtest_complete` por `InMemoryChannelLayer`, y pausa/resume real verificado con un hilo.

### Colisión de nombres `backtesting` (app Django) vs `backtesting/` (framework Python en la raíz) — `import backtesting.stats` es imposible

`luarix_rest_api/backtesting/` (app Django) y `nexora-trading-framework/backtesting/` (framework Python con `stats.py`/`BacktestStats`) son dos paquetes con el mismo nombre en `sys.path` (el segundo se agrega al final vía `REPO_ROOT` en `settings.py`, ver arriba). Python resuelve `import backtesting` SIEMPRE contra el primer path que tenga un paquete regular con ese nombre — como `BASE_DIR` (`luarix_rest_api/`, con la app Django) está antes que `REPO_ROOT` en `sys.path`, `import backtesting.stats` NUNCA puede llegar al framework Python; no hay merge de namespace packages posible porque ambos tienen `__init__.py` (paquetes regulares, no namespace).

**Fix**: `backtesting/execution/paper_runner.py::_load_root_module()` carga `backtesting/stats.py` por **ruta de archivo explícita** vía `importlib.util.spec_from_file_location` + `module_from_spec` + `exec_module`, con un nombre de módulo sintético (`_framework_backtesting_stats`) que no choca con nada. **Detalle no obvio**: hay que registrar el módulo en `sys.modules[name]` ANTES de `exec_module()` — si no, cualquier `@dataclass` dentro de ese archivo rompe con `AttributeError: 'NoneType' object has no attribute '__dict__'` porque `dataclasses._is_type` busca `sys.modules.get(cls.__module__)` y lo encuentra `None`. `strategy_conditions.py`/`strategies.py` (módulos sueltos en la raíz, sin equivalente Django) no tienen este problema — se importan normal vía el `sys.path.append`.

### `psql_partition.PostgresManager` exige el string "psql_partition" en ALGÚN `DATABASES[...].ENGINE`, no una conexión real

Al armar settings desechables con sqlite para verificar migraciones/lógica sin Postgres real, `marketdata.models.Candle` (hereda `PostgresPartitionedModel`) rompe al importarse (`ImproperlyConfigured: Could not locate the 'psqlextra.backend'`) apenas `settings.DATABASES` no tiene ninguna entrada con `"psql_partition"` en el `ENGINE` — el chequeo (`psql_partition/manager/manager.py::PostgresManager.__init__`) solo mira el string, nunca intenta conectar. Fix para settings desechables: agregar una entrada extra en `DATABASES` (ningún modelo enruta ahí) con `"ENGINE": "psql_partition.backend"` para pasar el check, sin necesidad de credenciales reales.

**La app `marketdata` en sí NO puede migrarse contra sqlite** — su migración usa `psql_partition`'s `create_partitioned_model` (partición RANGE nativa de Postgres), y el `DatabaseSchemaEditor` de sqlite no tiene ese método (`AttributeError: 'DatabaseSchemaEditor' object has no attribute 'create_partitioned_model'`). Para verificar otras apps (`backtesting`, etc.) contra sqlite: dejar `marketdata` en `INSTALLED_APPS` (si no, `RuntimeError: doesn't declare an explicit app_label` al importar `Candle` transitivamente) pero migrar app por app (`migrate <app>`, nunca `migrate` a secas) salteando `marketdata`. Para probar `ensure_coverage`/`get_history`/`PaperBacktestRunner` de verdad, hace falta mockear `ensure_coverage`/`get_history` a nivel del módulo que las importó (`backtesting.execution.paper_runner.ensure_coverage = ...`), no a nivel de `marketdata.services` (el binding ya quedó fijado en el namespace de `paper_runner` al hacer `from marketdata.services import ...`).

### `DATABASES["backtesting"]` (BD real para `marketdata`) sigue sin configurar — no es un bug, es deliberado

`luarix_rest_api/db_router.py::BacktestingRouter` enruta la app `marketdata` a un alias `"backtesting"` en `DATABASES` que **no existe** en `settings.py` (solo existe `"default"`) — las variables `LUARIX_BACKTESTING_SERVER_*` están comentadas en `.env`. Esto es intencional (el usuario aún no tiene ese segundo Supabase/Postgres configurado), NO restaurar esa entrada sin credenciales reales — reventaría `settings.py` con `KeyError` al leer `os.environ[...]`. Mientras tanto, `marketdata` (y por tanto backtests reales contra Binance) no puede funcionar en producción hasta que esas variables se descomenten con credenciales válidas.

### Diseño: dónde se coloca el OCO (Stop Loss/Take Profit) — reacciona al FILL de la entrada, no al mismo pase que la señal

`StopLossExecutor`/`TakeProfitExecutor` (`workflows/execution/nodes/execution.py`) **no llaman `broker.place_oco_order()`** — solo calculan el nivel y lo guardan en `state.run.context_data["_pending_stop_loss"/"_pending_take_profit"]`. El OCO real se coloca en `PaperBacktestRunner._on_execution_report`, cuando llega el reporte `"TRADE"` de la orden de ENTRADA (no de una OCO leg) — recién ahí hay posición abierta de verdad. Motivo: si el OCO se colocara en el mismo pase que la señal (junto con la orden de entrada), quedaría como orden pendiente desde ANTES de que la entrada llenara, pudiendo "cerrar" una posición que técnicamente aún no existe. Implica: solo tiene sentido una entrada con SL/TP pendiente a la vez (no hay tranching ni múltiples posiciones concurrentes esta sesión — mismo alcance ya acordado en el plan).

`_on_execution_report` traduce los execution reports estilo Binance de `PaperBroker` (`report["g"]` = oco_list_id, `-1` si no es leg de OCO; `report["i"]` = order_id, ambos **int**, no string — `_fmt()` en `paper.py` no los toca) a los eventos de `BacktestStats` (`on_signal`/`on_fill`/`on_tp_hit`/`on_sl_hit`). Distingue TP vs SL de una leg OCO por `order_type == "LIMIT"` (TP) vs `"STOP_LOSS_LIMIT"` (SL) — correlaciona `oco_list_id → entry_id` vía `context_data["_oco_entry_map"]`, poblado en el momento en que se coloca el OCO.

### `PaperBroker.get_balance()` siempre devuelve `{"USDT": balance}` — asume quote currency fija

Usado por `PaperBacktestRunner` para actualizar `BacktestStats.update_capital()` en cada vela — funciona para pares `*USDT`, pero si algún día se backtestea un símbolo con otra quote currency, `get_balance()["USDT"]` seguiría siendo el balance real (el atributo interno `_balance` no distingue moneda), solo la KEY del dict está hardcodeada. No es una limitación introducida esta sesión, ya existía en `PaperBroker`.

---

## `luarix_rest_api` — conectar la ejecución del workflow con el gráfico de velas (sesión actual)

Auditoría completa del motor de workflow hecha antes de esta tarea — **282 de 294 tipos de nodo del catálogo no tienen `NodeExecutor`** (solo se cerró el subconjunto necesario para esta tarea: `on-candle`/`manual-trigger` + `swing-high`/`swing-low`/`bos`/`choch`/`liquidity-sweep`/`fvg-bullish`/`fvg-bearish`, todos wrappers delgados sobre `pandas_luarix.smc`, mismo patrón que `equal-high`/`bullish-ob` ya existentes). También confirmado: el motor **no tiene poda condicional real** (`if`/`switch` no existen, el sub-grafo alcanzable se ejecuta siempre completo — los nodos de ejecución ya tenían su propio `_upstream_triggered()` como workaround), y un `WorkflowGraph` en estado `LIVE` **no tiene ningún disparador real** (`dispatch_candle`/`dispatch_manual` no tienen ningún caller — ni Celery beat, ni listener de un feed). Ninguno de los dos se tocó esta sesión (fuera de alcance explícito).

### `swing-high`/`swing-low` tienen un param `lookback` en el catálogo que casi se ignora

El catálogo (`node_definitions.json`) expone `lookback` (default 5) como param configurable de estos dos nodos — la primera versión de `SwingHighExecutor`/`SwingLowExecutor` llamaba `state.df.smc.swing_high()`/`swing_low()` sin argumentos, usando el default de `pandas_luarix` (`length=50`), ignorando por completo lo que el usuario configura en el nodo. Fix: leer `node.config.get("lookback", 50)` y pasarlo como `length=`. Lección: al escribir un wrapper delgado sobre una función con params, siempre cruzar el fixture del catálogo (`params` de esa `NodeDefinition`) contra la firma real de la función que se envuelve — no asumir que "wrapper delgado" significa "sin params".

### `swings()`/`bos_choch()`/`liquidity_sweep()` exigen un mínimo de velas (`require_min_rows`) — los primeros `NodeExecutionLog` de una corrida son `FAILED`, y es correcto

Con `length` default de 50 (o el `lookback` configurado), estas funciones de `pandas_luarix` necesitan `length*2+1` filas antes de poder calcular nada — en un backtest de 140 velas con `length=50`, las primeras 100 pasadas de `bos`/`choch`/`liquidity-sweep` quedan `NodeExecutionLogStatus.FAILED` (excepción atrapada por `engine.execute()`, no crashea el backtest) hasta acumular suficiente historia, recién ahí empiezan a `SUCCESS`. **No es un bug** — es exactamente el comportamiento esperado del *warm-up* de estos indicadores. Cualquier verificación futura de estos executors debe medir "¿tuvo éxito alguna vez pasado el warm-up?", no "¿tuvo cero fallos en total?".

### `bos_choch()` devuelve ambos eventos mezclados — se filtra por columna `structure_type`

Un solo `df.smc.bos_choch()` devuelve filas con columna `structure_type` en `{"BOS", "CHOCH"}` — `BosExecutor`/`ChochExecutor` son la MISMA llamada, filtrada distinto (`df[df["structure_type"] == "BOS"]` / `"CHOCH"`). De igual forma, `fair_value_gaps()` devuelve ambas direcciones mezcladas con columna `direction` (`1`/`-1`) — `FvgBullishExecutor`/`FvgBearishExecutor` filtran por eso. Esto significa que si un grafo conecta AMBOS nodos (`bos` y `choch`) al mismo trigger, `bos_choch()` se recalcula dos veces por vela (una por cada executor) — redundante pero no incorrecto; no se optimizó (memoización por-pase) esta sesión.

### Endpoint de streaming (`GET runs/{id}/stream/`) — sondeo de `NodeExecutionLog`, no push real

Implementado como generador Python (`StreamingHttpResponse`, `content_type="application/x-ndjson"`) que sondea `NodeExecutionLog.objects.filter(run_id=..., id__gt=last_log_id)` cada 300ms — decisión explícita de la sesión (ver plan): se prefirió esto sobre WebSocket/Channels porque `redis`/`channels_redis` no están instalados y este mismo patrón (fetch-stream + aplicar eventos a un store) ya está probado en el frontend para el AI Copilot. El `BacktestConsumer`/WebSocket de la fase anterior queda intacto pero sin usar. Verificado con un test real: `APIClient` lanza el backtest (que corre en un hilo daemon, no Celery — ver siguiente hallazgo) y lee `stream_resp.streaming_content` mientras el hilo corre en paralelo — con 140 velas × 2 nodos llegaron 280 eventos `type=node` más un `type=complete` final, todo correcto.

### `perform_create` lanza el backtest en un `threading.Thread`, no `run_backtest_task.delay()` — decisión temporal, documentada en el propio código

No hay worker Celery ni Redis corriendo en este entorno — encolar con `.delay()` nunca ejecutaría nada. `backtesting/viewsets/run.py::perform_create()` lanza `PaperBacktestRunner(run).run()` en un hilo daemon en su lugar. `backtesting/tasks.py::run_backtest_task` sigue existiendo intacto (código correcto para producción) — el cambio es de una sola línea cuando haya Redis/Celery real. **Importante para debugging futuro**: si el hilo lanza una excepción (p. ej. `marketdata.Candle` no existe porque la BD `backtesting` no está configurada — ver hallazgo de arriba sobre `DATABASES["backtesting"]`), la excepción se pierde silenciosamente (comportamiento por defecto de un `daemon=True` thread sin manejo de excepción) y `BacktestRun.status` se queda pegado en `PENDING` para siempre, sin ningún error visible salvo el traceback en stderr del proceso servidor. Vale la pena, cuando se pase a producción con Celery real, no perder esta ruta de "silencioso si truena" — Celery al menos guarda el traceback en el resultado de la tarea.

### El frontend no tenía login/JWT en ningún lado — usuario dev fijo + endpoint de token

`luarix-web-client` no maneja auth en absoluto (confirmado por grep en todo el repo). Los endpoints nuevos de esta sesión (`strategies`, `workflows` graph sync, `backtesting` runs, `brokers`) usan `IsAuthenticated` + `owner=request.user` — sin login real, se agregó un usuario fijo (`security/migrations/0003_create_dev_user.py`, username `luarix-dev`, password `luarix-dev-2026`, credenciales intencionalmente simples/públicas — SOLO entorno de desarrollo) y se cablearon las vistas estándar de `rest_framework_simplejwt` (`POST /api/v1/auth/token/`, `/api/v1/auth/token/refresh/`) en `luarix_rest_api/urls.py`. El frontend pide un token una vez (login "silencioso" con esas credenciales fijas) y lo manda en cada request — ver `lib/luarix-workflow-api/auth.ts`. Reemplazar por auth real es trabajo aparte, fuera de esta sesión.

### Endpoint mínimo de `strategies` (`StrategyViewSet`) — agregado porque el frontend no tiene ningún Strategy real

Las estrategias del builder (`lib/strategies-data.ts`) son 100% mock — ids tipo string sin relación a ninguna base de datos, y su `config` (`baseOrderSize`/`safetyOrders`/etc.) no tiene nada que ver con lo que `backtesting.BacktestRun.strategy` necesita (FK a un `Strategy` real con symbol/capital/start/side). Se agregó un CRUD mínimo (`strategies/serializers|viewsets/strategy.py`, mismo patrón `ModelViewSet` que `brokers`) — el frontend crea (o reusa, guardado en localStorage) un `Strategy` real la primera vez que se lanza un backtest, vía un diálogo que pide esos 4 campos.

### Frontend: `lib/backtest/simulator.ts` sigue vivo — solo se reemplazó el de la Strategy Builder, no el de `/backtesting` workspace

Hay DOS simuladores/ejecutores distintos en `luarix-web-client` que no se descubrieron hasta editar el frontend: `hooks/useStrategyRunner.ts` (narración falsa nodo-por-nodo con timer, SOLO usado por `strategy-builder.tsx` — ESTE se retiró, reemplazado por `hooks/useBacktestRun.ts` contra el backend real) y `lib/backtest/simulator.ts` + `lib/backtest/repository.ts` (un backtest histórico completo, simulado 100% en el cliente, usado por una página SEPARADA — `components/builder/workspace/backtesting-workspace.tsx`/`backtest-summary.tsx`/`node-properties-dialog.tsx`/`builder-info-panel.tsx`). Esta sesión solo tocó el primero — la página `/backtesting` (o como se llame esa ruta) sigue mostrando resultados 100% simulados en el cliente, no conectados al backend real. Reemplazarla también es trabajo aparte, no cubierto por el plan de esta sesión (que era específicamente sobre la vista Workflow/Candles del builder).

### Frontend: geometría degenerada para BOS/CHoCH/Liquidity Sweep/FVG en vivo — falta el punto de origen

`workflows/execution/nodes/smc.py`'s `bos_choch()`/`liquidity_sweep()`/`fair_value_gaps()` solo exponen la fila del bar de RUPTURA/evento, no el bar de ORIGEN (el pivot que se rompió) — a diferencia de `lib/luarix-api/structure-shapes.ts` (lado FastAPI/`/markets/chart`), que sí tiene ambos puntos. `lib/live-chart-shapes.ts` dibuja estos 3 tipos como una `EqualLevelsShape` con `time1 === time2` (segmento de longitud cero) en vez de una línea real origen→ruptura — visualmente marca el punto correcto, pero no la línea completa que el indicador nativo SMC dibuja. Para una línea real haría falta que los executors expongan también el bar de origen (requiere tocar `pandas_luarix.smc.bos_choch`/`liquidity_sweep`, que hoy no lo calculan como columna de salida) — no se hizo esta sesión.

### Frontend: Market/Limit Order en vivo siempre se dibuja como "buy" — no hay side en el evento

`MarketOrderExecutor`/`LimitOrderExecutor` (backend) solo devuelven `{"exchange_order_id", "quantity"}` en su `NodeExecutionLog.output` — no incluyen el lado (`strategy.side` vive en el backend, no viaja en el evento de stream). `lib/live-chart-shapes.ts` dibuja todo entry marker como `side: "buy"` — simplificación documentada, mismo criterio que ya usaba `deriveTradingShapes` (asume posición larga) para Stop Loss/Take Profit estáticos.

---

## Carga real de `backtests_data/` a `marketdata.Candle` (sesión actual)

Decisiones confirmadas con el usuario: `marketdata` reusa la MISMA BD/proyecto Supabase que el backend principal (no un segundo proyecto separado — `LUARIX_BACKTESTING_SERVER_*` en `.env` ahora son copia literal de `LUARIX_BACKEND_SERVER_*`, `DATABASES["backtesting"]` restaurado en `settings.py`); los ficheros `6M.csv`/`12M.csv` (no son intervalos reales de Binance, no están en `TimeframeChoices`) se omiten al cargar.

### Bug real en `partitioning.py`: importaba el `Candle` equivocado Y el manager configurado se descartaba

`luarix_rest_api/partitioning.py` tenía DOS problemas simultáneos, nunca ejercidos hasta ahora porque `marketdata` nunca se había migrado contra Postgres real:
1. `from app.core.models.market import Candle` — importaba el dataclass plano del framework Python de la raíz (usado en `paper_runner.py` como `FrameworkCandle`), NO el modelo Django real (`marketdata.models.Candle`). `PostgresPartitioningConfig(model=Candle, ...)` con ese `Candle` nunca podría haber funcionado.
2. Última línea del fichero: `manager = PostgresPartitioningManager()` — sin argumentos, SOBRESCRIBÍA la variable `manager` (la que sí tenía la config con `PostgresPartitioningConfig(...)`) con un manager vacío. `PSQLEXTRA_PARTITIONING_MANAGER` apuntaba efectivamente a un manager sin ninguna configuración.

**Fix**: import corregido a `from marketdata.models import Candle`, línea duplicada eliminada.

### La estrategia de particionado original era para datos rodantes, no para histórico permanente

`PostgresCurrentTimePartitioningStrategy(size=months(1), count=3, max_age=relativedelta(months=6))` — creaba solo 3 particiones alrededor de la fecha ACTUAL y borraba automáticamente las de más de 6 meses (pensado para logs/eventos recientes). Con velas históricas reales desde 2017, esto: (a) no tendría partición donde insertar filas de 2017-2025 (el insert fallaría, Postgres exige partición para el rango de la fila), y (b) de haber podido insertar, `pgpartition` corrido más adelante habría BORRADO esas particiones viejas automáticamente.

**Fix**: `PostgresTimePartitioningStrategy(start_datetime=datetime(2017,1,1), size=years(1), count=15)`, SIN `max_age` (nunca borra particiones automáticamente) — 15 particiones anuales, 2017 a 2031.

### Bug de la librería `django-postgres-partition` (o incompatibilidad con Django 6.0.6): el motor de migraciones no reconstruye `PartitioningMeta` en el modelo "state"

Al correr `manage.py migrate marketdata` normal (contra Postgres real por primera vez), Django reportaba `Applying marketdata.0001_initial... OK` — pero la tabla `marketdata_candle` NUNCA se creaba (confirmado con `pg_class`/`information_schema` directo, no solo `django_migrations`). Además, `django_migrations` YA tenía ambas migraciones marcadas como aplicadas desde antes de esta sesión (posible `--fake` accidental o un intento anterior que falló a medias) — sin que la tabla existiera. Al forzar el error real (`call_command` directo en vez de `manage.py`, para ver el traceback completo en vez del mensaje genérico "OK"), apareció: `django.core.exceptions.ImproperlyConfigured: Model 'Candle' is not properly configured to be partitioned. Create the PartitioningMeta class as a child of 'Candle'.` — pero el modelo REAL (`from marketdata.models import Candle`) sí tiene `_partitioning_meta` seteado correctamente (confirmado por inspección directa). El problema es específico del modelo "state" que el framework de migraciones reconstruye dinámicamente (`to_state.apps.get_model(app_label, self.name)`) durante `database_forwards` — `PostgresPartitionedModelState._pre_render` sí arma un `PartitioningMeta` a partir de `partitioning_options` (que el `.py` de la migración sí serializa bien), pero por algún motivo (no identificado con certeza — sospecha: `bases`/la metaclase de `PostgresPartitionedModel` no termina de procesar el `PartitioningMeta` reconstruido dinámicamente en este combo Django 6.0.6 + versión instalada de `psql_partition`) el modelo reconstruido nunca termina con `_partitioning_meta` seteado.

**Workaround aplicado** (sin tocar los ficheros de migración, que están correctos y servirían tal cual con una versión de la librería compatible): se creó la tabla partitioned DIRECTO con el modelo REAL, bypaseando el executor de migraciones:
```python
from django.db import connections
from marketdata.models import Candle
with connections["backtesting"].schema_editor() as se:
    se.create_partitioned_model(Candle)
```
Luego `manage.py migrate marketdata --fake --database=backtesting` para que el bookkeeping de `django_migrations` quede consistente con el estado real, y `manage.py pgpartition --yes` para crear las 15 particiones hijas reales. **Lección para la próxima vez que se toque `marketdata`**: si se agrega un campo nuevo a `Candle` y hace falta una migración nueva, probablemente haga falta el mismo workaround (crear/alterar la tabla a mano vía `schema_editor` + modelo real, luego `--fake`) en vez de confiar en que `manage.py migrate` sola alcance — no se investigó a fondo la causa raíz en `psql_partition` por tiempo, pero el síntoma (```ImproperlyConfigured``` en la migración, modelo real bien configurado) es reproducible y ahora está documentado.

### `pd.to_datetime` con formato fijo falla en `close_time` — filas mezclan con/sin microsegundos

Los CSV de `backtests_data/<symbol>/<interval>.csv` (`date,open,high,low,close,volume,close_time`) tienen `close_time` con microsegundos en casi todas las filas (`...23:59:59.999000+00:00`) pero NO en todas (`...16:00:00+00:00` sin fracción, en algunas filas de intervalos largos) — `pd.to_datetime(..., utc=True)` sin `format` explícito infiere un formato fijo del primer valor y truena en la primera fila que no calza. Fix: `format="ISO8601"` (pandas 2+), que tolera precisión variable dentro de ISO8601 válido.

### Comando `load_backtests_data` (`marketdata/management/commands/`)

Recorre `backtests_data/<symbol>/<interval>.csv`, `provider="binance"` fijo, usa `Candle.objects.bulk_create(..., update_conflicts=True, unique_fields=[provider,symbol,interval_code,time], update_fields=[...])` — upsert real (correr de nuevo no duplica filas), respeta la PK compuesta. Omite cualquier fichero cuyo nombre (sin `.csv`) no esté en `TimeframeChoices` con datos reales de Binance (hoy: `4h`, `1d`, `1M` — `6M`/`12M` se saltan). Resultado real cargado: **295,382 velas, 19 símbolos** (42,029 en `1d`, 1,404 en `1M`, 251,949 en `4h`).

### Sync de grafo (`PUT/GET workflows/strategies/{id}/graph/`) hace reemplazo TOTAL, no diff

`WorkflowGraphSyncSerializer.save()` borra TODOS los `WorkflowNode`/`WorkflowEdge` existentes del grafo antes de recrearlos — decisión explícita del plan (coincide con cómo el frontend ya trata el grafo como un blob único). Efecto colateral real: como `WorkflowNode` tiene `NodeExecutionLog` en cascada (`on_delete=CASCADE`), sincronizar el grafo de una Strategy que ya tiene backtests corridos **borra el historial de logs de ejecución de esos backtests** (no los `BacktestRun`/`Trade` en sí, esos no dependen de `WorkflowNode` — pero sí el detalle nodo-por-nodo). Aceptado conscientemente para esta sesión; si en el futuro se necesita conservar el historial de ejecución al reeditar el grafo, haría falta un diff incremental en vez de borrar-y-recrear.

---

## Cache de velas real para `/markets/chart` (sesión actual)

Se expuso `marketdata.services.ensure_coverage()`/`get_history()` (ya construidos para el motor de backtesting) como un endpoint DRF real (`GET /api/v1/marketdata/candles/`, `CandleViewSet` con solo `ListModelMixin` — sin `retrieve`, la PK compuesta de `Candle` no tiene un "detail by pk" con sentido). Se seedeó una `BrokerAccount(broker=BINANCE, owner=luarix-dev, testnet=False)` vía data migration (`brokers/migrations/0003_seed_system_binance_account.py`, mismo patrón que `security/migrations/0003_create_dev_user.py`) — solo por comodidad/testing, un usuario real crea la suya propia (el endpoint ya filtra `broker_account` por `owner=request.user`).

**Verificado de punta a punta contra la BD real y Binance real** (no un sandbox sqlite esta vez, ya había 295k velas reales cargadas): un rango ya cubierto se sirve sin insertar nada nuevo; un rango que se extiende más allá de lo cargado dispara `ensure_coverage()`, trae 65 velas reales de Binance (2026-07-01 a 2026-07-12, BTCUSDT 4h) y las persiste sin duplicados (`unique_together` compuesto respetado); repetir el mismo request no vuelve a insertar nada.

### Bug preexistente encontrado (no introducido esta sesión, no arreglado): `REST_FRAMEWORK.EXCEPTION_HANDLER` apunta a un módulo que no existe

`settings.py`: `'EXCEPTION_HANDLER': 'apps.security.exceptions.exception_404_handler'` — el paquete `apps` no existe en este proyecto (ni en `luarix_rest_api/` ni en la raíz). Mientras ningún endpoint necesite el exception handler custom (el camino feliz), nunca se nota. En cuanto CUALQUIER vista de CUALQUIER app levanta una excepción que DRF necesita manejar (ej. `get_object_or_404` fallando, un `Http404`, un `ValidationError` no atrapado a mano) — DRF intenta importar ese handler y explota con `ImportError: Could not import 'apps.security.exceptions.exception_404_handler'`, devolviendo un 500 en vez del código de error que debería. Se encontró probando el `broker_account` inválido de `CandleViewSet` (esperaba 404, la vista entera revienta). **No es un bug de esta sesión ni de `marketdata`** — es un problema global de configuración de DRF que afecta cualquier endpoint del proyecto que dependa de manejo de excepciones estándar. No se arregló (fuera de alcance de esta tarea), pero vale la pena saberlo antes de asumir que un 500 inesperado en cualquier endpoint es un bug de la lógica de esa vista en particular.

---

## Repartición de `Candle` por (broker, símbolo) en vez de por año (sesión actual)

El usuario señaló correctamente que particionar `Candle` por RANGE de fecha (`PostgresTimePartitioningStrategy`, 15 particiones anuales fijas 2017-2031) era un muro arbitrario: cualquier vela con `time` fuera de ese rango pre-creado rompe el INSERT ("no partition of relation... found for row") hasta correr `pgpartition` a mano. Se cambió a particionado LIST sobre una columna nueva `provider_symbol` (`f"{provider}_{symbol}".lower()`, calculada en Python, NO con `GeneratedField` — ver razón abajo) — una partición por símbolo (`marketdata_candle_binance_btcusdt`, etc.), sin ningún límite de fecha dentro de cada una. `marketdata/partition_utils.py::ensure_partition_exists()` crea la partición de un símbolo la primera vez que aparece (antes de cualquier insert, en `_bulk_upsert_candles`/`load_backtests_data`) — sin `pgpartition`, sin mantenimiento programado; `luarix_rest_api/partitioning.py` ya no tiene ninguna `PostgresPartitioningConfig` para `Candle`.

### Descubrimiento clave: `makemigrations` normal NO detecta modelos particionados de `psql_partition` — hace falta `pgmakemigrations`

Al regenerar las migraciones de `marketdata` para el nuevo esquema, `manage.py makemigrations marketdata` (el comando estándar de Django) escribió un `CreateModel` PLANO, sin `partitioning_options` ni `PostgresCreatePartitionedModel` — como si `Candle` fuera un modelo cualquiera. Pasó lo mismo contra sqlite desechable Y contra las settings reales (no es un problema de qué BD está configurada).

**Causa raíz**: `psql_partition` parchea `MigrationAutodetector.add_operation` (`psql_partition/backend/migrations/patched_autodetector.py::patched_autodetector()`, un context manager) para poder emitir `PostgresCreatePartitionedModel` en vez de `CreateModel` cuando el modelo es un `PostgresPartitionedModel` — pero ese parche NUNCA se aplica automáticamente (no está en `AppConfig.ready()`, no se activa por tener `psql_partition` en `INSTALLED_APPS`). La única forma de activarlo es el comando **`python manage.py pgmakemigrations`** (`psql_partition/management/commands/pgmakemigrations.py`), que envuelve el `makemigrations` real dentro de `with postgres_patched_migrations(): ...`. Usar `makemigrations` a secas para cualquier app con un `PostgresPartitionedModel`/`PostgresViewModel`/`PostgresMaterializedViewModel` silenciosamente genera una migración INCORRECTA (parece funcionar — no tira error — pero pierde toda la config de particionado).

**Lección para cualquier cambio futuro al modelo `Candle` (o cualquier otro modelo particionado)**: SIEMPRE `python manage.py pgmakemigrations <app>`, nunca `python manage.py makemigrations <app>` a secas. Si por error ya se generó con el comando equivocado, se nota mirando el `.py` de la migración: si dice `migrations.CreateModel` en vez de `psql_partition...PostgresCreatePartitionedModel`, o si no tiene `partitioning_options`, está mal — hay que borrarla y regenerar con `pgmakemigrations`.

### El bug de `migrate` normal (`ImproperlyConfigured`, ver sección de la sesión pasada) sigue apareciendo igual con la migración bien escrita

Confirmado esta sesión: incluso con la migración generada CORRECTAMENTE (`pgmakemigrations`, con `PostgresCreatePartitionedModel`/`partitioning_options` completos), `manage.py migrate marketdata` normal contra Postgres real sigue sin crear la tabla (reporta "OK" pero no pasa nada) — el bug de reconstrucción de estado (`model._partitioning_meta` no seteado en el modelo "state" dinámico) es independiente de qué comando escribió el archivo. **Se sigue necesitando el mismo workaround**: `schema_editor.create_partitioned_model(Candle)` + `schema_editor.add_default_partition(Candle, "default")` directo con el modelo REAL (no vía `migrate`), luego `migrate --fake` para dejar `django_migrations` consistente.

### `PostgresAddDefaultPartition` — un extra útil que trae LIST partitioning y RANGE no tiene

`pgmakemigrations` agregó sola una segunda operación, `PostgresAddDefaultPartition(model_name="Candle", name="default")` — crea una partición `marketdata_candle_default` que captura cualquier fila cuyo valor de partición no matchee ninguna partición explícita, en vez de que el INSERT falle. Es una red de seguridad real: si `ensure_partition_exists()` tuviera un bug o hubiera una condición de carrera, la fila cae en `default` en vez de perderse/tronar — verificado que queda en 0 filas en operación normal (todo se rutea a su partición de símbolo correcta). RANGE partitioning no tiene un equivalente directo (habría que definir un rango explícito tipo MAXVALUE).

### Migración de datos real: DROP + recreate + reload, no ALTER

Postgres no permite cambiar la estrategia de particionado de una tabla existente (RANGE→LIST) in situ. Se hizo `DROP TABLE marketdata_candle CASCADE` (se lleva las 15 particiones anuales), se recreó con el nuevo esquema (workaround de arriba), y se re-corrió `load_backtests_data` completo — reprodujo exactamente las mismas 295,382 filas (verificado símbolo por símbolo contra los CSV, igual que la sesión pasada) y creó solo 19 particiones (`marketdata_candle_binance_<symbol>`, una por símbolo real encontrado) en vez de las 15 fijas por año. Las 65 velas extra de BTCUSDT 4h (2026-07-01→07-12, traídas en vivo en la sesión anterior, no estaban en los CSV) no se resembraron — se auto-sanan solas la próxima vez que alguien pida ese rango.

**Verificado el problema original ya no existe**: se pidió un símbolo nunca visto (`ADAUSDT`, no estaba entre los 19) vía el endpoint real — la partición `marketdata_candle_binance_adausdt` se creó sola, sin ningún paso manual, y trajo velas reales de Binance. Se insertó (directo, sin pasar por Binance) una vela de BTCUSDT en 2010 y otra en 2035 — ambas fuera del viejo rango 2017-2031 — y ambas se insertaron sin ningún error de partición, confirmando que el muro de fechas arbitrario desapareció.

---

## Log persistente y legible de la ejecución de un backtest (`BacktestRun.logs`, sesión actual)

Se agregó `BacktestRun.logs` (JSONField) — narrativa curada (solo `NodeExecutionLog` con `status=success` y `output` truthy, mismo criterio que `_upstream_triggered()`) construida UNA sola vez al final de `PaperBacktestRunner.run()` (sin escrituras extra durante la corrida), y las filas de `NodeExecutionLog` de esa corrida se borran justo después — la tabla nunca acumula más allá de la(s) corrida(s) activa(s), pero el streaming en vivo (que sí lee `NodeExecutionLog` mientras la corrida está corriendo) no se tocó. Se construye/guarda tanto en el camino normal/cancelado como en el `except Exception` (para que una corrida que falla a mitad de camino tampoco deje `NodeExecutionLog` creciendo).

### Hallazgo grande: `workflows` y `backtesting` tampoco estaban realmente migrados contra la BD real — mismo síntoma que `marketdata`, mucho más extendido de lo que parecía

Al intentar correr un backtest real por primera vez contra Postgres real (no sqlite desechable) para esta verificación, aparecieron DOS problemas en cadena, ninguno relacionado con esta tarea en sí:

1. **`workflows_workflowrun`/`workflows_nodeexecutionlog` no existían** — `workflows.0001_initial` estaba marcada aplicada en `django_migrations` pero solo había creado `NodeCategory`/`NodeDefinition`/`WorkflowGraph`/`WorkflowNode`/`WorkflowEdge`; las otras 2 tablas (definidas en el MISMO fichero de migración) nunca se crearon. Además, las 5 tablas que sí existían estaban desactualizadas respecto al modelo actual (`workflows_workflowgraph` tenía una columna `is_active` que ya no existe en el modelo, y le faltaban `status`/`active_run_id`) — ninguna tenía datos reales (`0` filas en las 5, y `nodedefinition` en particular tenía 0 filas — los fixtures del catálogo tampoco se habían cargado nunca contra la BD real). Se resolvió igual que `marketdata`: se confirmó que no había datos reales, se hizo `DROP TABLE ... CASCADE` de las 5 existentes, se limpió `django_migrations` para `workflows`, y se corrió `migrate workflows` de verdad — esta vez sin el bug de reconstrucción de estado de `psql_partition` (workflows no usa particionado, es un `migrate` normal). Se cargaron también los fixtures (`node_categories`/`node_definitions`, 313 objetos) que nunca habían llegado a la BD real.
2. **`backtesting_backtestrun` también estaba desactualizada** — le faltaban `workflow_run_id`, `data_source_account_id`, `timeframe` (campos agregados al modelo en una sesión anterior, cuyas migraciones nunca se aplicaron de verdad contra Postgres real). Mismo fix: confirmar 0 filas reales, `DROP TABLE ... CASCADE` de `backtestrun`/`trade`/`tradeevent`, limpiar `django_migrations` para `backtesting`, `migrate backtesting` de verdad.

**Lección importante**: hasta esta sesión, prácticamente ningún trabajo de backend de las sesiones anteriores (motor de workflow, motor de backtesting) había sido verificado alguna vez contra la BD real de Postgres — todo el testing previo usó sqlite desechable, y en algún punto alguien (o algún intento anterior) marcó migraciones como aplicadas (`--fake` o similar) sin que las tablas realmente reflejaran el modelo. **Antes de asumir que una app está "lista" en producción, conviene comparar columnas reales (`information_schema.columns`) contra `Model._meta.get_fields()`**, no confiar en que `django_migrations` diga la verdad.

### Bug real encontrado y arreglado: `PaperBacktestRunner` rompía el camino de backtest más común (`PAPER` como fuente de datos)

`get_history()` ganó un parámetro `provider` opcional en la tarea de reparticionado (para podar a la partición correcta) — `PaperBacktestRunner.run()` lo llamaba con `provider=run.data_source_account.broker.lower()` sin excepción. Cuando `data_source_account.broker == PAPER` (el camino más común — `ensurePaperBrokerAccount()` en el frontend, backtests que reusan datos ya cacheados), esto pasaba `provider="paper"`, filtrando por una partición `paper_<symbol>` que **nunca existe** (los datos reales siempre están cacheados bajo el provider real, ej. `binance_<symbol>`) — `history_df` quedaba vacío, el loop de velas nunca corría, `BacktestStats._last_candle_time` nunca se seteaba, y `stats.finish()` caía al fallback `datetime.now()` (naive) mientras `start_time` seguía aware, rompiendo con `TypeError: can't subtract offset-naive and offset-aware datetimes`.

**Fix**: si `data_source_account.broker == PAPER`, se pasa `provider=None` a `get_history()` (mismo criterio que `ensure_coverage()` ya usaba — PAPER es agnóstico a la fuente real, lee lo que ya esté cacheado sin importar qué broker lo trajo).

### Efecto secundario descubierto (no arreglado, es del framework Python raíz, no de esta sesión): `BacktestStats.avg_monthly_return`/`apr` pueden devolver un número complejo

Si `final_capital` termina siendo negativo (posible con un grafo de prueba sin gating de "ya tengo posición abierta" — cada disparo del trigger abre una entrada nueva sin límite), `ratio = final_capital / initial_capital` es negativo, y `ratio ** (1/months)` en Python devuelve un **complejo** cuando la base es negativa y el exponente no es entero — `Field 'avg_monthly_return' expected a number but got (826.16-2798.97j)`. No se tocó (es `backtesting/stats.py`, framework Python de la raíz, ya establecido como "no se modifica" en sesiones anteriores) — se evitó en la verificación usando un grafo con un único disparo de entrada en vez de dejar que un detector ruidoso (swing-high con lookback corto) dispare una entrada nueva en cada vela.

---

## Log persistente de la estrategia en vivo (`Strategy.logs`) + limpieza diaria por Celery (sesión actual)

Mismo espíritu que `BacktestRun.logs`, pero para `dispatch_manual`/`dispatch_candle` (`workflows/execution/dispatch.py`) — la ejecución en vivo/manual de un grafo desplegado, que a diferencia de un backtest **no tiene un final natural** (`WorkflowGraph.active_run` vive mientras el grafo esté LIVE/PAUSED, recibiendo una pasada de `engine.execute()` por cada vela o disparo manual, potencialmente para siempre). Por eso el diseño es incremental en vez de "una vez al final":

- La lógica de curado (`NodeExecutionLog` con `status=SUCCESS` y `output` truthy → narrativa legible) se extrajo a `workflows/execution/log_utils.py` (`summarize_log_entry()` + `curate_and_append_logs(run, target, field_name)`), reusada tanto por `PaperBacktestRunner._build_and_save_logs()` (una sola llamada, al final) como por `dispatch.py` (una llamada después de CADA `engine.execute()`, tanto en `dispatch_manual` como en `dispatch_candle`).
- A diferencia de `BacktestRun.logs` (que se asigna una vez), `curate_and_append_logs` **agrega** (`target.<field> + new_entries`) — necesario porque `Strategy.logs` se alimenta de muchas pasadas separadas a lo largo de toda la vida del despliegue, no de una corrida acotada.
- `NodeExecutionLog` se limpia después de cada pasada igual que en el backtest — nunca acumula más allá de la pasada en curso, ni siquiera en el caso en vivo.
- Nuevo campo `Strategy.logs` (JSONField, `strategies/migrations/0002_add_strategy_logs.py`) — vive en `Strategy` (no en `WorkflowGraph`/`WorkflowRun`) porque sobrevive a ciclos de stop/redeploy, a diferencia de `active_run`.
- Tarea Celery `strategies.tasks.trim_strategy_logs` (`LOG_RETENTION_DAYS = 7`) recorre `Strategy.objects.exclude(logs=[])` y filtra cada lista de logs por `entry["tick_time"] >= cutoff` (comparación directa de strings ISO8601, sin parsear — ya vienen normalizados así). Registrada como `PeriodicTask`/`CrontabSchedule` diario (03:00 UTC) vía migración de datos (`strategies/migrations/0003_seed_trim_strategy_logs_periodic_task.py`), mismo patrón `RunPython` idempotente que `brokers/migrations/0003_seed_system_binance_account.py`. Sin worker/beat real corriendo en este entorno (sigue faltando Redis) — verificado llamando `trim_strategy_logs()` directo.

### Verificado contra la BD real (grafo LIVE de verdad, vía `workflows.execution.lifecycle.deploy()`)

- 3 pasadas de `dispatch_candle` sobre un grafo LIVE: `Strategy.logs` creció monótonamente (2, luego 3, luego 2 entradas nuevas — el nodo `on-candle` y un nodo de prueba siempre-truthy aportan 2 por pasada, un tercer nodo condicional aportó 1 extra en la pasada donde su output fue truthy), nunca se pisó lo acumulado antes, y `NodeExecutionLog` quedó en 0 filas para ese `run` después de cada pasada.
- `dispatch_manual` sobre el mismo grafo LIVE reusa el mismo `active_run` (confirmado `run.pk == graph.active_run_id`) y agrega al mismo `Strategy.logs` (2 entradas nuevas: `manual-trigger` + el nodo alcanzable desde él).
- Se insertaron entradas sintéticas con `tick_time` de hace 8 días y de hace 1 día, se llamó `trim_strategy_logs()` directo: sobrevivió solo la reciente.
- Se re-confirmó (sanity check, no specific a esta tarea) que el `PaperBacktestRunner` refactorizado para usar `curate_and_append_logs()` en vez de su propia copia de la lógica sigue produciendo el mismo resultado que antes, y que un backtest **nunca** toca `Strategy.logs` (queda en `len == 0` tras una corrida completa) — la separación entre los dos mecanismos (`BacktestRun.logs` para corridas acotadas, `Strategy.logs` para despliegues en vivo sin final) es limpia, no se mezclan.
- Toda la data sintética de esta verificación (2 `Strategy` de prueba, sus `WorkflowGraph`, 2 `BacktestRun`, 1 `BrokerAccount`, categoría/definiciones de nodo de prueba) se borró de la BD real al terminar — confirmado `0` filas restantes.

---

## Auditoría de modelado (MER): catálogos reales `Broker`/`Instrument` + limpieza (sesión actual)

Auditoría a nivel de modelos (no de lógica de negocio) comparando 5 capacidades de producto contra el código real, con 3 agentes de exploración + 1 agente de planificación. Diseño completo documentado en fases (0 a 4); esta sesión ejecutó **Fase 0** (limpieza) + **Fase 1** (catálogos `Broker`/`Instrument` + `NodeDefinition.is_executable`). Fases 2-4 (lifecycle/versionado de `WorkflowGraph`, conectar la app `indicators` nunca poblada, trazabilidad `Trade`→señal) quedan como roadmap diseñado y aprobado, sin ejecutar.

### Fase 0 — limpieza
- `Strategy.is_active` eliminado (confirmado que ningún código lo leía — el lifecycle real vive en `WorkflowGraph.status`).
- `ConditionType`/`Condition` (`strategies/models/conditions.py`) eliminados — confirmado 100% sin uso (ni serializer, ni viewset, ni motor de ejecución), predataban el modelo de grafo de nodos.
- Timeframe unificado: `core/choices.py` ahora tiene `TIMEFRAME_PANDAS_FREQ` como única fuente (antes duplicado en `marketdata/services.py`), y el fixture `node_definitions.json` corrigió el casing de sus opciones de timeframe ("1D"/"1W" → "1d"/"1w", bug ya anotado antes en `workflows/execution/dispatch.py`).

### Fase 1a — `Broker` reemplaza `AvailableBrokerChoices` (no lo duplica)

Se eliminó `AvailableBrokerChoices` (Django `TextChoices`) por completo — antes duplicado como `Enum` plano en `app/brokers/factory.py::AvailableBrokers` (fuente que de verdad decide qué cliente HTTP instanciar, y que sigue existiendo — el usuario la adapta directamente, fuera de alcance de esta sesión). `BrokerAccount.broker` pasó de `CharField(choices=...)` a `ForeignKey(Broker, on_delete=PROTECT, db_column="broker")`, con `Broker.code` como PK (mismos valores que ya tenía la columna, migración sin backfill). Los 4 call sites que hacían `.broker.lower()`/`== AvailableBrokerChoices.PAPER` (`marketdata/services.py`, `marketdata/viewsets/candle.py`, `backtesting/execution/paper_runner.py`) pasaron a usar `.broker_id` (el string del PK sin seguir la FK) y el literal `"PAPER"`.

También se corrigió el fixture `node_definitions.json`: el param `"exchange"` de `market-stream`/`ticker` tenía una lista TOTALMENTE inventada e inconsistente (Binance/Bybit/OKX/Coinbase/Kraken) — se reemplazó por los 5 códigos reales, y el nuevo endpoint `GET /workflows/node-catalog/` además sobreescribe esas opciones dinámicamente desde `Broker.objects.filter(is_active=True)` en cada request, para que nunca vuelva a desincronizarse si se agrega/desactiva un broker.

### Fase 1b — `Instrument`, y el hallazgo grande de esta sesión: `marketdata` vive en OTRA base de datos física

El plan original (agente de diseño) proponía crear `Instrument` dentro de la app `marketdata` — **esto era incorrecto y se descubrió recién al aplicar la migración contra la BD real**: `luarix_rest_api/db_router.py::BacktestingRouter` enruta TODA la app `marketdata` (incluido cualquier modelo nuevo agregado ahí) a la base de datos física `"backtesting"` (TimescaleDB, credenciales `LUARIX_BACKTESTING_SERVER_*`), mientras que `strategies`/`backtesting` (la app Django)/`brokers` viven en `"default"`. Un FK real de Postgres **no puede cruzar dos bases de datos físicas distintas** — al migrar, `strategies.0005` explotó con `relation "marketdata_instrument" does not exist` porque la tabla efectivamente existía en la BD `backtesting`, no en `default`, donde `strategies` intentaba crear el constraint.

**Fix**: se revirtió la migración (`migrate marketdata 0001_initial`), se borró el modelo/migración de `marketdata`, y `Instrument` se recreó en la app `core` (ya compartida por todas las apps de `default`, sin modelos concretos previos — hogar natural para un catálogo transversal). `Candle.symbol`/`Candle.provider` de todos modos iban a quedar como string plano por diseño (particionado nativo), así que esta reubicación no pierde nada — `marketdata` nunca necesitó una FK real a `Instrument`.

**Lección para el futuro**: antes de agregar un modelo nuevo a una app, revisar `db_router.py` — no todas las apps del proyecto comparten base de datos física, y `makemigrations`/`check` NO detectan este problema (ambos pasan limpio); solo se manifiesta al aplicar la migración contra Postgres real.

Alcance final de la conversión a FK: **solo** `Strategy.symbol`, `Fractal.symbol`, `BacktestRun.symbol` (campos de configuración de baja frecuencia de escritura) — `Order.symbol`/`Fill.symbol`/`Position.symbol`/`IndicatorElementBase.symbol`/`DetectionRun.symbol` quedan como `CharField` (tablas transaccionales/generadas por el sistema, y `indicators` ni siquiera está conectada todavía). El seed (`core/migrations/0001_fase1b_instrument_catalog.py`) tomó `SELECT DISTINCT symbol` de `Candle` (cruzando el router automáticamente, sin `.using()` explícito — el ORM resuelve la conexión sola incluso dentro de una migración de otra app) ∪ `Strategy` ∪ `Fractal` ∪ `BacktestRun` — 20 símbolos reales, cobertura 100% confirmada contra la BD real de producción.

Call sites corregidos para usar `.symbol_id` (el string plano) en vez de `.symbol` (ahora una instancia de `Instrument`): `backtesting/execution/paper_runner.py` (6 usos: `ensure_coverage`, `get_history`, `BacktestStats(symbol=...)`, `PaperBroker.on_candle`, `FrameworkCandle.from_dataframe_row`, `place_oco_order`), `workflows/execution/runner.py` (`WorkflowRunner.run_backtest`), `workflows/execution/nodes/execution.py` (`MarketOrderExecutor`/`LimitOrderExecutor`, `OrderRequest(symbol=...)`). `workflows/execution/dispatch.py::dispatch_candle` no necesitó cambios — `strategy__symbol=tick.symbol` ya resuelve correctamente contra el PK de la FK sin tocar código.

### Fase 1c — `NodeDefinition.is_executable`

Confirmado: de los 294 `NodeDefinition` del fixture, solo 21 tienen un `NodeExecutor` real registrado — el resto queda `SKIPPED` silenciosamente si se coloca en un grafo. Se agregó `is_executable` (BooleanField, default False), sembrado por migración con la lista exacta de 21 `type_id` verificados por grep contra `workflows/execution/nodes/*.py`. Nuevo endpoint de solo lectura `GET /workflows/node-catalog/` (antes **no existía ningún endpoint** que sirviera `NodeCategory`/`NodeDefinition` al frontend) — verificado por HTTP real: 19 categorías, 294 definiciones, exactamente 21 con `is_executable=true`. Se agregó `workflows.execution.registry.registered_type_keys()` (antes solo había `get_executor(key)`, sin forma pública de listar todo lo registrado) y el management command `check_node_catalog_consistency`, que compara ambas fuentes y reporta discrepancias — corrido contra la BD real, `0` discrepancias.

### Verificación end-to-end contra Postgres real

- Los 5 `Broker` sembrados coinciden con los códigos ya usados; `BrokerAccount` (`system-binance`) sigue apuntando a `BINANCE` tras la conversión a FK; `Broker.PROTECT` bloquea borrar un broker en uso (probado con un `BrokerAccount` real).
- `Instrument`: 20 símbolos reales sembrados; crear una `Strategy` con un symbol inexistente falla con `IntegrityError` (antes aceptaba cualquier string); `Strategy.symbol` como FK real funciona de punta a punta.
- Backtest real completo (camino PAPER, mismos datos cacheados de sesiones anteriores) sigue funcionando igual tras las 3 conversiones a FK (`Broker`, `Instrument`, `is_executable`) — `status=completed`, logs curados generados normalmente.
- Toda la data sintética de esta verificación (1 `Strategy`, 1 `WorkflowGraph`, 1 `BacktestRun`, 1 `BrokerAccount` de prueba) se borró al terminar — los 5 `Broker` y 20 `Instrument` sembrados NO se tocaron (son catálogo real, no datos de prueba).

---

## Fase 2: lifecycle real (deploy/pause/resume/stop por API) + versionado/auditoría de WorkflowGraph (sesión actual)

Se expuso `workflows/execution/lifecycle.py` (antes sin ningún endpoint) vía `POST /workflows/strategies/<id>/graph/lifecycle/` (`{"action": "deploy"|"pause"|"resume"|"stop"}`), y se agregó auditoría/versionado real:

- **`WorkflowGraphSnapshot`** — foto de nodes/edges tomada antes de cada `deploy()`/`resume()` exitoso (`reason=DEPLOY`) y antes de cada PUT que reemplaza un grafo YA EXISTENTE (`reason=MANUAL_SAVE`; el primer PUT que crea el grafo no genera snapshot). Punto sutil manejado con cuidado: el snapshot se toma sobre el grafo obtenido ANTES de `update_or_create()` en `WorkflowGraphSyncSerializer.save()` — tomarlo después habría capturado los valores NUEVOS del payload en vez de los viejos que se están reemplazando.
- **`WorkflowDeployment`** — una fila por cada llamada a `deploy/pause/resume/stop`, incluyendo intentos FALLIDOS de `deploy`/`resume` (con `validation_errors` poblado, `resulting_run`/`snapshot` en `None`) — auditoría completa, no solo de lo exitoso.
- **`resume()` refactorizado** para no perder la auditoría: antes llamaba a `deploy()` tal cual (correcto en comportamiento) pero habría quedado mal-etiquetado como `action="deploy"` en `WorkflowDeployment`. Se extrajo `_deploy_or_resume(graph, action, performed_by)` compartido, y `deploy()`/`resume()` solo difieren en qué `action` pasan — verificado que un `resume()` real queda auditado como `RESUME`, no genera un `DEPLOY` extra, y reusa el mismo `active_run` (no pierde contexto).
- **`workflows/models/graph_serialization.py`** (nuevo) — `nodes_to_json()`/`edges_to_json()` extraídas de `WorkflowGraphReadSerializer` para reusarlas también en el snapshot, sin crear un ciclo de import `serializers`↔`execution` (ninguno de los dos importaba al otro; la función compartida vive en `models/`, capa común a ambos).
- **`Strategy.status`** — property de solo lectura (NO columna nueva) que devuelve `workflow_graph.status`, con import LOCAL de `WorkflowGraphStatus` dentro del método (no a nivel de módulo) para mantener `strategies` desacoplado de `workflows` — mismo criterio que ya usa `workflows/models/graph.py` con la FK string `"strategies.Strategy"` en la dirección opuesta.

### CRUD/lectura faltantes, agregados en esta misma pasada (a pedido explícito)

- **`Broker`** (`brokers/viewsets/broker.py`) y **`Instrument`** (`core/viewsets/instrument.py`, con `core/urls.py` nuevo — la app `core` no tenía rutas) — `ModelViewSet` completo, `IsAuthenticated` (mismo criterio que el resto del proyecto, sin precedente admin-only). Ambos con `destroy()` sobrescrito (`core/viewsets/mixins.py::ProtectedDestroyMixin`) para devolver `409` en vez de un `500` crudo cuando se intenta borrar uno en uso (`on_delete=PROTECT`) — verificado con HTTP real contra `BINANCE`/`BTCUSDT` (ambos en uso).
- **`WorkflowGraphSnapshot`/`WorkflowDeployment`** — de solo lectura (`ListModelMixin`+`RetrieveModelMixin`, sin `POST`/`PATCH`/`DELETE` — verificado `405`), filtrables por `?graph=<id>`.

### Hallazgo grande, no planeado, descubierto durante esta verificación: `strategies.Fractal` estaba modelado en el lugar equivocado

Al ir a agregarle CRUD a `strategies.Fractal` (el fractal institucional/IPDA marcado manualmente), se identificó que el modelo estaba mal ubicado desde su creación en una sesión anterior: conceptualmente es un elemento SMC como `EqualLevel`/`OrderBlock`/`FairValueGap` (todos en la app `indicators`, heredando `IndicatorElementBase` con `source=MANUAL|DETECTED`), no un concepto propio de `strategies`. La app `indicators` YA tenía un modelo similar pero DISTINTO (`SwingFractal`, un patrón técnico automático de 1 barra) — `Fractal` (el institucional, un rango macro high/low/trend) es un elemento diferente, no un duplicado.

**Fix**: se movió el modelo completo a `indicators/models/smc.py::Fractal(IndicatorElementBase)`, con `high/low/trend/start_time/high_index/low_index` — deliberadamente SIN un `*Config` emparejado (a diferencia de sus hermanos), porque no existe ningún algoritmo de detección real para este elemento todavía (es "un problema difícil", palabras del usuario) — se agregará el día que exista `source=DETECTED` real. `Strategy.fractal` ahora apunta a `"indicators.Fractal"` (FK string, mismo criterio de desacople que el resto de las cruces `strategies`↔`workflows`). CRUD nuevo en `indicators/viewsets/fractal.py`, con `source` de solo lectura en el serializer (siempre queda `MANUAL` al crear vía API — `DETECTED` solo lo pondría directo por ORM un futuro proceso de detección real, verificado con HTTP: un intento de `PATCH source=detected` se ignora silenciosamente, queda `manual`).

Se agregó también la entrada `fractal` al catálogo de nodos (`workflows/fixtures/node_definitions.json`, categoría `smart-money`, `is_executable=False` — no hay `NodeExecutor` real, coherente con que no hay detección automática) y se re-corrió `manage.py loaddata node_categories node_definitions` (314 objetos, 295 `NodeDefinition` ahora) para reflejarlo en la BD real, ya que este catálogo se carga a mano (no vía migración automática).

Migración en 3 pasos por el orden de dependencias correcto: `indicators` (crear `Fractal`) → `strategies` (`AlterField Strategy.fractal` al nuevo destino + `DeleteModel` del `Fractal` viejo, en ese orden dentro del mismo archivo) → confirmado `0` filas reales en `strategies_fractal` antes de dropearla (mismo patrón de seguridad de toda la sesión).

### Bug real, preexistente y NO introducido esta sesión, encontrado al verificar los status HTTP: `REST_FRAMEWORK['EXCEPTION_HANDLER']` apuntaba a un módulo que nunca existió

`luarix_rest_api/settings.py` tenía `'EXCEPTION_HANDLER': 'apps.security.exceptions.exception_404_handler'` — `apps` no es un paquete real de este proyecto (la app real es `security`, sin el prefijo `apps.`). Esto significa que **cualquier excepción manejada por DRF** (`Http404`, `ValidationError`, etc., en CUALQUIER endpoint de la API, no solo los nuevos de esta sesión) crasheaba con un `500 ImportError` en vez de devolver el status code correcto (`404`, `400`, etc.) — confirmado en vivo: un `POST` a un `strategy_id` inexistente y una `action` inválida en el endpoint de lifecycle nuevo dieron `500` en vez de `404`/`400`. Probablemente nunca se había notado porque toda la verificación de esta sesión (y aparentemente de las anteriores) probaba caminos exitosos o revisaba errores vía llamadas directas a función, no vía HTTP real con inputs inválidos.

**Fix**: se quitó la línea (comentario explicando por qué), dejando que DRF use su `exception_handler` default — que sí convierte `Http404`/`ValidationError`/etc. en el status code correcto. Verificado en vivo tras el fix: `404` para strategy inexistente, `400` para action inválida, `422` para deploy/resume rechazados por validación de negocio (estos SÍ ya funcionaban antes porque esa vista devuelve una `Response` explícita en vez de levantar una excepción).

---

## Fase 3 (arranque): primer nodo que ejecuta de verdad — Bollinger Bands (sesión actual)

De los 295 `NodeDefinition` del catálogo, solo 21 tenían un `NodeExecutor` real (ver Fase 1c). Se agregó el primero de la categoría `indicators` (`bollinger-bands`, ahora 22 ejecutables) como caso piloto, para establecer el patrón que se repita con el resto.

- **El cálculo ya existía, solo faltaba conectarlo**: `pandas_luarix/indicators/accessor.py::IndicatorsAccessor.bb50(length, std)` ya calcula Bollinger Bands real (usa `pandas_ta_classic` internamente) — no hubo que implementar matemática nueva. Nuevo `workflows/execution/nodes/classic.py::BollingerBandsExecutor` (mismo nombre que `indicators/models/classic.py`, mismo concepto — indicadores clásicos no-SMC), leyendo `period`/`stdDev` de `node.config` (ya definidos en el catálogo) y devolviendo el snapshot de la ÚLTIMA vela (`upper`/`middle`/`lower`/`close`), mismo criterio que `OnCandleExecutor`/`StopLossExecutor` (un valor por pasada, no la serie completa repetida).
- **Ya estaba resuelta por código previo la pregunta de si esto debía persistir en la app `indicators`**: `indicators/models/classic.py::BB50Config` ya documentaba explícitamente *"Sin modelo de elemento: produce una serie densa (un valor por vela), no eventos discretos"* — a diferencia de Swing/OrderBlock/FVG. Se respetó esa decisión: sin tocar `indicators` en esta pasada, solo el mecanismo ya establecido (`NodeExecutionResult` → `NodeExecutionLog`/`context_data`, mismo que los 11 nodos SMC).
- Se extrajeron `_json_safe`/`_records` (antes solo en `smc.py`) a `workflows/execution/nodes/_shared.py` (`json_safe`/`records`) para reusarlos en `classic.py` sin duplicar — `smc.py` ahora importa de ahí, comportamiento idéntico (confirmado por regresión).
- Mismo patrón dual que Fase 1c para `is_executable`: migración de datos (`workflows/migrations/0005_fase3_bollinger_bands_executable.py`) + actualización del fixture JSON, para que un futuro `loaddata` no lo pierda.

### Verificado contra la BD real (backtest real, mismos datos cacheados de sesiones anteriores)

- Grafo real `on-candle` → `bollinger-bands` (+ `swing-high` en paralelo, para regresión SMC) → `context`, corrido con `PaperBacktestRunner` sobre ~110 velas reales de BTCUSDT 4h cacheadas: **91 ejecuciones exitosas** de `bollinger-bands` curadas en `BacktestRun.logs`, con valores reales y coherentes (`upper > middle > lower`, ej. `upper=67449.18 / middle=65438.53 / lower=63427.87`).
- **Fallo gracioso confirmado**: las primeras ~19 velas (menos que `period=20`) hacen que `bb50()` levante `ValueError` (`require_min_rows`) — el motor (`engine.py`, ya existente) lo atrapa, loguea `FAILED` con el mensaje, y sigue con el resto del grafo sin tumbar la corrida — el backtest completo terminó `status=completed` de todos modos.
- `context_data["indicators"]` se llenó correctamente (una entrada por pasada exitosa, con los valores reales) — solo porque el nodo `bollinger-bands` tiene un edge hacia un nodo `context`, mismo comportamiento ya establecido para los buckets de SMC.
- Regresión confirmada: `swing-high` (SMC, ahora usando el helper compartido `_shared.py` en vez de su copia local) siguió funcionando igual — 92 entradas curadas en la misma corrida.
- Toda la data sintética (1 `Strategy`, 1 `WorkflowGraph`, 1 `BacktestRun`, 1 `BrokerAccount` de prueba) se borró al terminar.

### Roadmap natural para continuar (no ejecutado, documentado para la próxima pasada)

`IndicatorsAccessor` ya expone `stochastic_oscillator()` además de `bb50()` — mismo tratamiento (`StochasticOscillatorExecutor` en `classic.py`) sería el siguiente paso más rápido. El resto de los ~27 nodos de `indicators` (EMA, SMA, RSI, MACD, ATR, ADX, etc.) necesitan primero exponer el método correspondiente en `IndicatorsAccessor` (la librería subyacente, `pandas_ta_classic`, ya los calcula — falta el wrapper) antes de poder repetir este mismo patrón de `NodeExecutor`.

---

## Fase 3 (continuación): persistencia real de los 11 elementos SMC detectados en vivo (sesión actual)

Los 11 `NodeExecutor` de `workflows/execution/nodes/smc.py` ya detectaban de verdad (llaman a `pandas_luarix`) pero el resultado se perdía — solo vivía en `NodeExecutionLog` (se borra al terminar cada corrida) y en `WorkflowRun.context_data` (JSON sin estructura ni dedup). Se conectó la app `indicators` (existía diseñada, nunca poblada) para que estos 11 nodos persistan filas reales y consultables — **solo para estrategias en vivo, nunca para backtesting** (pedido explícito del usuario).

### Hallazgo grande antes de implementar: los modelos de `indicators/models/smc.py` mirroreaban el motor EQUIVOCADO

Confirmado leyendo el código fuente real de `pandas_luarix` (no asumido): `Swing`, `StructureEvent`, `OrderBlock`, `LiquiditySweep`, `FairValueGap`, `EqualLevel` fueron diseñados como "mirror de X (`app/tradingview/types.py`)" — el motor LEGACY stateful (Engine B, usado solo por el pipeline/backtester viejo), no `pandas_luarix` (Engine A), que es el que de verdad corre en los `NodeExecutor` de `workflows`. Sus campos no calzaban 1:1 — resuelto campo por campo:

- **`Swing.previous_level`** (requerido, sin default, SIN fuente en Engine A — Engine A no clasifica HH/HL/LH/LL) — se volvió `null=True, blank=True` y se calcula en la capa de persistencia consultando el `Swing` anterior del mismo lado ya persistido (queda `None` para el primer swing de cada lado).
- **`Swing.is_high`** — campo NUEVO (`BooleanField(null=True)`) — discriminador confiable entre swing-high/swing-low en la misma vela; `swing_type` (HH/HL/LH/LL) no sirve para esto porque queda `None` en el caso bootstrap.
- **`LiquiditySweep.swept_level_type`** — tenía un TODO ("confirmar el set exacto de valores") — resuelto leyendo `SMCAccessor.liquidity_sweep()`: el set cerrado real es `{swing_high, swing_low, equal_high, equal_low}`, convertido a `TextChoices`.
- **`StructureEvent.pivot`** (FK a `Swing`) — queda `None` siempre: `SMCAccessor.bos_choch()` no expone `pivot_bar_index`/`pivot_level` en su DataFrame público (se descartan internamente en `_core/trend.py::track_structure_events()`), y no se tocó `pandas_luarix` (librería compartida) para exponerlos — limitación documentada, no resuelta.
- **`StructureEvent.internal`** — siempre `False`: Engine A no distingue estructura "interna" vs "swing" (concepto exclusivo de Engine B).
- **`StructureEvent.broken_price`** — se interpretó como el `close` de la vela de ruptura (el motor no expone el nivel del pivote roto en el DataFrame público) — interpretación defendible del nombre del campo, no un dato inventado.

### Por qué nunca corre en backtesting (verificado, no solo diseñado)

`WorkflowEngine.execute()` es compartido por backtest y por vivo — la persistencia (`workflows/execution/indicator_persistence.py::persist_smc_elements()`) se llama **solo** desde `dispatch_manual`/`dispatch_candle` (mismo patrón exacto que ya usa `curate_and_append_logs()`), nunca desde `runner.py`/`paper_runner.py`. Exclusión estructural, no un `if run_mode`. Verificado con un backtest real completo (mismos datos cacheados de sesiones anteriores): conteos en los 6 modelos + `DetectionRun` idénticos antes/después, 0 filas creadas.

### Deduplicación: por timestamp real, nunca por índice posicional

`pandas_luarix` recalcula TODO el historial en cada pasada (no es incremental) — sin dedup, cada vela nueva re-insertaría todo lo ya visto. Se descartó `bar_index`/`*_index` como clave de identidad (cambia según cómo se reconstruya la ventana, especialmente en vivo) — se usa el timestamp real de cada elemento (`timestamp`/`broken_time`/`left_time`/`first_time`+`second_time` según el tipo) vía `unique_together` + un diff en memoria (`_sync()` en `indicator_persistence.py`: 1 `SELECT` + a lo sumo 1 `bulk_create` + 1 `bulk_update` por handler por pasada, sin importar cuánta historia acumulada haya). Caso especial: `Swing` no usa el `_sync()` genérico — `previous_level`/`swing_type` dependen del swing anterior del MISMO lado, incluyendo swings nuevos dentro de la misma pasada (ej. primera corrida escaneando mucho historial de una vez), así que se procesa en orden cronológico con un cursor en memoria.

### `NodeExecutionResult` ganó un campo `groups` — hallazgo adicional durante la implementación

`EqualHighExecutor`/`EqualLowExecutor` (`smc.py`) aplanaban `list[pd.DataFrame]` (grupos de nivel igual, pares de velas) en una lista de filas sueltas ANTES de devolver `output` — perdiendo qué fila pertenece a qué par, dato imprescindible para reconstruir `EqualLevel.first_index/second_index`. Se agregó `NodeExecutionResult.groups: list[pd.DataFrame] | None` (sin tocar `output`, que sigue igual para quien ya lo consume vía `context_data`) — la persistencia de `EqualLevel` lee `result.groups`, no `result.output`. `ExecutionState` ganó `executed_nodes: dict[int, WorkflowNode]` (necesario para saber `type_id`/`config` al persistir) y `WorkflowEngine.execute()` pasó de no devolver nada a `return state` — cambio no-breaking confirmado (los 3 call sites existentes ya ignoraban el valor de retorno).

### `DetectionRun` — un solo run reusado por `(workflow_run, source_node)`, mismo ciclo de vida que `active_run`

Se crea en la primera pasada (`get_or_create`), queda `RUNNING` mientras el grafo esté LIVE/PAUSED, y se cierra (`SUCCESS` + `finished_at`) en `lifecycle.py::stop()`, mismo momento exacto en que se cierra `active_run` — `pause()` no lo toca, igual que no toca `active_run`.

### Verificado contra Postgres real (grafo LIVE real, ~360 velas reales de BTCUSDT 4h cacheadas, vía `dispatch_candle`)

- Los 6 modelos recibieron filas reales con valores coherentes: `FairValueGap.right_index == left_index + 2` (patrón de 3 velas), `EqualLevel.second_index > first_index`, `OrderBlock.top >= bottom`.
- Repetir la MISMA pasada 3 veces seguidas: cero filas nuevas, cero cambios — dedup confirmado.
- Avanzar la ventana 30 pasadas más: los conteos solo crecieron, nunca decrecieron ni duplicaron lo ya visto.
- Secuencia completa de `Swing.previous_level`/`swing_type` verificada coherente contra los niveles reales (primer swing de cada lado con `previous_level=None`, el resto con `HH`/`LH` según corresponda).
- `DetectionRun`: exactamente uno por `(workflow_run, source_node)` que detectó algo (7 de los 11 nodos SMC probados produjeron datos en esta ventana — `liquidity-sweep` no detectó nada, plausible, patrón específico/raro).
- `stop()`: los 7 `DetectionRun` quedaron `SUCCESS` + `finished_at` seteado.
- Endpoints de lectura (`GET /indicators/{swings,structure-events,order-blocks,liquidity-sweeps,fair-value-gaps,equal-levels}/`) probados por HTTP real: filtro `?strategy_id=`, filtro de campo mutable (`?filled=false`), scoping por owner, `POST` rechazado con `405` (son de solo lectura).
- Backtest real completo tras todos los cambios: **0 filas creadas** en los 6 modelos + `DetectionRun` — exclusión estructural confirmada, no solo diseñada.
- Toda la data sintética de esta verificación (2 `Strategy`, 2 `WorkflowGraph`, 1 `BacktestRun`, 1 `BrokerAccount`, 7 `DetectionRun`, 20 elementos SMC) se borró al terminar.

### Fuera de alcance, documentado explícitamente

- Tocar `pandas_luarix` para exponer `pivot_bar_index`/`pivot_level` en `bos_choch()` (permitiría enlazar `StructureEvent.pivot` a un `Swing` real) — limitación conocida, no resuelta.
- CRUD manual de estos 6 tipos (a diferencia de `Fractal`) — son de solo lectura, se crean solo por detección automática.
- `method=pct_range` en equal-levels (grupos de 3+ filas) — los `NodeExecutor` no lo exponen hoy vía `node.config`; el modelo actual (`first_index`/`second_index`, solo par) no lo soportaría sin pérdida de datos.

---

## Fase 4 (final del roadmap): trazabilidad Trade → señal (sesión actual)

`Trade` (backtesting) era puramente numérico — sin forma de saber qué nodo del grafo lo originó ni qué contexto/indicadores había detectados en ese momento. `TradeEvent` (SIGNAL/FILL/TP_HIT/SL_HIT) ya estaba modelado desde antes pero nunca se instanciaba.

### Mismo patrón de hallazgo que en Fase 3: el docstring de `TradeEvent` apuntaba al motor equivocado

`TradeEvent` decía "mirror de los eventos que hoy escribe TradeJournal (`trade_journal.py`)" — ese `trade_journal.py` (raíz del repo) es del pipeline LEGACY (`contexts.py`/`pipeline.py`, Engine B), no tiene relación con `backtesting/execution/paper_runner.py` (el runner Django real que efectivamente genera `Trade` hoy). Se conectó `TradeEvent` contra el runner real — mismo criterio que ya se aplicó con `pandas_luarix` vs. `app/tradingview` en Fase 3, sin necesitar tocar el framework raíz (`BacktestStats`) para nada.

### Diseño: tracking paralelo en `PaperBacktestRunner`, sin tocar `BacktestStats`

`BacktestStats.trades` (framework raíz, no se toca) no trackea "qué nodo" ni "lista de eventos". Se agregó tracking propio en memoria:
- **`entry_node`**: `WorkflowEngine.execute()` ya devuelve `ExecutionState` (desde Fase 3) — el loop de `run()` ahora captura ese retorno y escanea `state.node_outputs` buscando cualquier output tipo `{"exchange_order_id": ..., "quantity": ...}` (lo que YA devuelven `MarketOrderExecutor`/`LimitOrderExecutor`, genérico, sin hardcodear type_id), mapeando `exchange_order_id → WorkflowNode` antes de que el execution report correspondiente llegue.
- **`TradeEvent`**: los 4 puntos donde `_on_execution_report()` ya llama `stats.on_signal/on_fill/on_tp_hit/on_sl_hit` ahora también bufferan `{event_type, timestamp, payload}` en memoria (keyado por `entry_id`, el mismo key que usa `stats.trades`).
- **`signal_snapshot`**: en el punto `on_signal`, se captura `dict(self.workflow_run.context_data)` — copia superficial del contexto en ese instante.
- **`_persist_results()`**: al `update_or_create` cada `Trade` (como ya hacía), se agregan `entry_node`/`signal_snapshot` a `defaults`, y justo después se hace `bulk_create` de los `TradeEvent` bufereados para ese `entry_id`.

Sin necesidad de exclusión estructural esta vez (a diferencia de Fase 3): `Trade` solo existe para backtesting (única FK del modelo), no hay otro camino que lo toque.

### Verificado contra Postgres real

- **Nota de infraestructura, no un bug de código**: la primera corrida de verificación (ventana de 90 días) murió a mitad de camino con `psycopg.OperationalError: consuming input failed: server closed the connection unexpectedly` — la conexión a Postgres remoto (Supabase) se cerró en medio de una corrida larga (varios cientos de velas, con logging in-process constante). El estado quedó limpio (`Trade` se persiste recién al final de `run()`, así que no había filas parciales — solo un `BacktestRun` en `status=running` colgado, limpiado a mano). Reintentado con una ventana más corta (35 días) sin problema — no se investigó más a fondo (probablemente un límite de vida de conexión del pooler, no algo del código de esta sesión).
- Backtest real (grafo con `swing-high` → `context` para contenido real de `signal_snapshot`, señal de prueba espaciada cada 30 velas para lograr varios trades independientes sin pyramiding): 4 trades reales, 1 cerrado por TP y 3 por SL.
- `Trade.entry_node`: los 4 trades apuntan correctamente al `WorkflowNode` real (`market-order`) que los originó.
- `Trade.signal_snapshot`: contenido real en los 4 (`{"swings": [...], "_oco_entry_map": {...}}` — el bucket `swings` real más una clave interna de bookkeeping ya conocida de `context_data`, sin namespacing entre claves reservadas y buckets de detector — limitación ya documentada en Fase 3, no introducida acá).
- `TradeEvent`: cada trade con su secuencia completa y coherente (`SIGNAL`+`FILL`+`TP_HIT` o `SIGNAL`+`FILL`+`SL_HIT`), payloads reales (ej. `fill_price`/`tp_price`/`sl_price` coherentes con los fills reales del broker paper).
- Endpoints de lectura (`GET /backtesting/trades/?backtest_run=<id>`, `GET /backtesting/trade-events/?trade=<id>`) probados por HTTP real — antes NO existía ningún endpoint para `Trade`/`TradeEvent` (`BacktestRunSerializer` no los anidaba). `POST` rechazado con `405` (solo lectura) en ambos.
- Toda la data sintética (1 `Strategy`, 1 `WorkflowGraph`, 1 `BacktestRun`, 4 `Trade`, 12 `TradeEvent`, 1 `BrokerAccount`) se borró al terminar.

### Con esto queda cerrado el roadmap completo de la auditoría de modelado (Fase 0 → Fase 4).

---

## Fase 5: corte de pre-producción — seguridad, Swagger, nodos genéricos (EMA/RSI/riesgo) (sesión actual)

Objetivo: preparar `luarix_rest_api` para operar con 2 usuarios reales del equipo (sin registro público), reemplazando poco a poco al servicio FastAPI. Plan completo en el historial de conversación; acá solo lo que hace falta recordar para no re-investigar.

### Seguridad — todo lo que era hardcoded/inerte, ahora env-driven

- `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` ahora leen de env (`DJANGO_SECRET_KEY`/`DJANGO_DEBUG`/`DJANGO_ALLOWED_HOSTS`/`DJANGO_CSRF_TRUSTED_ORIGINS`), con el valor hardcoded anterior como fallback SOLO para dev.
- **CORS estaba completamente inerte**: `corsheaders` en `INSTALLED_APPS` y configurado (`CORS_ALLOW_CREDENTIALS`, `CORS_ORIGIN_ALLOW_ALL`, `CORS_ALLOW_HEADERS`), pero `corsheaders.middleware.CorsMiddleware` **nunca estuvo en `MIDDLEWARE`** — ningún header CORS se agregaba nunca a ninguna respuesta. Se agregó el middleware (antes de `CommonMiddleware`) y se reemplazó `CORS_ORIGIN_ALLOW_ALL` (nombre viejo/inerte en versiones actuales de `django-cors-headers`) por `CORS_ALLOWED_ORIGINS` env-driven. Verificado con un request HTTP real (`Origin: http://localhost:3000` → `Access-Control-Allow-Origin` presente).
- JWT: `SIMPLE_JWT["SIGNING_KEY"]` reusaba `SECRET_KEY` — separado en `JWT_SIGNING_KEY` (env, fallback a `SECRET_KEY` solo en dev). `ACCESS_TOKEN_LIFETIME` bajado de 2 días a 1 hora (credenciales de broker reales de por medio).
- **No existía ningún rate limiting**, ni siquiera en el endpoint de token (`/auth/token/` aceptaba fuerza bruta ilimitada). Se agregó `DEFAULT_THROTTLE_RATES = {"auth": "10/min"}` + `ThrottledTokenObtainPairView`/`ThrottledTokenRefreshView` (`security/viewsets/token.py`, subclases de las vistas de SimpleJWT con `throttle_scope="auth"`), reemplazando las vistas crudas en `urls.py`. Verificado: 13 intentos seguidos → `429` a partir del 11º.
- **Logout no existía** a pesar de que `rest_framework_simplejwt.token_blacklist` ya estaba instalado: `POST /api/v1/auth/logout/` (`LogoutView`, blacklistea el refresh). Verificado con login real → logout → reintentar el mismo refresh en `/auth/token/refresh/` → `401` (blacklisteado de verdad).

### `EncryptedCharField` — cifrado en reposo de credenciales de broker

`BrokerAccount.api_key`/`api_secret`/`api_passphrase` tenían un `TODO: cifrar` sin resolver desde Fase 1. Se descartó `django-fernet-fields`/`django-cryptography` (compatibilidad incierta contra Django 6.0.6, muy reciente) a favor de un campo propio (`core/fields.py`) sobre `cryptography.fernet.Fernet` (ya instalado, usado por otra dependencia). `from_db_value` hace `try/except InvalidToken: return value` — necesario para no romper filas preexistentes en texto plano antes de la migración de re-cifrado.

- `FIELD_ENCRYPTION_KEY` (settings) — nueva env var. Con `DEBUG=False` y sin esta variable seteada, `settings.py` **revienta al arrancar** (`RuntimeError` explícito) — a propósito, para que sea imposible desplegar en producción sin haberla generado.
- Migración en 2 pasos (`brokers/migrations/0005`/`0006`): `AlterField` a `EncryptedCharField` primero, luego un `RunPython` que re-guarda cada `BrokerAccount` existente (fuerza el cifrado real de lo que ya estaba en texto plano). Campos subidos a `max_length=512` (el texto cifrado de Fernet es bastante más largo que la credencial original — para un API key de ~64 caracteres, el ciphertext base64 ronda 180-190 caracteres).
- **Verificado contra Postgres real**: `SELECT api_key FROM brokers_brokeraccount` crudo (vía `connection.cursor()`) devuelve un token Fernet (`gAAAAAB...`), no el texto plano; releído vía ORM (`BrokerAccount.objects.get(...).api_key`) recupera el valor original correcto.

### Dev-user + cuenta Binance real: ya no se crean fuera de `DEBUG`, pero NO se borran en BDs existentes (solo se desactivan)

`security/migrations/0003_create_dev_user.py` y `brokers/migrations/0003_seed_system_binance_account.py` corrían **siempre**, incluso contra una BD de producción — la segunda siembra una `BrokerAccount` con credenciales reales de Binance mainnet (`TEST_BINANCE_API_KEY`/`SECRET`). Se agregó `if not settings.DEBUG: return` al inicio de ambas.

**Decisión de diseño importante**: para limpiar una BD de dev que se promueva a real, la tentación obvia es una migración que *borre* el usuario dev y su cuenta si `DEBUG=False`. Se descartó — `BrokerAccount.owner`/`Strategy.owner` (`OwnedModel.owner`) es `on_delete=CASCADE`, así que borrar al usuario `luarix-dev` arrastraría TODAS las `Strategy`/`BacktestRun`/`BrokerAccount` que se hayan creado bajo ese usuario durante todo el desarrollo (Fase 0 a Fase 5 de esta sesión, por ejemplo). En vez de eso, dos migraciones nuevas (`security/0004`, `brokers/0007`) solo ponen `is_active=False` cuando `DEBUG=False` — nunca `DELETE`. Verificado simulando `DEBUG=False` dentro de una transacción con rollback forzado (sin tocar la BD real): usuario/cuenta fresh no se crean, usuario/cuenta existentes se desactivan; tras el rollback, todo sigue como estaba.

**Alta de los 2 usuarios reales del equipo**: no requiere código nuevo. `manage.py createsuperuser` (o `User.objects.create_user(...)` vía shell) por persona; cada uno crea su propia `BrokerAccount` con FK a `Broker` (Binance/etc.) + sus propias API keys reales (quedan cifradas automáticamente por `EncryptedCharField`).

### Swagger/OpenAPI (`drf-spectacular`)

Elegido sobre `drf-yasg` por integración nativa más activa con DRF. Rutas nuevas: `/api/schema/` (JSON), `/api/docs/` (Swagger UI), `/api/redoc/` (Redoc) — las 3 verificadas con `200` real. `drf-spectacular==0.30.0` (0.30.1 no existe en PyPI, la versión más reciente disponible es 0.30.0) + `uritemplate==4.2.0` (dependencia), agregados a `requirements.txt` con cuidado (el archivo está en **UTF-16 little-endian con terminadores CRLF** — se editó con un script Python que abre/escribe con `encoding="utf-16-le"`, nunca con el `Write` tool genérico, que lo corrompería a UTF-8).

**Warnings preexistentes en la generación del schema, no introducidos en esta sesión** (no se tocaron, fuera de alcance de este pase): `CandleViewSet` (falta `serializer_class`), `NodeCatalogView`/`WorkflowGraphView`/`WorkflowGraphLifecycleView` (APIViews sin serializer inferible — drf-spectacular no puede adivinar el schema de request/response). No rompen nada (`/api/schema/` responde 200 igual, son solo advertencias en el log), pero valdría la pena limpiarlas en una pasada futura si el equipo quiere el schema 100% completo. `LogoutView` tenía el mismo warning — sí se corrigió acá (`security/serializers/token.py::LogoutSerializer` + `@extend_schema`), porque es código nuevo de esta misma pasada.

### El catálogo de nodos YA tenía definiciones concretas para varios de estos nodos — distintas de lo que se había planeado a ciegas

Antes de escribir los executors se revisó `workflows/fixtures/node_definitions.json` (295 `NodeDefinition`, ya poblado en fases anteriores) y varias definiciones NO coincidían con el diseño planeado inicialmente — se adaptaron los executors al catálogo real, no al revés:

- **`stochastic`**: params son `kPeriod`/`dPeriod`, no `period`/`dPeriod`.
- **`ema`**: tiene un param `source` (close/open/high/low) que no estaba contemplado — se agregó soporte real (`IndicatorsAccessor.ema(length, source)`).
- **`entry-condition`**: el catálogo YA lo definía con 3 inputs fijos (`a`/`b`/`c`, vía `WorkflowEdge.target_port`) + un param `logic` (`and`/`or`) — es un combinador booleano de hasta 3 señales, **no** un nodo de comparación numérica contra un umbral como se había bocetado al planear. Se implementó conforme al catálogo real (más genérico y ya consistente con `weighted-score`, que comparte la misma forma de 3 inputs).
- **`weighted-score`**: también 3 inputs `a`/`b`/`c`, pero **sin ningún param declarado** (`params: []`) — no hay campo de UI para los pesos todavía. Se implementó leyendo `node.config["weights"]` (dict puerto→peso, ej. `{"a": 2, "b": 1}`) como config "avanzada" sin UI dedicada aún — documentado en el docstring del executor. Si el equipo quiere pesos editables desde el frontend, hace falta agregar ese param al catálogo (`params: [{"key": "aWeight", ...}, ...]`) en una pasada futura.
- **`max-trades`**: param es `value` (no `max_positions`).

Como consecuencia, un futuro "gate de umbral numérico" (`score >= X`) que sí compare `weighted-score` contra un número **no existe todavía como nodo** — `entry-condition` es puramente booleano AND/OR. Si Luis's-strategy-like scoring necesita eso literal, hace falta un nodo nuevo (`threshold-gate` o similar), no contemplado en el catálogo actual.

### `_upstream_triggered` movido a `_shared.py`

Antes vivía privado en `execution.py` (usado por `market-order`/`limit-order`/`stop-loss`/`take-profit`). Se movió a `workflows/execution/nodes/_shared.py` para que `risk.py` (`MaxOpenPositionsExecutor`) lo reuse sin duplicar ni crear un import circular (`_shared.py` ya no depende de nada en `nodes/`, solo de `types.py`).

### `_open_positions_count` en `context_data` — solo para backtesting

`PaperBacktestRunner._on_execution_report()` ahora incrementa `context_data["_open_positions_count"]` en cada fill de ENTRADA y lo decrementa en cada `TP_HIT`/`SL_HIT` — es lo que lee `MaxOpenPositionsExecutor`. **No existe equivalente en vivo** (las órdenes en vivo no están conectadas a un broker real todavía, limitación ya documentada en fases anteriores) — el nodo `max-trades` hoy solo funciona en backtesting.

### Nodo de riesgo debe ir EN SERIE, no en paralelo (ya documentado en el docstring del executor)

`_upstream_triggered` dispara con OR (cualquier upstream truthy alcanza), así que `señal` y `max-trades` conectados como dos entradas PARALELAS a `market-order` no bloquearían nada — la señal sola bastaría. El grafo correcto es `señal → max-trades → market-order` (y lo mismo hacia `stop-loss`/`take-profit`), para que el único upstream que ve cada nodo de ejecución sea el output ya combinado (`triggered AND cupo disponible`) de `max-trades`.

### Deploy artifacts para `luarix_rest_api` — el `.env` real vive en la RAÍZ del repo, no en `luarix_rest_api/`

`python-dotenv`'s `load_dotenv()` (sin path, llamado en `settings.py`) busca `.env` hacia ARRIBA desde el archivo que lo invoca — desde `luarix_rest_api/luarix_rest_api/settings.py` sube hasta encontrar `nexora-trading-framework/.env` (confirmado: ese archivo ya existe ahí, con `LUARIX_BACKEND_SERVER_*`/`TEST_BINANCE_API_KEY`/etc. reales). Por eso `.env.example` se creó en la **raíz del repo** (`nexora-trading-framework/.env.example`), no dentro de `luarix_rest_api/` — ahí es donde realmente hay que copiarlo. Documenta TODAS las variables nuevas de esta sesión (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `FIELD_ENCRYPTION_KEY`, `JWT_SIGNING_KEY`, `CORS_ALLOWED_ORIGINS`) más las ya existentes.

Artefactos nuevos en `deploy/` (mismo patrón que los ya existentes de FastAPI, pero apuntando a Django/puerto 8001): `nexora-django.service` (Daphne, ASGI — necesario por Channels/WebSocket, a diferencia de FastAPI que corre con uvicorn plano), `nexora-django-celery-worker.service`, `nexora-django-celery-beat.service` (requieren Redis real, todavía no instalado en este entorno de dev), `nginx-nexora-django.conf` (con bloque `location /ws/` para upgrade de conexión WebSocket, que el conf de FastAPI no necesita). **El servicio FastAPI no se tocó ni se borró** — sigue corriendo en paralelo hasta que el usuario confirme paridad de features y lo retire a mano.

### Verificado contra Postgres real

- Migraciones (`brokers` x4 nuevas, `security` x2 nuevas, `workflows` x1 nueva) aplican limpio; `manage.py check`/`makemigrations --check` limpios; `check_node_catalog_consistency` confirma 28/28 `NodeExecutor` registrados ↔ `is_executable=True` (antes 22).
- Cifrado de `BrokerAccount` (ver arriba), logout+blacklist, throttling `429`, CORS real, Swagger x3 rutas: todo verificado por HTTP real (Django test client contra la BD real, no mocks) — ver detalle en cada sección arriba.
- `ema`/`rsi`/`stochastic`: grafo real (`on-candle` 4h → 3 nodos en paralelo) contra ~140 velas reales de BTCUSDT — valores coherentes (`ema≈59566` cerca del `close=60107`, `rsi=53.28` en rango, `stochastic slow_k=77.4/fast_d=61.2` en rango). Leído directo de `state.node_outputs` de un solo `engine.execute()` — **no** de `NodeExecutionLog` post-run, porque `PaperBacktestRunner._build_and_save_logs()` cura y BORRA esas filas al terminar la corrida (mismo mecanismo de Fase 2/3, ver `log_utils.py`) — cualquier test futuro que quiera inspeccionar outputs de nodos debe leerlos DURANTE la corrida (`state.node_outputs`) o antes de que el run termine, no después.
- `weighted-score`(pesos `{a:2,b:1,c:5}`, señales `True,True,False`) → `3` (correcto, ignora el peso de `c` por ser `False`); `entry-condition` AND(`True,True,False`)→`False`, OR(mismo)→`True`. Verificado con `WorkflowEngine.execute()` directo (nodos/edges reales en Postgres, sin mocks).
- `max-trades(value=2)`: grafo real `señal periódica (cada 10 velas) → max-trades → {market-order, stop-loss, take-profit}` corrido contra ~140 velas reales de BTCUSDT (35 días). 9 `Trade` creados (8 con fill real), barrido de intervalos `[fill_time, exit_time]` confirma que el máximo de posiciones concurrentes observado fue **2**, nunca 3 — el gate funciona.
  - **Gotcha durante esta verificación** (no un bug, un recordatorio del comportamiento ya documentado): una señal que dispara en **cada** vela (sin espaciado) fuerza tanto pyramiding que el balance del broker paper se va muy negativo y dispara el bug ya conocido/fuera de alcance de `avg_monthly_return` (`log` de capital negativo → número complejo, `TypeError` al guardar en un `FloatField`). Se evita con una señal espaciada (cada 10 velas, mismo patrón que Fase 4) — no es algo a arreglar en esta pasada, solo un recordatorio de cómo escribir señales de prueba seguras para futuras verificaciones.
- Toda la data sintética (múltiples `Strategy`/`BacktestRun`/`Trade`/`BrokerAccount`/`NodeDefinition`/`NodeCategory` de prueba, más el usuario HTTP de prueba `fase5-http-test`) se borró al terminar.

### Pendiente para una pasada futura (no bloqueante para este corte)

- Limpiar los warnings preexistentes de `drf-spectacular` en `CandleViewSet`/`NodeCatalogView`/`WorkflowGraphView`/`WorkflowGraphLifecycleView` (agregar `serializer_class` o `@extend_schema` manual) para un schema 100% limpio.
- Agregar params de peso editables (`aWeight`/`bWeight`/`cWeight`) al catálogo de `weighted-score` si el frontend necesita una UI para configurarlos, en vez de `node.config["weights"]` crudo.
- Un nodo de comparación numérica contra umbral (`score >= X`) si alguna estrategia lo necesita literal — `entry-condition` no lo cubre (es booleano AND/OR, no numérico).
- Instalar Redis real y validar los `deploy/nexora-django-celery-*.service` contra un servidor real (no se pudo en este entorno de dev).
- Reconexión del frontend (fuera de alcance explícito de esta pasada) — Swagger (`/api/docs/`) ya es el contrato disponible para esa pasada futura.

---

## Fase 6: migrar el frontend fuera de `fastapi_server/` — indicadores/SMC on-demand (sesión actual)

Objetivo: el usuario preguntó si ya se podía borrar `fastapi_server`. Auditoría (4 agentes en paralelo, 2 rondas) encontró que el chart de mercado del frontend (`luarix-web-client`) todavía dependía de FastAPI para 3 cosas: catálogos estáticos, cómputo on-demand de indicadores/SMC/análisis sobre un rango de fechas arbitrario, y velas de brokers no-Binance. Se resolvieron las primeras dos (las que realmente bloqueaban el chart); la tercera queda documentada como gap real, no resuelto.

### Hallazgo: hay DOS servicios FastAPI, no uno

`fastapi_server/` (indicadores/SMC/catálogos/velas, puerto 8000) y **`backtesting_api/`** (`backtesting_api/main.py`, mismo puerto 8000 por defecto) — un servicio aparte, no auditado en fases anteriores, que corre una estrategia legacy completa (`IPDAStrategy`, root `strategies.py`/`contexts.py`/`backtester.py::LocalBacktester`) sobre un motor SMC distinto (`app/tradingview/smc_indicator.py`, no `pandas_luarix`). Nada de esa lógica (kill-switch de Fractal, high/low anual-semestral, entrada partida en tramos) está replicado como grafo de nodos en Django — es un gap separado y mayor, pendiente de decisión (¿se replica, o se borra si ya no se usa?), no resuelto en esta pasada.

### Backend — `indicators/compute/` (nuevo subpaquete): cómputo on-demand, separado de los elementos persistidos

Namespace nuevo `api/v1/indicators/compute/<recurso>/` (GET, no POST — cómputo sin efectos secundarios es más idiomático en REST/DRF que el POST que usaba FastAPI), deliberadamente separado de `indicators/<recurso>/` (`SMCElementReadOnlyViewSet`, que solo lee lo que un `WorkflowRun` real ya persistió — mezclar ambos conceptos en el mismo viewset habría sido incorrecto). 9 endpoints (`swings`, `bos-choch`, `order-blocks`, `liquidity-sweeps`, `fair-value-gaps`, `fractals`, `bb50`, `stochastic`, `divergence`) + 3 de catálogo (`catalog/{indicator,smc,analysis}/`), todos requieren JWT real + una `BrokerAccount` propia (`broker_account`, mismo patrón que `CandleViewSet`/`BacktestRun` — no un concepto nuevo).

**Se portó 1:1 el contrato de respuesta de FastAPI** (`fastapi_server/services/visual_elements.py` → `indicators/compute/elements.py`, mismo `_marker`/`_line`/`_box`/`_multiline_element`, mismo `id` sintético `f"{indicator_id}:{sub_kind}:{anchor}"`) — no había ninguna razón de diseño para inventar un shape nuevo, y así el frontend no necesitó cambiar sus tipos TS (`lib/luarix-api/types.ts` no se tocó).

**Gotcha de diseño no obvio, ya solucionado**: los accessors de `pandas_luarix` (`df.smc.*`/`df.indicators.*`/`df.analysis.*`) leen el tiempo real del **índice** del DataFrame (`for time, row in df.iterrows()`, `row.name`), no de una columna — confirmado comparando contra `fastapi_server/services/market_data_service.py::fetch_ohlcv`, que hace `df.set_index("date")` antes de llamar cualquier accessor. `marketdata.services.get_history()` (lo que ya usan los `NodeExecutor` de Django) trae `"date"` como **columna**, no como índice — así que cada vista de `indicators/compute/views.py::BaseIndicatorComputeView` hace su propio `df = df.set_index("date")` después de `get_history()`. Sin este paso, `fractal()` en particular habría devuelto `confirm_time` como una posición entera en vez de un timestamp real (es el único accessor que lee `df.index` explícitamente para producir una columna de salida) — los demás (`bos_choch`, `order_blocks`, etc.) simplemente habrían heredado un índice sin sentido en vez de fallar ruidosamente, un bug silencioso más difícil de detectar si no se hubiera revisado el código fuente de FastAPI con cuidado antes de escribir el puerto.

**Catálogo**: se portaron solo 9 de las 16 entradas originales de `fastapi_server/catalog/indicators.py` (las que el frontend realmente consume hoy — `swings`, `bos_choch`, `order_blocks` combinados, sin las variantes atómicas `swing_high`/`swing_low`/`bullish_order_block`/`bearish_order_block` ni `equal_high`/`equal_low`/`equal_high_low`, que el frontend no llamaba). Si se necesitan más adelante, agregarlas es mecánico (mismo patrón, mismos accessors ya expuestos por `pandas_luarix`).

### Bug real preexistente encontrado y arreglado (no introducido hoy): `ensure_coverage()` truena con rangos de fecha mixtos naive/aware

Al probar el chart en un navegador real, `GET /api/v1/marketdata/candles/` (usado por `useCachedCandles`, ya conectado a Django desde antes de esta sesión) devolvía **500** siempre que el frontend pedía el rango por defecto (`start_date=2009-01-01T00:00:00` sin offset — naive — hasta `end_date=<ahora>Z` — aware). `marketdata/services.py::ensure_coverage()` llamaba `pd.date_range(start=start, end=end, freq=freq)` sin normalizar — pandas no puede inferir una sola zona horaria cuando un extremo es naive y el otro no (`TypeError: Start and end cannot both be tz-aware with different timezones`). Esto NO lo introdujo el fix de multi-broker de esta sesión (el `pd.date_range` que falla está ANTES de la rama que yo edité) — es un bug preexistente que nunca se había disparado en un flujo real de principio a fin hasta esta verificación en navegador. Fix: nuevo helper `_aware()` en `marketdata/services.py` que normaliza cualquier `datetime` naive a UTC-aware (vía `django.utils.timezone.make_aware`) antes de usarlo, aplicado al inicio de `ensure_coverage()` y `get_history()`.

### `ensure_coverage()` — fix de multi-broker (bug real, no solo "falta soporte")

Instanciaba **siempre** `BinanceBroker` sin mirar `broker_account.broker_id` — una `BrokerAccount` de Bitunix habría traído datos de Binance por error si se usara para completar huecos. Se cambió a branchear por `broker_account.broker_id` (`BinanceBroker`/`BitunixBroker`, instanciados directo con las credenciales de la cuenta — **no** vía `app/brokers/factory.py::BrokerFactory`, que está diseñado para credenciales globales de entorno, no por-cuenta, y habría ignorado las credenciales reales del usuario). **Limitación real descubierta, no resuelta**: `BitunixMarketDataProvider.get_historical_candles()` (`app/brokers/market_data/bitunix.py`) **ignora `start`/`end`** — solo devuelve las últimas N velas (`get_last_candles`), no un rango histórico real. El fix de `ensure_coverage` hace que Bitunix ya no traiga datos de Binance por error, pero la promesa de "backfill de cualquier rango" sigue sin cumplirse realmente para Bitunix — arreglar eso es un cambio aparte en la librería de mercado, no en Django.

### Frontend — `luarix-web-client` (repo hermano)

- Nuevo `lib/luarix-workflow-api/indicators.ts` (cliente autenticado, mismo patrón `authedJson` que ya usa `getCachedCandles`) + `hooks/useIndicatorCatalogs.ts` (hooks de catálogo). `lib/luarix-api/indicator-series.ts`/`structure-shapes.ts`/`market-chart-workspace.tsx` repuntados a Django; se agregó `brokerAccountId` (resuelto vía `useBinanceBrokerAccount()`, ya existente) a `IndicatorSeriesContext`/`StructureShapesContext`.
- **Limpieza de código muerto**: se borraron de `lib/luarix-api/client.ts`/`types.ts`/`structure-shapes.ts` las 7 funciones/tipos que ya no tenían endpoint Django (`getSwingHigh`, `getSwingLow`, `getEqualHigh`, `getEqualLow`, `getEqualHighLow`, `getBullishOrderBlock`, `getBearishOrderBlock`, sus tipos de parámetros, y la función `orderBlockToShapes` que quedó huérfana) — mataría código FastAPI residual sin uso real, en línea con el objetivo del usuario de limpiar lo innecesario.
- `getProviders`/`getIntervals` (picker de broker/símbolo/timeframe del chart) **NO se portaron** — `fastapi_server/catalog/providers.py` carga datos reales de todos los símbolos/intervalos de Binance (`load_binance_data()`, no una lista estática chica como el catálogo de indicadores) — portar esto es un trabajo aparte, no trivial, fuera de esta pasada.
- Velas de brokers no-Binance (`getCandles`, `POST /brokers/candles` de FastAPI) tampoco se migraron — dado que Bitunix real ni siquiera soporta backfill por rango (ver arriba), migrar ese endpoint no resolvería nada todavía.

### Verificado extremo a extremo (Postgres real + navegador real, Playwright con Chromium, sin mocks)

- Backend: los 9 endpoints de cómputo + 3 catálogos probados vía Django test client contra BTCUSDT real (Postgres) — valores/timestamps coherentes.
- **Navegador real** (login real vía el gate de la app + JWT real contra `luarix-dev`, `/markets/chart`, panel "Indicators & SMC"): se agregaron 7 indicadores por doble-click real (Swings, Bollinger Bands, BOS/CHoCH, Order Blocks, Stochastic Oscillator, Fair Value Gaps, Fractal) — los 7 dispararon requests reales a `:8001/api/v1/indicators/compute/...` (confirmado `200` con payloads reales en el log de Django) y **se dibujaron correctamente en el chart** (marcadores de swing, bandas de Bollinger, cajas de order blocks/FVG/fractal, panel de Stochastic) — capturas de pantalla confirmadas visualmente.
- `getProviders`/`getIntervals` confirmados siguiendo apuntando a `:8000` (FastAPI) — **`fastapi_server` sigue siendo necesario**, no se puede borrar todavía por esto solo (aparte del gap de `backtesting_api`/IPDA ya mencionado).
- `npx tsc --noEmit` y `eslint` limpios sobre todo el frontend tras los cambios.

### Veredicto final: ¿se puede borrar FastAPI ya?

**Todavía no.** Quedan 2 bloqueadores reales, independientes entre sí:
1. `getProviders`/`getIntervals` (picker de broker/símbolo/timeframe) siguen en `fastapi_server` — no portado en esta pasada (dataset de símbolos real de Binance, no trivial).
2. `backtesting_api/` (estrategia IPDA) — servicio completamente aparte, con lógica no replicada en Django, decisión pendiente (replicar vs. borrar si ya no se usa).

Lo que SÍ quedó resuelto: el catálogo y el cómputo on-demand de indicadores/SMC/análisis (el uso más pesado y frecuente de `fastapi_server` en el chart) — verificado en vivo, funcionando end-to-end.

---

## Fase 7: catálogo Broker↔Instrument (M2M) + réplica de la estrategia IPDA de Luis como grafo de nodos (sesión actual)

Cierra los 2 bloqueadores documentados al final de Fase 6. Bloqueador #1 (`getProviders`/`getIntervals`) se resuelve con el catálogo M2M. Bloqueador #2 (`backtesting_api`/IPDA) se resuelve replicando el **núcleo real** de la estrategia como grafo de nodos — decisión de alcance confirmada con el usuario, ver más abajo.

### Parte 1 — Catálogo Broker↔Instrument

`Broker.instruments = ManyToManyField("core.Instrument", related_name="brokers", blank=True)`, poblado desde el mismo JSON estático que ya usaba FastAPI (`fastapi_server/utils/data/binance.json`, 1000 símbolos) vía migración de datos (`brokers/migrations/0009_fase7_seed_binance_instruments.py`). Nuevo `GET /api/v1/brokers/providers/` / `GET /api/v1/brokers/intervals/` (`brokers/viewsets/catalog.py`), mismo shape que `ProviderOut`/`IntervalOut` de FastAPI — el frontend no necesitó cambiar tipos, solo repuntar `lib/luarix-workflow-api/client.ts::getProviderCatalog/getIntervalCatalog` a Django.

**Gotcha de URL routing (real, no hipotético)**: `brokers/providers/` quedaba enmascarado por la ruta de detalle auto-generada del `DefaultRouter` (`brokers/<pk>/`, interpretando `"providers"` como un pk). Fix: los `path()` explícitos deben ir ANTES de `router.urls` en `urlpatterns` — cualquier endpoint literal nuevo bajo un prefijo con `ModelViewSet` registrado debe respetar este orden.

Con esto, **bloqueador #1 de Fase 6 cerrado**: `getProviders`/`getIntervals` ya no dependen de `fastapi_server`.

### Parte 2 — Auditoría: ni el propio Python legacy implementa toda la doc de Luis

Antes de replicar nada se auditó `backtesting_api/` (`strategies.py`/`contexts.py`/`backtester.py`, motor SMC en `app/tradingview/smc_indicator.py`) contra `docs/Estrategia Luis.md`. Hallazgo clave: **la brecha no es solo Pine-vs-Python (como en Fase 6), es Python-vs-su-propia-doc**:
- Solo se crea **1 de los 3 tramos** — `entry_40`/`entry_last_30` están comentados en `strategy_conditions.py:81-82`, nunca se completó.
- El Stop Loss usa un placeholder hardcodeado (`structure = 10`, comentario `# Hardcode por ahora`) en vez de la fórmula ATR real de la doc.
- El Oscilador de Volumen, las entradas "EMA de BB50", y el mapa institucional mensual **no existen en ningún lado** (ni Pine, ni Python) — no son features regresadas, son features que nunca se construyeron.

**Decisión de alcance confirmada con el usuario** (`AskUserQuestion`, respuesta: "Núcleo real + fixes de bugs conocidos"): replicar 3 tranches reales (30/40/30), cancelar-hermanas-al-cierre + reset, kill-switch de Fractal persistente, SL/TP dinámico con fórmula ATR real, estructura diaria/anual/semestral. **Explícitamente fuera de alcance** (documentado, no construido): Oscilador de Volumen, entradas "EMA de BB50", mapa institucional mensual, tramos graduados por banda de score.

### Nodos nuevos / patrones de ejecución añadidos al motor de grafos

- **`resolve_df(node, state, default_timeframe=None)`** (`workflows/execution/nodes/_shared.py`): permite que CUALQUIER nodo lea un timeframe distinto al de su trigger (vía `node.config["timeframe"]`), llamando `marketdata.services.get_history()` directo — el patrón "multi-timeframe ya posible hoy" que quedó documentado como pendiente en Fase 5, implementado por primera vez de verdad. Cachea por `(symbol, timeframe, día)` en un atributo Python NO persistido de `state.run` (`_htf_df_cache`) — válido porque `PaperBacktestRunner` reutiliza el mismo objeto `WorkflowRun` en todas las pasadas de un backtest, así que sobrevive entre ticks sin necesitar ser serializable a JSON. Aplicado a `equal-high`/`equal-low`/`bullish-ob`/`bearish-ob`/`bollinger-bands`/swings y a los indicadores clásicos.
- **`upstream_output_by_type(node, state, type_ids)`** / **`latest_record(output)`**: disambiguan "qué nodo corriente arriba produjo este output" por `type_id` (vía `state.executed_nodes`), no por la forma del output — necesario porque los outputs de elementos SMC (order blocks, swings) comparten columnas OHLC genéricas (`low`/`high`) con cualquier otro, haciendo el matching por forma ambiguo. Reemplazó un primer diseño (`_latest_upstream_record` por claves de dict requeridas) que resultó ambiguo en la práctica.
- **`gate_triggered(node, state)`**: variante de `_upstream_triggered` (que hace OR sobre TODOS los edges entrantes) que excluye edges provenientes de `_STRUCTURE_DATA_TYPES = ("bullish-ob","bearish-ob","swing-high","swing-low","atr","bollinger-bands")`. Necesario porque `stop-loss`/`take-profit`/`tranche-entry` ahora también reciben edges de referencia estructural (para la fórmula ATR) además de su edge de señal real — esos outputs estructurales son casi siempre "truthy" (lista/dict no vacío), así que el `_upstream_triggered` original los confundía con la señal disparándose. Aplicado solo a `StopLossExecutor`/`TakeProfitExecutor`/`TrancheEntryExecutor` — NO a `MarketOrderExecutor`/`LimitOrderExecutor`/`MaxOpenPositionsExecutor` (sin edges estructurales, cambiarlos habría sido riesgo sin beneficio).
- **`TrancheEntryExecutor`** (`execution.py`, type_key `tranche-entry`): calcula 3 precios de tramo desde un Order Block conectado (Tranche1=`ob.top`, Tranche2=punto medio, Tranche3=`ob.bottom`), coloca 3 LIMIT reales (tamaños configurables, default 30/40/30) y guarda el grupo en `context_data["_tranche_groups"]`.
- **`FractalKillSwitchExecutor`** (`risk.py`, reusa el `NodeDefinition` `fractal` ya existente en el fixture): lee `strategy.fractal`, una vez roto escribe `context_data["_kill_switch_triggered"]=True` de forma permanente (nunca se resetea); si `strategy.fractal is None` no bloquea nada.
- **`SemesterRangeExecutor`/`YearlyRangeExecutor`** (`structure_htf.py`, nuevo archivo): high/low del semestre (H1 Ene-Jun/H2 Jul-Dic) o año calendario actual, sobre `resolve_df` con `timeframe="1d"`.
- **`NumericThresholdExecutor`** (`strategy_logic.py`, type_key `numeric-threshold`): compara un campo numérico contra un umbral (`gte`/`lte`) o dos campos entre sí con tolerancia — el nodo de comparación que ya había quedado anotado como gap pendiente en Fase 5.
- **`AtrExecutor`** + `IndicatorsAccessor.atr(length=14)` (`pandas_luarix`) y **`BullishDivergenceExecutor`/`BearishDivergenceExecutor`** (`classic.py`) — exponen como nodos ejecutables indicadores que ya existían en la librería pero sin executor.
- **SL/TP dinámico real**: `_compute_exit_level` (`execution.py`) ganó las ramas `structure_atr` (buy: `min(ob.low, swing_low) - 0.5*ATR`; sell: `max(ob.high, swing_high) + 0.5*ATR`) y `bb50_target`, reemplazando el placeholder que hasta ahora caía silenciosamente al mismo cálculo por `%` sea cual sea la config (`sl_type`/`tp_type`) — simplificación ya documentada en Fase 3/5, ahora resuelta de verdad para este caso.

### Dos bugs reales encontrados y arreglados vía backtest real (400 días, BTCUSDT, Postgres real) — no hipotéticos

1. **Pyramiding sin límite**: primer intento mostró 12+ fills idénticos al mismo precio, balance cayendo a -108,922. Causa: `_open_positions_count`/`max-trades` solo cuenta posiciones **llenadas**, pero las 3 LIMIT de un tranche-entry pueden quedar pendientes muchos ticks antes de llenarse — durante esa ventana `max-trades` ve `count=0` y deja disparar rondas nuevas sin límite. Se probó primero agregar un nodo `max-trades` en serie (`score_gate → max_trades → entry_gate`) — el output fue **byte-idéntico** al de antes, confirmando que el gate basado en conteo de llenados no puede resolver esto por diseño. **Fix real**: guard directo en `TrancheEntryExecutor.execute()` — si `context_data["_tranche_groups"]` ya tiene un grupo vivo, no dispara una ronda nueva.
2. **Ciclo atascado para siempre tras SL**: con solo el fix anterior, la estrategia disparó exactamente 1 ciclo en 400 días y nunca más — el cierre de ese ciclo fue por SL (no TP), y la lógica de cancelar-hermanas-y-resetear el grupo solo corría en la rama TP_HIT, dejando `_tranche_groups` permanentemente no vacío (bloqueando el guard del bug #1 para siempre). **Fix**: la limpieza (`cancel_order` de las hermanas pendientes + `del context["_tranche_groups"][key]`) ahora corre igual en TP_HIT y en SL_HIT (`paper_runner.py::_on_execution_report`). Simplificación deliberada frente al `all_closed`/red-de-seguridad más matizada del legacy Python/Pine (ver Fase 6) — elegida por robustez ("nunca se queda atascado") dado el alcance "núcleo real" acordado.

**Verificación final** (backtest real 400 días, `run.pk=25`, ambos fixes juntos): 3 fills de ENTRY (0.0367/0.0504/0.0390 BTC — proporción 30/40/30 correcta) a 3 precios de tramo distintos entre 2025-11-21 y 2026-01-31, luego los 3 cerrados por SL compartido en el mismo precio (72975.90) — sin pyramiding, sin atasco, ciclo completo coherente de principio a fin. `check_node_catalog_consistency` confirmó 36/36 executors nuevos/actualizados registrados.

### Grafo real: usuario `luis`, estrategia `IPDAFractals`

Usuario real `security.User(username="luis", pk=2)` creado vía migración DEBUG-gated (mismo patrón que `luarix-dev` de fases previas). `Strategy(owner=luis, name="IPDAFractals")` + `WorkflowGraph` (18 nodos, 26 edges) implementando el scoring real de Luis (Equal Sweep +35, Order Block +25, Divergencia +20, Sobreventa/sobrecompra +15, BB50 Near-Lower +15, umbral ≥50) 100% con nodos genéricos (nuevos + ya existentes) — sin acoplar el motor de Django a `app/tradingview/smc_indicator.py`. **Esta `Strategy`/`WorkflowGraph`/usuario/`BrokerAccount`/`Fractal` son el entregable real pedido — NO se borran, a diferencia de la data sintética de verificación de fases anteriores.**

### Frontend

`getProviderCatalog`/`getIntervalCatalog` (Parte 1) ya apuntaban a Django antes de esta sesión (trabajo hecho en paralelo, verificado consistente: `hooks/useProviderCatalog.ts`, `hooks/useCachedCandles.ts`, `lib/luarix-workflow-api/client.ts`, `components/markets/chart/market-chart-workspace.tsx`). Código FastAPI-específico (`lib/luarix-api/client.ts`/`queries.ts`) confirmado eliminado, cero referencias residuales (grep).

**Hallazgo importante para futuras sesiones**: el panel de catálogo de nodos del builder (`lib/builder-nodes.ts`) **NO es data-driven desde el `NodeDefinition` de Django** — es un array TS hardcodeado (`nodeDefinitions: NodeDefinition[]`, ~4000 líneas) que actúa como la única fuente de verdad para la paleta/render/modal de propiedades del builder visual. La suposición original del plan ("aparecen automáticamente, es data-driven") era incorrecta — quedaba marcada como "a confirmar" y, al confirmar, resultó falsa. Se agregaron a mano las 3 entradas que faltaban (`fractal`, `tranche-entry`, `numeric-threshold`) espejando params/opciones exactos del fixture Django (`semester-range`/`yearly-range`/`atr`/`bullish-divergence`/`bearish-divergence` ya habían sido agregados en paralelo antes de esta verificación). **Cualquier `NodeDefinition` nuevo en el backend a futuro necesita este mismo paso manual en `lib/builder-nodes.ts`** — no hay sincronización automática entre el fixture de Django y este catálogo del frontend; es una deuda de arquitectura conocida, no resuelta en esta pasada (reconectar el builder a un catálogo real vía API sigue fuera de alcance, ya documentado en Fase 5/6).

`npx tsc --noEmit` y `eslint` limpios tras los cambios (los 17 errores/2 warnings de `eslint` son de `react-hooks/set-state-in-effect` en archivos preexistentes no tocados por esta sesión — `theme-toggle.tsx`, `carousel.tsx`, `use-mobile.ts`, `useAgentMode.ts`, `useAiModel.ts`, `useAiPanelOpen.ts`, `useMarketData.ts`, `useMarketSymbol.ts` — deuda técnica preexistente, no una regresión de esta pasada).

### Segunda estrategia de `luis`, más simple, para smoke-tests rápidos: "BB Touch Simple"

Por pedido explícito del usuario (backtestear el grafo de 18 nodos de IPDAFractals repetidas veces es lento, y lo que hace falta verificar rápido es "si el código funciona", no si la estrategia es rentable): segunda `Strategy`/`WorkflowGraph` real, también de `luis` (pk=38/graph pk=37, coexiste con IPDAFractals, no la reemplaza), con un solo indicador — 5 nodos: `on-candle(4h)` → `bollinger-bands(20,2)` → `numeric-threshold(near, tolerance=0.3%)` (precio toca banda inferior) → `max-trades(1)` → `{market-order, stop-loss(percent 2%), take-profit(percent 4%)}`.

**Encontró un bug real de inmediato, en el primer intento (sin `max-trades`)**: exactamente el mismo patrón de pyramiding ya documentado y resuelto para `tranche-entry` en IPDAFractals — un `market-order` sin gate de conteo de posiciones dispara una orden nueva CADA VEZ que la señal es truthy, así que mientras el precio se mantiene cerca de la banda inferior durante varias velas seguidas, se apilan entradas sin límite (balance cayó a -39,393 en el log). Fix: agregar `max-trades(value=1)` en serie antes de `market-order`/`stop-loss`/`take-profit` — mismo patrón ya validado en Fase 5 (`señal periódica → max-trades → {market-order, stop-loss, take-profit}`). Con el gate, las entradas/salidas alternan correctamente, sin pyramiding.

**Con el fix de `max-trades`, expuso una causa raíz más precisa de un bug YA CONOCIDO** (Fase 5, "log de capital negativo → número complejo" documentado arriba en la sección de Fase 5 gotchas): `BacktestStats.avg_monthly_return`/`.apr` (`backtesting/stats.py`, framework legacy en la RAÍZ del repo, cargado por ruta de archivo por colisión de nombre con la app Django `backtesting` — ver `paper_runner.py::_load_root_module` — y reusado deliberadamente "tal cual, sin tocarlo") hacen `ratio = final_capital / initial_capital` y luego `ratio ** (1/months)` — una potencia fraccionaria de un número NEGATIVO da un `complex` en Python, que revienta al guardarlo en el `FloatField` de Postgres.

Causa raíz exacta (antes solo se sabía que "pyramiding sin límite" lo disparaba; ahora se confirmó un disparador mucho más amplio y común): `PaperBacktestRunner` alimenta `self.stats.update_capital(self.broker.get_balance()["USDT"], ...)` — es decir, **`final_capital` es el cash crudo (USDT), no el equity real** (cash + valor a mercado de cualquier posición abierta). Con un tamaño de posición cercano al 100% del capital (el default de `MarketOrderExecutor`/`FULL_POSITION_PERCENT`), CUALQUIER backtest que termine su ventana con una posición todavía abierta (no solo los que hacen pyramiding) va a reportar cash muy negativo aunque el equity real sea positivo — y de ahí el crash. Reproducido de nuevo en el backtest corto (60 días) de BB Touch Simple, con el gate de `max-trades` ya puesto y sin ningún pyramiding, solo por terminar la ventana con una posición abierta.

**Decisión del usuario, confirmada explícitamente** (`AskUserQuestion`): dejarlo como bug conocido/documentado, NO tocar `backtesting/stats.py` (mantiene la convención ya establecida de no tocar el framework legacy reusado tal cual). El código de nodos nuevo (bollinger-bands, numeric-threshold, max-trades, market-order, stop-loss, take-profit) quedó confirmado correcto igualmente vía el log de ejecución real (20+ operaciones, entradas/salidas alternadas sin pyramiding, niveles de SL/TP matemáticamente correctos: -2%/+4% exactos sobre el precio de entrada) — el crash ocurre DESPUÉS, en la persistencia de estadísticas del framework legacy, no en la ejecución del grafo. Si en el futuro se decide arreglarlo, el fix mínimo sería: en `avg_monthly_return`/`apr`, si `ratio <= 0`, devolver un valor centinela (p. ej. `-100.0`) en vez de intentar la potencia fraccionaria — pero no se aplicó en esta pasada por decisión explícita del usuario.

### Login real por usuario (Django JWT) reemplazando el gate compartido del frontend

El usuario reportó no poder loguearse en el frontend con `luis`/`amina` (contraseñas reales, confirmadas correctas contra Django vía `authenticate()`). Causa real: el frontend tenía **dos mecanismos de auth desconectados** — (1) `app/login` validaba contra un único par usuario/password fijo en `.env` (`AUTH_USERNAME`/`AUTH_PASSWORD`, `lib/auth.ts::checkCredentials`, sin concepto de múltiples usuarios) y (2) por separado, `lib/luarix-workflow-api/auth.ts` se autenticaba en segundo plano SIEMPRE como el usuario fijo `luarix-dev`, sin importar quién pasara el gate. `luis`/`amina` nunca iban a funcionar en esa pantalla porque no la validaba en absoluto.

**Fix**: login real conectado a Django, con dos cookies separadas — `luarix_session` (marcador HMAC existente, sigue gateando páginas vía `middleware.ts`, sin cambios) y `luarix_dj_refresh` (nueva, httpOnly, guarda el refresh token real de Django del usuario que inició sesión). `loginAction` (`app/login/actions.ts`) ahora llama `authenticateWithDjango()` (nuevo, `lib/auth.ts`) contra `POST /api/v1/auth/token/` con las credenciales reales tipeadas. Nuevo Route Handler `app/api/auth/access-token/route.ts` lee la cookie httpOnly y la cambia por un access token de corta vida vía `POST /api/v1/auth/token/refresh/`; `lib/luarix-workflow-api/auth.ts::fetchToken` ahora pide ese access token a la ruta local (mismo origen, sin CORS) en vez de autenticarse con el usuario `luarix-dev` fijo — se eliminó ese bootstrap por completo.

**Detalle no obvio, importante para no repetir el error**: `SIMPLE_JWT` tiene `ROTATE_REFRESH_TOKENS=True` + `BLACKLIST_AFTER_ROTATION=True` (`settings.py:224`) — cada `POST /token/refresh/` devuelve un refresh token NUEVO y blacklistea el viejo. Esto significa: (a) la ruta `/api/auth/access-token` debe re-escribir la cookie con el refresh nuevo en CADA llamada, o la siguiente falla contra un token ya blacklisteado (verificado con un test real: reusar el mismo refresh dos veces da `401 Session expired` la segunda vez); (b) `logoutAction`'s blacklist best-effort debe hacer un refresh PRIMERO (para tener un access token válido, que `LogoutView` exige) y blacklistear el refresh NUEVO que ese refresh devuelve, no el viejo de la cookie — blacklistear el viejo sería un no-op porque ya está blacklisteado por la rotación misma.

**Decisión de alcance confirmada con el usuario**: login real obligatorio en todos lados (dev local y cloud), sin atajo de bootstrap fijo para desarrollo — `middleware.ts` no se tocó (sigue sin gatear páginas fuera de `ENVIRONMENT=cloud`), pero como ya no hay bootstrap silencioso, cualquier hook que llame a la API ahora necesita que alguien haya pasado por `/login` de verdad primero, en dev local también.

**Verificado** (sin navegador real disponible en este entorno — Playwright no estaba instalado/configurado — se verificó equivalentemente vía curl contra los servidores Django+Next.js reales corriendo): `POST /api/v1/auth/token/` 200 real para `luis` y `amina`; `/api/auth/access-token` da 401 sin cookie, 200+rotación con cookie válida; reusar un refresh ya rotado da 401 (`Session expired`); secuencia completa de logout (refresh → logout con el par rotado) confirmada contra Django real — el refresh queda blacklisteado (`"Token is blacklisted"` al reintentarlo). `npx tsc --noEmit` y `eslint` limpios.

### Bug real encontrado y corregido: "integer out of range" al lanzar un backtest desde el builder (frontend)

El usuario reportó `psycopg.errors.NumericValueOutOfRange: integer out of range` al backtestear, asociándolo con la fecha de inicio que acababa de tipear ("15 junio 2026"). La fecha no tenía nada que ver: `hooks/useBacktestRun.ts:71` (frontend) pasaba `Date.now()` como el `version` de `toStrategyGraph(id, name, version, graph)` — `version` es un `IntegerField` de Postgres (`workflows/models/graph.py:26`, int4, máx `2147483647`), y `Date.now()` da milisegundos desde epoch (~1.78 billones en 2026), muy por encima del límite. DRF no lo rechaza en validación (`serializers.IntegerField()` sin `max_value` no impone el límite de Postgres), así que llega intacto hasta el `UPDATE` y revienta ahí — **fallaba siempre, para cualquier fecha, cualquier usuario, cualquier estrategia**, no algo puntual de ese input.

Fix: usar el contador de versión real que ya existe al lado (`lib/builder-store.ts::version`, arranca en 1, se incrementa de a uno en `markSaved`) en vez de `Date.now()`. Cambio de una línea.

Verificado contra el servidor Django real del usuario (puerto 8000) sobre la estrategia real `BB Touch Simple` (pk=38): reproducido el 500 exacto con un `version` estilo `Date.now()`; confirmado 200 con un `version` chico; confirmado el flujo completo reportado por el usuario (`POST /api/v1/backtesting/runs/` con `start_time=2026-06-15`) devuelve `201` y arranca (`status=running`) sin el error.

### Veredicto: ¿ya se puede borrar `fastapi_server`/`backtesting_api`?

Los 2 bloqueadores documentados al final de Fase 6 quedan **cerrados**: `getProviders`/`getIntervals` migrado a Django (Parte 1), y la estrategia IPDA de `backtesting_api` tiene ahora una réplica real (núcleo + fixes de bugs conocidos) corriendo sobre el motor de grafos de Django (Parte 2), verificada end-to-end con datos reales. Decisión de borrar los servicios FastAPI legacy queda a criterio del usuario — no ejecutada en esta pasada (fuera del alcance pedido, que era "reemplazar", no "borrar").

---

## Fix real de `avg_monthly_return`/`apr` + streaming en vivo de progreso/métricas por WebSocket (sesión actual)

El usuario pidió arreglar de verdad el bug de `avg_monthly_return`/`apr` (ya documentado arriba, dejado sin tocar por decisión explícita anterior) y agregar streaming en vivo del % de progreso + métricas corriendo del backtest (estilo MetaTrader), con todos los números redondeados a 2 decimales (decisión: redondeo solo en el backend, el frontend hereda valores ya redondeados).

### Fix del bug: `backtesting/stats.py` (raíz del repo)

`avg_monthly_return`/`apr` (líneas ~338-359) ganan un guard `if ratio <= 0: return -100.0` antes de intentar `ratio ** (1/months)`/`ratio ** (1/years)` — exactamente el fix mínimo que el propio equipo ya había dejado anotado. Verificado con un backtest real que termina con `final_capital=-1115.52` (mismo escenario que crasheaba antes): `avg_monthly_return`/`apr` ahora persisten como `-100.0` (float real, no `complex`), `status=completed` en vez de que `run.save()` reviente.

### Redondeo centralizado: `paper_runner.py::_persist_results`

Nuevo helper `_r(value)` (`round(value, 2)` para `int`/`float`, pasa `None`/otros intactos) aplicado a los 21 `FloatField`s de métricas de `BacktestRun` (antes esta ruta no redondeaba nada — solo `BacktestStats.to_dict()`, usado nada más para el mensaje WS final, ya redondeaba). También aplicado a `equity_curve` y a los campos de precio/PnL de `Trade` (`fill_price`/`tp_price`/`sl_price`/`exit_price`/`pnl`/`pnl_pct`).

**Cuidado real, no aplicado a `quantity`**: `Trade.quantity` (en BTC u otro activo, típicamente `0.03xx`) se dejó **sin redondear** a propósito — redondear a 2 decimales convertiría `0.0367` en `0.04`, ~9% de distorsión real en el tamaño de la posición. 2 decimales es la precisión natural para precios/PnL en USD, no para cantidades de cripto con muchos decimales significativos.

### Streaming en vivo: WebSocket nuevo para % + métricas, en paralelo al NDJSON existente

`PaperBacktestRunner.run()` calcula `progress_pct = i/total_ticks*100` en el loop y llama `_send_progress` cada `max(1, total_ticks//100)` ticks (~100-140 mensajes por corrida, no uno por vela — evita saturar el WS). `_send_progress` (WS, grupo `backtest_{run_id}`, `BacktestConsumer` ya existía pero nunca se había podido usar de verdad — ver más abajo) ahora manda, además de `time/close/capital/n_trades` que ya mandaba: `progress_pct`, `win_rate`, `total_pnl`, `total_pnl_pct` — todos redondeados con `_r()`. El NDJSON existente (`GET runs/{id}/stream/`, eventos de nodo) **no se tocó**, sigue funcionando igual, corre en paralelo.

Frontend: nuevo `hooks/useBacktestProgressSocket.ts` (WebSocket real, `new WebSocket(...)`, no fetch/NDJSON) conectado en paralelo a `useBacktestStream` desde `useBacktestRun.ts::start()`. `lib/run-store.ts::RunState.progress` se amplió (`progressPct`/`winRate`/`totalPnl`/`totalPnlPct` nuevos, además de `finalCapital`/`nTrades` ya existentes) con una acción nueva `applyLiveProgress`. El panel "Backtesting" del builder (`components/builder/workspace/builder-info-panel.tsx`, el grid de 2 `StatWidget` que antes solo tenía "Final capital"/"Trades so far") gana una barra de progreso (`components/ui/progress.tsx`, ya existía sin usar) + 2 tiles nuevos ("Win rate", "Total PnL").

### 3 bugs reales de infraestructura/API encontrados y corregidos DURANTE la verificación (no hipotéticos, bloqueaban la feature por completo)

Verificar esto en vivo (no solo leer código) destapó una cadena de problemas preexistentes, ninguno introducido por esta sesión, todos necesarios de arreglar para que el WebSocket funcionara de verdad por primera vez:

1. **`daphne`/`channels` nunca estuvieron en `INSTALLED_APPS`**: `luarix_rest_api/asgi.py`/`routing.py`/`CHANNEL_LAYERS` estaban bien configurados desde hace tiempo, pero `manage.py runserver` corría WSGI puro (sin `daphne` como primera entrada de `INSTALLED_APPS`, Channels no puede reemplazar el comando `runserver` por uno ASGI-aware) — cualquier `ws://` daba **404** sin importar que Redis estuviera corriendo. Fix: `"daphne"` (primero, antes de `django.contrib.staticfiles`) + `"channels"` agregados a `INSTALLED_APPS`. Confirmado con el propio traceback del usuario tras el restart: pasó de 404 a un error distinto (ver #3), confirmando que la ruta SÍ empezó a resolverse.
2. **`channels_redis` no estaba instalado** (aunque sí `channels`, `daphne`, `redis` sueltos, y Redis-servidor sí corría y respondía `PING`): `CHANNEL_LAYERS` apunta a `channels_redis.core.RedisChannelLayer`, que no se podía importar — cualquier conexión WS daba **500** (`InvalidChannelLayerError`, confirmado reproduciendo en proceso con `channels.testing.WebsocketCommunicator` en vez de adivinar). Fix: `pip install channels_redis`. De paso, `requirements.txt` (que estaba en **UTF-16** por algún `pip freeze > requirements.txt` corrido alguna vez desde PowerShell — al abrirlo se veía con espacios entre cada letra) se regeneró en UTF-8 real vía `pip freeze` corrido desde bash, capturando también `channels`/`daphne`/`channels_redis` que nunca habían quedado pineados.
3. **`POST /api/v1/backtesting/runs/` nunca devolvía el `id` del run recién creado**: `BacktestRunViewSet.get_serializer_class()` usa `BacktestRunCreateSerializer` (solo 6 campos de escritura) también para la respuesta del `create()` — DRF por defecto responde con `serializer.data` del serializer usado para validar el input, que nunca tuvo campo `id`. El frontend (`launchBacktest()`, tipado `Promise<BacktestRun>`) confiaba en `run.id` para armar la URL del stream NDJSON existente Y del WebSocket nuevo — ambos rompían con `.../undefined/` (confirmado con el traceback real del usuario: `ValueError: No route found for path 'ws/backtest/undefined/'`, y el NDJSON daba 404 silencioso en el mismo log). **Bug real preexistente, no introducido en esta sesión** — el stream NDJSON ya estaba roto de la misma forma desde que existe, simplemente nadie lo había notado porque nunca se verificó con el id real. Fix: `BacktestRunViewSet.create()` override — sigue validando con `BacktestRunCreateSerializer`, pero responde con `BacktestRunSerializer(serializer.instance).data` (el serializer de lectura completo, con `id`).

### Hallazgo aparte, no arreglado (fuera de alcance de esta pasada): `perform_create` sigue lanzando en un hilo daemon, no Celery

El comentario en `BacktestRunViewSet.perform_create` (`"No hay worker Celery/Redis corriendo todavía en este entorno"`) está desactualizado — el usuario ya tiene Celery corriendo, pero el código sigue lanzando `PaperBacktestRunner(run).run` en un `threading.Thread` en vez de `run_backtest_task.delay(run.id)` (la tarea Celery, `backtesting/tasks.py`, ya existe pero no se usa). No se tocó en esta pasada — no fue parte de lo pedido, y cambiar el mecanismo de ejecución es una decisión aparte (afecta pausa/resume, cancelación, y cómo se recupera de un restart del proceso a mitad de una corrida).

### Verificado end-to-end (servidor real del usuario, puerto 8000, Redis real, Postgres real)

Backtest real de 60 días (`BB Touch Simple`, strategy pk=38) lanzado vía `POST /runs/`, WebSocket conectado con un cliente Python real (`websockets`, con header `Origin: http://localhost:3000` — **sin un `Origin` válido, `AllowedHostsOriginValidator` cierra la conexión con código 1000 sin loggear error, algo a tener en cuenta si se vuelve a probar con un cliente que no sea un navegador real**): 143 mensajes `progress` recibidos (no 360, uno por vela — el throttling funciona), `progress_pct` avanza de 1.38 a 97.24 de forma monótona, `win_rate`/`total_pnl`/`total_pnl_pct` cambian coherentemente con los trades reales (ej. `win_rate=33.33` tras 1 TP de 3 trades), todos los valores con exactamente 2 decimales. Mensaje final `complete` recibido (confirma que `_persist_results` ya no revienta). Métricas finales persistidas confirmadas vía `GET /runs/{id}/`: `avg_monthly_return=-100.0`, `apr=-100.0` (ambos `float`, no `complex`), `final_capital=-1115.52` (el mismo escenario negativo que antes crasheaba). `npx tsc --noEmit`/`eslint` limpios en el frontend (el único error de ESLint pre-existente en `builder-info-panel.tsx` es de código no tocado por esta sesión, ya documentado como deuda técnica preexistente en la Fase de login).

---

## Tab Backtesting: layout roto, todas las métricas en vivo, gráfico de equity + tabla de entradas (sesión actual)

Tras el streaming en vivo (sección anterior), el usuario reportó 3 problemas: el layout del tab se desbordaba, el WebSocket solo mandaba 4 métricas (comparado con los ~24 campos visibles en `/admin/backtesting/backtestrun/<id>/change/`), y pidió mejorar la UI (gráficos, tabla de entradas).

### Fix del layout

`components/builder/workspace/builder-info-panel.tsx`, `TabsContent value="backtesting"`: usaba `items-center justify-center` sin `ScrollArea` (a diferencia de los tabs "Workflow"/"Output", que sí envuelven su contenido en `ScrollArea`) — con solo 4 tiles cabía de casualidad; con más contenido se salía del panel. Fix: envuelto en `ScrollArea`, contenido en `flex-col` normal.

### Backend: snapshot completo de métricas en cada mensaje de progreso

Nuevo `PaperBacktestRunner._metrics_snapshot(as_of)`: setea `self.stats.end_time = as_of` directo (sin pasar por `stats.finish()`, que tiene efectos secundarios sobre `_exposure_start`/`total_exposure` que no deben dispararse antes de tiempo) — necesario porque `trades_per_day`/`avg_monthly_return`/`apr`/`backtest_duration` de `BacktestStats` (raíz del repo, no se toca) dependen de `end_time`, que es `None` hasta el final. Devuelve los 24 campos que `BacktestRun` persiste, cada uno pasado por el `_r()` ya existente (redondeo a 2 decimales) — **no reusa `stats.to_dict()`** porque ese redondea `win_rate`/`long_win_rate`/`short_win_rate` a 1 decimal, no 2, inconsistente con el resto. `_send_progress` ahora manda este snapshot completo en cada mensaje (además de `time`/`close`/`progress_pct`, que son del tick, no de `BacktestStats`).

Verificado en vivo: cada mensaje `progress` trae 34 keys (24 métricas + `type`/`time`/`close`/`progress_pct` + `n_tp`/`n_sl`/counts), y la última métrica antes de `complete` coincide EXACTAMENTE con lo persistido en `BacktestRun` tras terminar (confirmado campo por campo: `final_capital`, `total_pnl`, `win_rate`, `n_tp`/`n_sl`, `profit_factor`, `avg_monthly_return`/`apr`, `max_drawdown_pct` — todos idénticos entre el último snapshot en vivo y `GET /runs/{id}/`).

### Backend: nuevo evento WS `"trade"` — entradas cerradas en vivo

`_on_execution_report` (rama TP_HIT/SL_HIT) ahora llama a un nuevo `_send_trade(entry_id)` justo después de `stats.on_tp_hit`/`on_sl_hit` — manda por el mismo grupo de canal (`type="backtest_trade"`) los mismos campos que tendrá la fila `Trade` real (direction, fill_price, tp_price, sl_price, quantity, exit_price, exit_reason, pnl, pnl_pct, fill_time, exit_time), sin persistir nada antes de tiempo (el evento vive solo en el WebSocket — `Trade` real se sigue creando únicamente en `_persist_results`, al final, como ya estaba decidido). `backtesting/consumer.py` gana el handler `backtest_trade` correspondiente (mismo patrón que `backtest_progress`/`backtest_complete`).

Verificado en vivo: 11 eventos `"trade"` recibidos a lo largo de la corrida (no al final), cada uno en el momento exacto en que la entrada cierra — valores (`pnl`, `pnl_pct`, `exit_reason`) coherentes con los niveles de SL (-2%) / TP (+4%) configurados en el grafo.

### Frontend

- `lib/luarix-workflow-api/types.ts`: `BacktestProgressSocketMessage` ampliado a las 24 métricas; nuevo `BacktestTradeSocketMessage`.
- `lib/run-store.ts`: `RunState.progress` pasa a `RunProgress` (24 campos, en camelCase); nuevo `equitySeries: EquityPoint[]` (un punto por mensaje `progress`, usando `time`/`final_capital` que ya viajan — no hace falta que el backend reenvíe el `equity_curve` completo cada vez, evitando que el payload crezca sin límite); nuevo `liveTrades: LiveTrade[]` (uno por mensaje `trade`). `hooks/useBacktestProgressSocket.ts` distingue `message.type` (`"progress"` vs `"trade"`) y llama a la acción correspondiente.
- `components/builder/workspace/builder-info-panel.tsx`: la grilla de 4 tiles se reemplaza por 5 secciones (`MetricsSection`, nuevo helper local) — Overview, Trades (12 tiles: conteos, win rates long/short, avg/largest win-loss, avg trade), Risk, Streaks (incluye "Longest trade", con un `formatDuration()` local que convierte segundos a "Xd Yh"/"Xh Ym"), Returns — más un gráfico de equity en vivo (`components/builder/workspace/live-equity-chart.tsx`, nuevo, mismo patrón visual/Recharts que `components/platform/equity-curve.tsx` pero parametrizado con datos reales — **no se tocó `equity-curve.tsx`** para no arriesgar a las otras páginas que ya lo usan con datos mock) y una tabla de entradas en vivo (`LiveTradesTable`, nuevo helper local, mismo patrón `Table`/`TableRow` que la tabla de resultados de `backtesting-workspace.tsx`, más reciente primero).
- `hooks/useBacktestRun.ts`/`components/builder/strategy-builder.tsx`: exponen/pasan `equitySeries`/`liveTrades` desde el store hasta `BuilderInfoPanel`.

### Verificado end-to-end (servidor real, puerto 8000)

Backtest real de 60 días (`BB Touch Simple`, pk=38): 145 mensajes `progress` (34 keys cada uno, todos con 2 decimales), 11 mensajes `trade` (uno por cada entrada cerrada, con `pnl`/`exit_reason` correctos), último snapshot en vivo idéntico campo-por-campo al `BacktestRun` final persistido. `npx tsc --noEmit`/`eslint` limpios (los 6 hallazgos de ESLint son pre-existentes, confirmados vía `git diff` que ninguno cae en líneas tocadas por esta sesión).

---

## Página standalone /strategy/[id]/backtesting: modo Live + panel de posiciones abiertas (sesión actual)

El usuario pidió poder lanzar y ver un backtest completo desde `/strategy/[id]/backtesting` (grafo, velas, config, métricas, progreso, entradas — "como un trader profesional"). La página **ya existía** pero era de solo lectura (`BacktestingWorkspace`, última corrida completada, botón "Go to builder" como única vía para lanzar una nueva). El fetch de la referencia visual dada (template ThemeForest SignalAIX) no devolvió contenido usable (preview renderizado por JS) — el diseño se basó en convenciones estándar de dashboards de trading (KPI strip agrupado, velas + equity, tablas de posiciones abiertas/cerradas) combinadas con el sistema de diseño ya existente.

### Backend: panel de posiciones abiertas (PnL no realizado en vivo)

Nuevo `PaperBacktestRunner._open_positions_snapshot(current_price)`: itera `self.stats._active` (confirmado leyendo `on_fill`/`_close` de `backtesting/stats.py` — es exactamente "entradas ya llenas, esperando TP/SL", nunca más de lo que `tranche-entry` puede dejar abierto a la vez, hasta 3). Calcula PnL no realizado contra el `close` del tick actual (`(current_price - fill_price) * quantity` para LONG, invertido para SHORT), redondeado con `_r()`. Se agrega como `"open_positions"` (lista, no un único objeto) al mismo mensaje `"progress"` que ya manda el snapshot completo de métricas — no es un evento WS nuevo.

### Refactor: sistema de métricas en vivo extraído a un componente compartido

El sistema de métricas en vivo (barra de progreso, 5 secciones de `StatWidget`, tabla de entradas) vivía como funciones privadas dentro de `builder-info-panel.tsx` (sesión anterior). Se extrajo a `components/builder/workspace/live-backtest-dashboard.tsx` (`LiveBacktestDashboard`, con `formatDuration`/`MetricsSection`/`LiveTradesTable`/`OpenPositionsTable` — esta última nueva, sexta sección "Open Positions") para que tanto el panel docked del builder como la página standalone nueva rendericen exactamente lo mismo sin duplicar ~150 líneas de JSX. `builder-info-panel.tsx` pasó a importar este componente; no hay cambio visual en el panel del builder, solo de dónde vive el código (confirmado — mismo output, ~200 líneas menos en ese archivo).

De paso, `run-backtest-dialog.tsx` (el diálogo de lanzar backtest ya existente en el builder) se separó en `backtest-config-form.tsx` (el formulario puro, sin acoplamiento a `Dialog`) + un wrapper fino — reusado tanto por el diálogo original (sin cambio de comportamiento) como por el panel de config inline de la página nueva.

### La página: 3er modo "Live" automático

`components/builder/workspace/backtesting-view-toggle-panel.tsx` (el composer de la página, sin tocar `page.tsx` ni `backtesting-workspace.tsx`) gana:
- `useLoadStrategyGraph(strategyId)` al montar — hidrata el store global `useBuilderStore`, requisito real descubierto en la investigación: `useBacktestRun.start()` lee el grafo a lanzar de ESE store (no de `useStrategyBackendGraph`), así que sin esto `start()` revienta con "Add at least one node...".
- Nuevo `useBacktestRun(strategyId, strategyName).attach(runId, nodes)` (método nuevo en el hook): conecta los canales NDJSON/WebSocket a una corrida YA EN CURSO (lanzada desde el builder, detectada vía `useBacktestRunsList` buscando `status running/paused` para esta estrategia) sin repetir el flujo de crear-estrategia/sync-grafo/lanzar de `start()`. Se auto-adjunta solo en el flanco de "se detectó una corrida externa Y esta página todavía no seguía ninguna" — no pelea con la corrida propia de la página si ya hay una.
- El toggle Results/Graph gana "Live" (solo visible mientras hay una corrida activa, propia o adjuntada) — se auto-selecciona en el flanco de subida de "hay corrida activa" (`useRef` guardando el valor anterior), sin forzar de vuelta a Live si el usuario elige manualmente Results/Graph mientras sigue corriendo.
- Botón "Run backtest" (visible solo sin corrida activa) abre `BacktestConfigForm` inline (no un diálogo) en una card sobre el contenido.
- Nuevo `components/builder/workspace/backtesting-live-workspace.tsx` (modo Live): `PriceChart` (velas reales del rango vía `useCachedCandles`, entradas cerradas como marcadores vía nuevo `toLiveBacktestTrades()` en `lib/backtest/trade-adapter.ts`, detecciones en vivo vía `deriveLiveShapes(nodeEvents, nodes)` — mismo mecanismo que ya usa `strategy-builder.tsx`) y `ReadOnlyStrategyGraph` lado a lado (`grid lg:grid-cols-2`), `LiveBacktestDashboard` a todo el ancho debajo. Nuevo `useBacktestRunDetail(runId)` (`hooks/useBacktestRuns.ts`) resuelve `symbol`/`timeframe`/`start_time`/`data_source_account` de la corrida para poder pedir las velas (usa `end=ahora` ya que `end_time` del run sigue `null` mientras corre).

### Verificado

`manage.py check` limpio. `npx tsc --noEmit` limpio. `eslint` limpio en todo el código nuevo/tocado de esta sesión — el único hallazgo en el archivo nuevo (`backtesting-view-toggle-panel.tsx`, el efecto que resuelve `backendStrategyId` desde localStorage) es el mismo patrón `react-hooks/set-state-in-effect` ya presente en 4 lugares preexistentes de este mismo subsistema (`backtesting-workspace.tsx`, `strategy-builder.tsx` x3) — replicado deliberadamente para consistencia con la convención ya establecida, no una regresión nueva.

**Pendiente de verificación en vivo** (servidor Django del usuario quedó inalcanzable tras el último edit de `paper_runner.py` — mismo patrón de autoreload de sesiones anteriores, no confirmado si ya volvió): confirmar `open_positions` con valores reales de PnL no realizado, y un recorrido real por el navegador del flujo completo (lanzar desde la página nueva, ver Live, completar, volver a Results).

---

## Análisis competitivo de "Stratos" (plataforma de trading automatizado) — sin acceso a YouTube en este entorno (sesión actual)

El usuario pidió analizar a fondo una plataforma vista en 2 vídeos de YouTube para comparar contra Luarix. Documento completo en `docs/plans/stratos-platform-analysis.md`. Aquí solo lo que hay que recordar para no repetir intentos fallidos ni perder contexto de las limitaciones.

### Este entorno NO tiene acceso de red a YouTube — no reintentar

`WebFetch` a `youtube.com` → 403. `yt-dlp` (instalado vía `pip install yt-dlp`, funciona) → mismo 403 a nivel de proxy: `curl -sS "$HTTPS_PROXY/__agentproxy/status"` confirma `recentRelayFailures` con `"gateway answered 403 to CONNECT (policy denial or upstream failure)"` para `www.youtube.com:443` — es política de red del sandbox, no un límite de la herramienta. Probado también contra dominios alternativos de transcripción (`youtubetranscript.com`, `noembed.com`) y `google.com` genérico: **mismo 403 de CONNECT** — o sea, el proxy bloquea prácticamente todo lo que no está en la whitelist (`noProxy` del status: solo `anthropic.com`, `registry.npmjs.org`, `pypi.org`, `jsr.io`, `crates.io`, `proxy.golang.org`, IPs privadas). `WebSearch` sí funciona (va por infraestructura propia de Anthropic, no por este proxy), pero no encontró nada indexado bajo el nombre exacto "Stratos" como plataforma de trading algorítmico — todas las coincidencias son irrelevantes (CFDs, cripto STOS, etc.). **Conclusión: cualquier análisis de contenido de YouTube en este entorno depende 100% de que el usuario pegue transcripción/texto/capturas — no hay ruta técnica alternativa a probar de nuevo.**

### Nombre real de la plataforma: "Stratos", no "StratOS"

El usuario la nombró "StratOS" en el pedido inicial; el creador (Ignacio Llagos) dice "Stratos" (una palabra) repetidamente en la transcripción. Usar "Stratos" en cualquier referencia futura — buscarlo como "StratOS" no da resultados relevantes.

### Transcripción del primer vídeo: incompleta, cortada a media explicación del Método 6

El PDF (TurboScribe, plan gratuito) corta literalmente con la nota "Este archivo dura más de 30 minutos" + cartel de upgrade — falta el resto del Optimizador AutoPro y el cierre del vídeo. Si el usuario trae más transcripción de esta misma fuente, probablemente sea continuación de ese punto exacto (después de "ST-46" en el documento de análisis).

### Segundo vídeo (`youtu.be/Vgmo3mxDOmM?t=1530`) — aún sin contenido capturado

El usuario solo compartió transcripción del primer vídeo (`mOibRdNtSso`). El análisis en `docs/plans/stratos-platform-analysis.md` NO cubre el segundo enlace. Falta pedir/recibir su transcripción o descripción antes de dar el análisis por completo.

### Lectura crítica ya hecha — no repetir el juicio, solo actualizar si hay más datos

La demo del "Diseñador AutoPro" (Método 4) muestra Profit Factor 7.2 / Drawdown 0.2% / Winrate 92.1% en 38 trades — cifras estadísticamente débiles (muestra muy pequeña) y sospechosas de overfitting o cherry-picking para una demo, pese a que el propio vídeo dedica tiempo a advertir contra exactamente ese error. Tratar cualquier cifra de rendimiento de Stratos como marketing auto-reportado, no como dato verificado — no hay fuente independiente de Stratos (a diferencia de las filas de la tabla 12.5 del documento institucional de Luarix, que sí citan fuente externa).
