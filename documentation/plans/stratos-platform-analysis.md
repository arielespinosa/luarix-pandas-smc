# Stratos — Análisis competitivo y captura de requisitos

> Análisis point-in-time de la plataforma **Stratos** (una sola palabra — no "StratOS"), creada por Ignacio Llagos, a partir de la transcripción del vídeo de YouTube "No programes, automatiza: el método definitivo para traders retail en 2026" (`youtube.com/watch?v=mOibRdNtSso`). Objetivo: extraer **todo** lo funcional que se puede confirmar textualmente, para comparar con Luarix y detectar solapes, huecos y diferenciadores.

## 0. Limitaciones de esta captura (leer antes de usar este documento)

- **Fuente única y parcial.** Este entorno no tiene acceso de red a YouTube (política de proxy del sandbox bloquea `youtube.com` a nivel de gateway; se intentó con `WebFetch`, `yt-dlp` y servicios alternos de transcripción, todos rechazados). Todo lo de abajo sale de la transcripción en PDF que pasó el usuario (TurboScribe), **no de haber visto el vídeo**. No hay confirmación visual de layout, colores, ubicación exacta de botones, etc. — solo de lo que el narrador describe con palabras.
- **Transcripción cortada.** El PDF se corta literalmente a mitad de la explicación del Método 6 (Optimizador AutoPro) con la nota "Este archivo dura más de 30 minutos" seguida del cartel de upgrade de TurboScribe (versión gratuita limitada). **Todo lo que iba después de ese punto (resto del optimizador, conclusión del vídeo, y cualquier "bonus") no está capturado.**
- **Segundo vídeo pendiente.** El usuario mencionó un segundo enlace (`youtu.be/Vgmo3mxDOmM?t=1530`) que aún no ha compartido transcripción/contenido. Este documento **no lo incluye**. Hay que repetir este proceso con ese contenido y fusionar hallazgos.
- **Sin verificación cruzada.** No hay evidencia independiente (sitio web de Stratos, docs públicas, reviews) — las búsquedas web durante esta sesión no encontraron una plataforma "Stratos" de trading algorítmico indexada bajo ese nombre exacto (solo coincidencias irrelevantes: CFDs, la criptomoneda STOS, etc.). Todo lo aquí descrito es **auto-reportado por el propio creador en un vídeo promocional** — tratar las cifras de rendimiento como marketing, no como hecho verificado (ver §4).

Si el usuario quiere cerrar estos huecos: (a) pegar la transcripción del segundo vídeo, (b) subir capturas de pantalla puntuales de las partes que quiera que se analicen visualmente (sí puedo leer imágenes), o (c) confirmar si tiene ya acceso de prueba a Stratos para describir de primera mano lo que falta.

---

## 1. Qué es Stratos (resumen ejecutivo)

Stratos es una plataforma no-code de construcción de bots de trading algorítmico basada en un **lienzo visual de nodos** (grafo de estrategia), con **6 métodos distintos de generación** que van desde importar una plantilla en un clic hasta describir una estrategia por chat a una IA especializada, más un optimizador de parámetros que corre 100% en el navegador del cliente. Target declarado: trader retail sin conocimientos de programación. Integra: biblioteca curada de estrategias, generación asistida por IA (3 niveles de profundidad), diseño automático desde datos históricos (multi-régimen con enrutador dinámico), chat conversacional tipo "ingeniero cuantitativo", y optimización de parámetros sin IA. Exporta a MetaTrader 4/5 (compilación desde la plataforma).

---

## 2. Inventario funcional — Requisitos capturados

Numerados como **ST-xx** para poder referenciarlos luego en comparaciones o backlogs. Todo viene de cita directa o paráfrasis fiel del transcript.

### A. Arquitectura general de la plataforma

- **ST-01 — Lienzo de nodos ("Canva"/canvas).** Editor visual de grafo de nodos donde toda estrategia vive como nodos conectados (indicadores, lógica, acciones de compra/venta). 100% editable en cualquier método de generación.
- **ST-02 — Proyectos personales vs. Biblioteca pública.** Separación explícita entre "biblioteca" (plantillas públicas, curadas por el equipo, de solo lectura/importación) y "proyectos personales" (los bots propios del usuario, mutables). Metáfora usada: tienda de muebles de exposición vs. tu casa.
- **ST-03 — Persistencia server-side de trabajo en curso.** Si se cae la conexión o se recarga el navegador a mitad de una generación con IA, el trabajo continúa en los servidores de Stratos; al reconectar, el resultado ya está listo y guardado en los proyectos personales del usuario (no se pierde el trabajo).
- **ST-04 — Sistema de créditos de IA.** Cada acción que invoca IA cuesta "créditos" (moneda interna, ligada a costo real de inferencia): Wizard cuesta "un par de créditos"; Bot Legendario cuesta 4 créditos; construir desde el chat ingeniero no cuesta crédito adicional (el diseño ya se pagó en la conversación). El Optimizador AutoPro cuesta **cero créditos** porque no usa IA (es cómputo puro).
- **ST-05 — Validación algorítmica automática de grafos.** Todo bot generado por IA pasa una validación estructural: detecta ciclos, nodos huérfanos, tipos de dato incompatibles, conexiones rotas. Si encuentra un fallo, la plataforma **lo repara automáticamente** cuando puede, o marca un error en rojo con explicación de causa y remedio cuando no puede auto-resolverlo.
- **ST-06 — Lista blanca de nodos ("catálogo de nodos").** Toda pieza usada por la IA (en cualquier método) sale de un catálogo cerrado y pre-validado propio de Stratos — nunca inventa nodos o indicadores inexistentes, a diferencia de pedirle a un LLM genérico (Claude/ChatGPT) que alucina indicadores o parámetros.
- **ST-07 — Compilación integrada a MetaTrader 4 / MetaTrader 5.** Un clic ("Compilar") convierte el grafo en código ejecutable listo para MetaTrader, sin que el usuario copie/pegue código ni lo edite en el MetaEditor.
- **ST-08 — Procesamiento local en navegador para datos de mercado sensibles.** En los métodos que usan datos históricos propios del usuario (Diseñador AutoPro, Optimizador AutoPro), el procesamiento pesado ocurre 100% client-side; al servidor solo viaja un resumen de contexto para monitorización de fallos, no el dataset.
- **ST-09 — Datos de mercado propios, "calidad institucional".** La plataforma ofrece históricos de mercado ya cargados (ej. EUR/USD), presentados como supervisados/revisados uno a uno por el equipo, como alternativa a que el usuario suba su propio CSV.
- **ST-10 — Transparencia / no-caja-negra como principio de diseño explícito.** En cada método generado por IA, la plataforma muestra explícitamente la lógica, ficha de estrategia, nodos y conexiones antes de operar — se declara varias veces como principio contrario a "código que no entiendes pero en el que confías tu dinero".

### B. Método 1 — Biblioteca de bots

- **ST-11** Catálogo público de estrategias completas (nodos + conexiones) curadas por el equipo de Stratos, importables al canvas en un clic.
- **ST-12** Filtros de biblioteca por: plataforma (MT4/MT5), mercado, frecuencia/timeframe, **régimen de mercado**, y **exponente de Hurst** (filtro explícitamente reivindicado como no visto en ninguna otra plataforma del sector).
- **ST-13** Ficha/perfil analítico por bot: tendencia, complejidad, riesgo, robustez. Se aclara explícitamente que **este perfil se calcula analizando el diseño/grafo del bot (una "radiografía" estructural), no es un backtest ni una promesa de rendimiento**.
- **ST-14** Disclaimer integrado en la propia UI: "los bots de la biblioteca no son máquinas de imprimir dinero"; requieren optimización antes de llevarse a mercado real.

### C. Método 2 — Wizard (generador de 3 preguntas)

- **ST-15** Flujo de 3 preguntas → bot generado: (1) estilo de trading (scalping/day trading/swing trading), (2) nivel de riesgo (bajo/moderado/alto), (3) hasta 2 familias de indicadores preferidas (ej. tendencia, volumen).
- **ST-16** Tiempo de generación: ~10–60 segundos. Costo: pocos créditos de IA.
- **ST-17** Pipeline interno declarado en 5 pasos: diseña estrategia → genera nodos desde catálogo → conecta indicadores/lógica → conecta lógica a acciones de compra/venta → valida algorítmicamente y auto-repara.
- **ST-18** Complejidad resultante: bots de 1 a 3 indicadores. Se presenta como "prototipo avanzado", boceto funcional pensado para llevar directo a backtest, no como sistema definitivo.

### D. Método 3 — "Bot Legendario" (investigación + generación en cadena)

- **ST-19** Arquitectura de **dos IAs encadenadas**: una IA de investigación busca en internet en tiempo real estrategias de trading reales/documentadas y rentables ajustadas a las preferencias del usuario; una segunda IA (especializada en trading, con conocimiento del catálogo de Stratos) construye el bot a partir de esa investigación.
- **ST-20** 5 dimensiones de configuración (más que el Wizard): estilo de trading, condición de mercado, tipo de estrategia, timeframe, nivel de riesgo.
- **ST-21** Costo: 4 créditos. Tiempo: 1–3 minutos (más lento que el Wizard por la fase de investigación web).
- **ST-22** Al terminar, entrega una "ficha de estrategia": nombre, descripción y lógica de la estrategia encontrada/aplicada — explícitamente para que el usuario entienda la base del bot antes de llevarlo a mercado.
- **ST-23** Mayor complejidad resultante: 3, 5 y hasta 8+ capas de lógica, filtros de sesión, filtros de volatilidad, gestión de riesgo avanzada.
- **ST-24** "Fuerza diversidad": cada generación parte de una semilla aleatoria, por lo que repetir el método con las mismas preferencias da una estrategia distinta cada vez.
- **ST-25** Warning explícito en la UI sobre posibles errores de la IA (nodo huérfano, conexión incorrecta) y obligación del usuario de supervisar antes de operar.

### E. Método 4 — "Diseñador AutoPro" (data-driven, sin preguntas de preferencia)

- **ST-26** Input: CSV propio del usuario o selección de un mercado ya disponible en Stratos (ej. EUR/USD, timeframe 1h).
- **ST-27** Pipeline de **9 pasos visibles** (sin caja negra), 100% client-side salvo un resumen de contexto para monitorización.
- **ST-28** Clasificación automática del histórico en **7 "climas de mercado"**: tendencia alcista, tendencia bajista, rango, ruptura, alta volatilidad, baja volatilidad, momentum.
- **ST-29** Selección automática de una estrategia distinta por cada régimen detectado, desde un catálogo profesional pre-validado de "cientos de estrategias".
- **ST-30** Nodo **"Smart Router"**: enruta dinámicamente entre las estrategias por-régimen según el régimen de mercado detectado en tiempo real (metáfora: caja de cambios automática). Resultado declarado como "bot dinámico/adaptativo", en contraste con bots estáticos de una sola estrategia fija.
- **ST-31** Optimización en paralelo (hasta 16 procesos, según potencia del hardware del cliente) + backtest sobre el histórico completo.
- **ST-32** Validación **anti-overfitting por umbrales configurables**: ej. Profit Factor mínimo 1.1, Drawdown máximo 30% (parametrizable). Si una estrategia candidata no supera el umbral, se descarta y se reintenta con otra — nunca se entrega un diseño que no pase el filtro.
- **ST-33** Opciones avanzadas mencionadas (no explicadas a fondo en esta transcripción — pendiente si aparecen en el resto del vídeo o en el segundo vídeo): **"Wall4Wall"** (nombre tal cual se oye/transcribe, podría ser "walk-forward" mal transcrito) y **validación Montecarlo**.
- **ST-34** ⚠️ Cifras de demo mostradas: Profit Factor 7.2, Drawdown 0.2%, Winrate 92.1%, 38 trades — ver nota crítica en §4, son sospechosamente altas para un ejemplo que se presenta como "anti-overfitting".

### F. Método 5 — Chat de IA "ingeniero cuantitativo"

- **ST-35** Dos modos de chat: **modo asistente** (dudas rápidas) y **modo ingeniero** (diseña y construye bots completos por conversación en lenguaje natural, ej. una instrucción con EMA 50/200, filtro ADX>25, SL en 2×ATR, TP 1:1.5).
- **ST-36** La respuesta del chat no es texto libre: es un diseño estructurado — lista de nodos exactos del catálogo, diagrama de conexiones cable-a-cable, parámetros sugeridos, diagrama de flujo.
- **ST-37** Exportación del diseño a **PDF descargable** con toda la lógica, indicadores, nodos, conexiones y parámetros explicados — documento de referencia del bot, independiente de la plataforma.
- **ST-38** Botón "Construyelo" materializa el diseño del chat directamente en el canvas (sin costo de crédito adicional sobre lo ya conversado); de ahí, un clic más para compilar a MetaTrader.
- **ST-39** **Iteración conversacional incremental**: se puede pedir un cambio puntual (ej. "añade un trailing stop basado en ATR") y el sistema actualiza el diseño existente conservando todo lo anterior, en vez de regenerar desde cero.
- **ST-40** Posicionamiento explícito frente a usar Claude/ChatGPT genérico para lo mismo: el chat de Stratos solo usa nodos reales de su catálogo (lista blanca) con validación automática y reparación de errores estructurales; un LLM genérico "alucina" indicadores/parámetros inexistentes y no construye ejecutable, solo un boceto en texto.
- **ST-41** Mención de un **"Copilot IA"** distinto y más avanzado, que sí "ve" el estado actual del canvas del usuario y construye colaborativamente paso a paso — explícitamente diferido a "otro vídeo", no cubierto en esta transcripción.

### G. Método 6 — Optimizador AutoPro (cómputo puro, sin IA) — *parcialmente capturado*

- **ST-42** Se abre por clic derecho sobre un bot ya existente en el canvas ("Optimizador AutoPro").
- **ST-43** Mismo patrón de carga de datos que el Diseñador AutoPro: CSV propio o mercado precargado.
- **ST-44** Tres garantías declaradas: (1) costo cero créditos — no usa IA, es "computación pura en tu navegador"; (2) procesamiento 100% client-side, el dataset no sale de la máquina; (3) cero configuración manual — un clic y arranca.
- **ST-45** Detección automática de qué parámetros del bot merece la pena optimizar (vs. barrer todos los parámetros posibles a ciegas, lo que el narrador llama "arqueología de trading").
- **ST-46** Se atribuye la selección inteligente de parámetros a que Stratos "es dueño" del catálogo de nodos (los crearon ellos), por lo que tiene criterio sobre qué rango de cada parámetro es razonable optimizar, a diferencia de un optimizador genérico que probaría combinaciones sin ese contexto.
- **[CORTE DE TRANSCRIPCIÓN AQUÍ — ST-47 en adelante pendiente del resto del vídeo o de una fuente alternativa.]**

---

## 3. Terminología / conceptos propios de Stratos (glosario para no perder matices al comparar)

| Término Stratos | Qué es según el transcript |
|---|---|
| Canva | El lienzo/canvas de edición visual de nodos |
| Wizard | Método 2, generador de 3 preguntas |
| Bot Legendario | Método 3, generación en 2 IAs (investigación + construcción) |
| Diseñador AutoPro | Método 4, diseño multi-régimen desde histórico |
| Optimizador AutoPro | Método 6, optimización de parámetros sin IA |
| Smart Router | Nodo que enruta entre estrategias por régimen de mercado detectado |
| Climas de mercado / regímenes | 7 categorías: tendencia alcista, tendencia bajista, rango, ruptura, alta volatilidad, baja volatilidad, momentum |
| Exponente de Hurst | Métrica de "memoria del precio": >0.5 tendencial, <0.5 reversión a la media |
| Créditos de IA | Moneda interna consumida por acciones que invocan modelos de IA |
| Copilot IA | Asistente distinto al chat "ingeniero", con visión del estado del canvas (mencionado, no explicado) |

---

## 4. Lectura crítica (no solo inventario — juicio de trader/ingeniero)

- **Las cifras del Diseñador AutoPro (ST-34) son una bandera roja, no una prueba de calidad.** Profit Factor 7.2 / Drawdown 0.2% / Winrate 92.1% en solo 38 trades es exactamente el patrón de sobreajuste que el propio narrador pasa media transcripción advirtiendo que hay que evitar. 38 trades es una muestra estadísticamente débil para sostener ninguna de esas métricas, y una combinación PF/DD/WR tan extrema en una demo de producto es más coherente con "se enseña el mejor resultado de varias corridas" que con un caso representativo. Esto no invalida el mecanismo (los umbrales anti-overfitting de ST-32 son una idea sólida), pero sí el ejemplo usado para venderlo.
- **La "validación estructural" (ST-05, ST-06, ST-17, ST-25) es distinta de "validación de mercado".** Repetidamente el propio narrador aclara que el perfil de un bot (ST-13) es una "radiografía de construcción", no una promesa de rendimiento — es una distinción honesta que vale la pena igualar en cualquier discurso de Luarix: no mezclar "el grafo es válido" con "la estrategia es rentable".
- **El diferenciador real frente a "pedirle a Claude/ChatGPT" (ST-40) es el mismo argumento de fondo que ya usa Luarix** en el documento institucional (§12.1: "copiloto que cuestiona antes de construir", "sincronización bidireccional lenguaje↔visual", "sin dos fuentes de verdad que puedan divergir") — Stratos lo resuelve con una lista blanca de nodos + auto-reparación estructural; Luarix lo resuelve con Luis + editor de flujos sincronizados. Son soluciones distintas al mismo problema (evitar que un LLM genérico alucine).
- **Todo lo que sabemos de Stratos es auto-reportado en un vídeo promocional de su propio creador.** No hay cifras de usuarios, facturación, ni review independiente — a diferencia de las filas de la tabla §12.5 de Luarix (eToro, FTMO, 3Commas, etc.), que sí tienen fuente externa. Cualquier comparación de "quién es mejor" debe tratar a Stratos como una demo de producto, no como un dato de mercado verificado.

---

## 5. Mapa rápido Stratos → Luarix (solapes y huecos)

No sustituye al Capítulo 12 del documento institucional de Luarix (`docs/luarix_documento_institucional.md`); es una nota de trabajo para decidir si conviene ampliar esa tabla comparativa con Stratos como fila nueva.

| Capacidad | Stratos | Luarix hoy |
|---|---|---|
| Construcción por lenguaje natural | Sí (chat "ingeniero", ST-35–41) | Sí (Luis) |
| Editor visual de nodos | Sí (Canva) | Sí (editor de flujos) |
| Sincronización bidireccional lenguaje↔visual | Parcial — el chat "construye" al canvas pero se aclara que **no ve** el estado actual del canvas (ST-41); eso lo reserva para el "Copilot IA" no cubierto aún | Sí, explícitamente bidireccional (§12.1) |
| Biblioteca de estrategias importables | Sí, con filtros por régimen/Hurst (ST-11–14) | No confirmado en el documento institucional revisado — punto a verificar |
| Multi-régimen con enrutador dinámico | Sí (Smart Router, ST-28–30) | No confirmado — punto a verificar contra el motor SMC de Luarix |
| Anti-overfitting con umbrales configurables | Sí (ST-32) | No confirmado — punto a verificar |
| Optimización de parámetros sin IA (client-side) | Sí (Método 6, ST-42–46) | No confirmado — punto a verificar |
| Exportación/compilación a MetaTrader | Sí (ST-07) | No es el enfoque de Luarix descrito en el documento institucional (que no menciona MT4/MT5 como target de compilación) |
| Procesamiento client-side de datos sensibles | Sí, declarado (ST-08, ST-27, ST-44) | No confirmado — punto a verificar |
| Gobierno de riesgo estructural obligatorio (kill switch, paper trading forzado) | No mencionado en esta transcripción | Sí, explícito y no opcional (§12.1, Cap. 7) |
| Motor de estructura de mercado (SMC) propio | No mencionado — el enfoque de Stratos es indicadores clásicos + régimen estadístico (Hurst, climas de mercado), no liquidez/order blocks | Sí, núcleo diferenciador de Luarix (§12.4) |
| Auditoría por nodo + contexto de mercado en cada señal | No mencionado con ese nivel de detalle | Sí, explícito (§12.1) |

**Lectura:** Stratos parece más fuerte en *ergonomía de generación* (6 caminos distintos hacia un bot, desde 1 clic hasta chat conversacional) y en *optimización/validación estadística multi-régimen* de forma muy visual. Luarix parece más fuerte en *gobierno de riesgo obligatorio* y en *metodología de señal* (SMC/liquidez vs. indicadores clásicos + régimen). Antes de sacar conclusiones firmes falta: el resto del Método 6, el segundo vídeo, y confirmar contra el documento institucional si Luarix ya cubre biblioteca/multi-régimen/optimización client-side (marcado "no confirmado" arriba porque no se revisó el código fuente de Luarix en esta sesión, solo el documento institucional).

---

## 6. Pendientes para cerrar el análisis

1. Transcripción o descripción del contenido del segundo vídeo (`Vgmo3mxDOmM`, desde el minuto ~25:30).
2. Resto del Método 6 (Optimizador AutoPro) y cualquier cierre/bonus del primer vídeo.
3. Confirmación visual (capturas) de al menos: la ficha de perfil de bot (ST-13), el grafo con Smart Router (ST-30), y el PDF exportado del chat ingeniero (ST-37) — para verificar que la lectura del texto coincide con la UI real.
4. Decidir si este análisis se traslada como fila nueva a la tabla comparativa del Capítulo 12 del documento institucional de Luarix, una vez esté completo.
