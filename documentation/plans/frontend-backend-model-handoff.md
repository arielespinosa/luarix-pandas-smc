# Traspaso frontend → backend: qué necesita `luarix-web-client` de `luarix_rest_api`

> Documento de contexto para quien construya los modelos Django de `luarix_rest_api`.
> No es una spec de API ni una propuesta de campos — es el mapa de dominio que hoy
> vive **solo en el frontend** (Next.js, `luarix-web-client`), para que el diseño de
> modelos en Django se haga con criterio y no a ciegas.

## 1. Resumen ejecutivo

Hoy conviven, sirviendo al mismo frontend Next.js, **dos backends**:

1. **Un servidor FastAPI** (`fastapi_server/`, dentro de `nexora-trading-framework`) que
   calcula indicadores técnicos y de Smart Money Concepts (SMC) sobre velas, de forma
   **stateless** (no tiene base de datos — los catálogos de providers/intervals/indicadores
   están hardcodeados en `fastapi_server/catalog/`). Usa `pandas_luarix` para el cómputo.
2. **`luarix_rest_api`** (Django REST Framework), en construcción, pensado para
   persistencia, autenticación y (a futuro) tareas asíncronas — ya tiene Celery+Redis y
   Django Channels configurados en `settings.py`, aunque sin uso real todavía.

Esto **no es un monolito puro hoy**: ya es una arquitectura de dos servicios. La pregunta
del usuario ("¿debería el workflow ser una app aparte?") aplica sobre este trasfondo: ya
existe precedente de separar por responsabilidad (cómputo de indicadores vs persistencia),
así que separar "ejecución de estrategias" en un tercer servicio no sería un salto raro.

El frontend, mientras tanto, tiene construidas **muchísimas pantallas y flujos** sobre
datos mock (arrays en `lib/*-data.ts`) y `localStorage` — nada de esto tiene todavía un
backend real detrás, excepto:
- el gráfico de `/markets/chart`, que sí habla con el FastAPI real (candles + indicadores), y
- el AI Copilot ("Luis"), que habla directo con la API de Anthropic desde una route de
  Next.js (no pasa por ningún backend Python).

Las tres decisiones más importantes que quedan abiertas (detalladas en la sección 4):

- **(a)** Si "ejecutar" los grafos de estrategia del builder (`StrategyGraph`) va a vivir
  como una app más del monolito Django o como servicio aparte.
- **(b)** Que `Strategy` significa **dos cosas distintas** hoy: un bot de trading en el
  frontend (pnl, win rate, config de DCA) vs. un ancla de contexto IPDA en Django
  (`strategies.Strategy`: symbol, capital, fractal, side). Hace falta reconciliar esto
  explícitamente, no asumir que ya son lo mismo.
- **(c)** Si Django va a terminar sirviendo el chart de indicadores (reemplazando a
  FastAPI) o si FastAPI se queda como motor de cómputo y Django solo persiste
  historial/config de las corridas.

## 2. Inventario de dominio del frontend

### 2.1 Constructor visual de estrategias ("Strategy Builder")

Es la pantalla más compleja del frontend: un canvas de nodos y conexiones (usando
`@xyflow/react`), donde el usuario arma una estrategia de trading arrastrando bloques.

- El modelo de datos central es un **grafo**: `StrategyGraph = { id, name, nodes, edges, version }`,
  donde cada `GraphNode` tiene `id`, `type` (referencia a un tipo del catálogo), `position`,
  `config` (un diccionario de parámetros propio de ese tipo de nodo) y `label`; y cada
  `GraphEdge` conecta un puerto de salida de un nodo con un puerto de entrada de otro.
  Ver `lib/ai-copilot/graphAdapter.ts` y `lib/builder-graph-ops.ts`.
- Existe un **catálogo de más de 19 categorías de nodos** (`lib/builder-nodes.ts`, ~4000
  líneas): eventos, control de flujo, datos de mercado, indicadores, estructura de
  mercado, smart money, estrategia, ejecución, riesgo, datos, procesamiento, IA, APIs,
  backtesting, optimización, código, debug, visualización, notificaciones. Cada tipo de
  nodo define su propio esquema de parámetros (`NodeParam[]`) — este catálogo es, en la
  práctica, el "lenguaje" en el que están escritas todas las estrategias que arme un
  usuario, y ese mismo catálogo se reutiliza tal cual para construir las herramientas
  (tool schemas) que usa el AI Copilot para editar el grafo.
- **Hoy nada de esto se ejecuta de verdad contra un mercado real.** Lo único que existe es
  un backtester **client-side** (`lib/backtest/simulator.ts`) que interpreta un subconjunto
  chico del catálogo (indicadores tipo EMA/SMA/RSI/MACD y el primer par de nodos
  entry-condition/exit-condition) sobre velas sintéticas generadas localmente; todo lo que
  cae en las categorías riesgo/ejecución/notificaciones/almacenamiento se trata como una
  acción simulada que solo queda logueada, explícitamente porque "correr una orden real
  necesita estado de cuenta y conectividad con el exchange que todavía no existe."
- **Persistencia hoy**: el grafo se guarda en `localStorage` bajo la clave
  `luarix:strategy-graph:<strategyId>`, a través de una interfaz `StrategyRepository` con
  métodos `load`/`save` — está deliberadamente shaped como un futuro
  `GET/PUT /strategies/{id}/graph`. Esto es exactamente el tipo de dato que no tiene
  ningún modelo Django hoy y que necesita uno si se quiere persistencia real de grafos.

### 2.2 AI Copilot ("Luis")

Un asistente conversacional embebido en el builder que puede leer y modificar el grafo de
estrategia. Vive enteramente en el frontend hoy: `app/api/ai-copilot/route.ts` es una route
de Next.js que llama directo a la API de Anthropic (streaming, tool-calling), sin pasar por
ningún backend Python.

- Tiene dos modos: **planner** (solo puede preguntar/analizar, no puede tocar el grafo —
  esto está bloqueado a nivel de qué tools se le exponen, no solo por prompt) y **executor**
  (tiene el set completo de tools: crear nodo, conectar, actualizar config, borrar nodo,
  mover nodo, validar grafo).
- El modo planner aplica una **rúbrica de 12 dimensiones de trading** (tesis de edge,
  verificabilidad, dependencia de régimen, confluencia real vs. redundante, cantidad de
  parámetros libres, look-ahead bias, lógica de invalidación/stop, sizing como
  preocupación separada, costos de fricción, win-rate/RR poco realista, overfitting
  retroactivo, ejecutabilidad contra el catálogo real de nodos) antes de dejar avanzar a
  construir nada — cada punto se clasifica como bloqueante/relevante/menor.
- Las **sesiones de chat** (`ChatSession`: id, title, createdAt, messages) se guardan hoy en
  `localStorage`, una lista por estrategia. Esto tampoco tiene modelo Django — si se
  quiere que el historial de conversación con el copiloto sobreviva entre dispositivos,
  hace falta persistirlo del lado del servidor.
- **"IPDA Strategy" / "cerebro analista trader de Luis"** no es un tipo de dato separado:
  es contenido de prompt/rúbrica (`traderRubric.ts`) que el copiloto aplica de forma
  genérica a cualquier estrategia que el usuario describa, usando las herramientas
  genéricas del grafo. No hay ("ni debería inventarse") un modelo "IPDA" en el frontend.

### 2.3 Estrategias/bots (concepto frontend de `Strategy`)

**Importante**: esto es distinto del contexto IPDA. En el frontend, un `Strategy` es un bot
de trading con: nombre, descripción, exchange, par, `status` (`live`/`paused`/`draft`/`backtest`),
pnl% y valor, win rate, total de trades, timeframe, tags, y una `config` de tipo DCA
(tamaño de orden base, safety orders, take profit %, stop loss %, máximo de posiciones
abiertas). El comentario en el código es explícito: **"una estrategia ES un solo bot: posee
una automatización, una config y una posición en vivo."**

### 2.4 Alertas y notificaciones (dos dominios separados, no confundir)

- **Alertas** (`AlertRule`/`AlertHistoryEntry`): reglas configurables por estrategia
  (tipo precio/indicador/error, condición, canal de notificación, on/off) más un historial
  de disparos con severidad (info/warning/critical). Hoy son mocks estáticos — no hay
  camino de escritura implementado en el frontend todavía.
- **Notifications** (feed de la topbar): `NotificationItem` con categoría (`fill` /
  `strategy-alert` / `market`), título, cuerpo, timestamp, leído/no leído, link opcional.
  Es la bandeja de actividad, conceptualmente separada de las reglas de alerta.
- `luarix_rest_api` ya tiene `django-notifications-hq` instalado en `INSTALLED_APPS` pero
  sin ningún uso todavía — hay que decidir si ese paquete sirve para el feed, para el
  historial de alertas, para ambos, o para ninguno (ver sección 4d).

### 2.5 Mercados / instrumentos

`Market` (símbolo, nombre, par, precio, cambios 24h/1h/7d, high/low 24h, volumen, market
cap, si está en watchlist, mini-serie para sparkline). No existe ningún catálogo
normalizado de instrumentos en Django hoy — ni FastAPI ni Django tienen un modelo real de
"mercado/instrumento" con metadata (exchange, clase de activo, tick size, precisión); todo
lo que existe hoy son catálogos hardcodeados en el código FastAPI o arrays mock en el
frontend.

### 2.6 Correlación, noticias y sentimiento

- **Correlación**: una matriz N×N de coeficientes entre una lista fija de símbolos
  (BTC, ETH, SOL, BNB, XRP, ADA, AVAX, LINK, DOGE), hoy escrita a mano, no calculada.
- **Noticias**: artículos con título, fuente, URL, fecha, sentimiento (bullish/bearish/
  neutral), símbolos relacionados. El propio comentario del código dice que esto
  "solo existe como mock" a propósito, por lo inestables/no documentados que son los feeds
  de noticias disponibles.
- **Sentimiento (Fear & Greed)**: un score con etiqueta (Extreme Fear…Extreme Greed) y
  sub-scores (momentum, volatilidad, dominancia, volumen).

Ninguno de los tres tiene cobertura alguna en Django ni en FastAPI hoy.

### 2.7 Backtesting

`BacktestResult` (lista de trades, win rate, pnl total %, max drawdown %, un "sharpe-like",
curva de equity, log de texto) — hoy corre 100% client-side (ver 2.1) y se persiste en
`localStorage`. Esto **sí tiene un equivalente razonable en Django** (`backtesting.BacktestRun`
+ `Trade` + `TradeEvent`, con ~25 métricas resumen que ya mapean casi 1:1 contra
`BacktestResult`) — el trabajo pendiente es conectar el motor real (no el simulador de
juguete del frontend) a esos modelos, y decidir qué pasa con las categorías de nodos que
hoy son no-ops simulados (riesgo, ejecución, notificaciones, storage).

### 2.8 Portfolio, marketplace, copy-trading, settings, academy

- **Portfolio**: holdings (símbolo, cantidad, precio, valor, allocation, cambios, pnl),
  resumen de portfolio, curva de equity, exchanges conectados (con estado
  connected/error/syncing), historial de transacciones (buy/sell/deposit/withdraw/fee).
- **Marketplace**: estrategias publicadas por otros usuarios para "comprar"/suscribirse
  (nombre, categoría, precio, rating, reviews, suscriptores, retornos, drawdown, tags) más
  reviews.
- **Copy-trading**: perfiles de traders para copiar (retorno, win rate, drawdown, risk
  score, copiadores, AUM), relación de "a quién sigo" y "copias activas" (cuánto asigné,
  pnl, desde cuándo).
- **Settings**: perfil de usuario (nombre, email, avatar, rol, timezone), preferencias de
  notificación por canal, **API keys** (con scopes tipo `strategies:read`,
  `strategies:execute`, `portfolio:read`, `backtests:run` — esto es una pista fuerte de
  cómo debería verse el control de acceso de una API key real), sesiones activas por
  dispositivo, y planes de suscripción (free/starter/professional/business/enterprise).
- **Academy**: tutoriales — puramente decorativo hoy, sin ningún dato real detrás.

Ninguna de estas áreas tiene modelo Django hoy.

### 2.9 Auth actual (no apto para producción)

El login de hoy es un **stub de demo de un solo usuario**: credenciales hardcodeadas
(override por variable de entorno), sin tabla de usuarios, sesión firmada con HMAC-SHA256
(no JWT) en una cookie httpOnly de 7 días, y la autenticación se **desactiva por completo**
fuera del entorno "cloud" (en dev local, cualquier request pasa sin login). Esto no tiene
ninguna relación con `security.User` de Django (que sí es un modelo real, extiende
`AbstractUser` + avatar) — hay que construir desde cero el cliente real de auth en el
frontend (login contra un endpoint Django, manejo de JWT/refresh, etc.), no adaptar lo que
existe hoy.

### 2.10 Contrato de indicadores/candles hacia FastAPI

Esta es la parte más formalizada y madura que existe hoy (documentada en
`docs/markets-chart-elements-contract.md` del frontend, verificada directamente). El
frontend solo sabe dibujar **5 tipos de objeto geométrico** sobre el chart:

| `kind` | Qué es | Geometría |
|---|---|---|
| `marker` | un punto sobre una vela | `time`, `price` |
| `line` | un segmento entre 2 puntos | `time1,price1` → `time2,price2` |
| `box` | un rectángulo | `time1,price1` → `time2,price2` (+ `direction` opcional) |
| `line_series` | una línea multi-vela | `data: [{time, value}]` |
| `multiline_series` | N líneas multi-vela | `lines: [{key, label, data}]` |

Hoy, el FastAPI expone 14 endpoints (`/indicators/swings`, `/indicators/bos-choch`,
`/smc/fair-value-gaps`, `/smc/fractal`, `/analysis/divergence`, etc.) que devuelven filas
crudas por vela con nombres de campo propios de cada indicador, y el frontend hace la
conversión a estas 5 formas **del lado del cliente** (`lib/luarix-api/structure-shapes.ts`).
**El estilo visual (color, grosor, relleno) nunca viaja del backend — es 100% preferencia
del usuario, resuelta en el cliente.**

Este contrato importa para Django porque los modelos ya existentes en la app `indicators`
(`Swing`, `StructureEvent`, `OrderBlock`, `LiquiditySweep`, `FairValueGap`, `SwingFractal`,
`Divergence`) están escritos como **espejo de las dataclasses de la capa Python/Pine
legacy** (los comentarios en el código dicen literalmente "Mirror de..."), no todavía
pensados para serializarse directo en esta forma de 5 objetos. Si Django llega a servir el
chart, hace falta una capa de traducción — no algo automático.

## 3. Comparación con lo que ya existe en `luarix_rest_api`

Apps Django ya existentes: `core` (abstracciones compartidas: `TimestampedModel`,
`OwnedModel`, choices comunes), `security` (`User`), `brokers` (`BrokerAccount`, `Order`,
`Fill`, `Position`), `strategies` (`Fractal`, `Strategy`, `ConditionType`, `Condition`),
`indicators` (todo lo de SMC/clásico/análisis + sus *Config + `DetectionRun`),
`backtesting` (`BacktestRun`, `Trade`, `TradeEvent`). Serializers/views/urls están vacíos
en las seis — todo el trabajo hecho hasta ahora es de modelos, tal como dijo el usuario.

**Bien cubierto conceptualmente** (el modelo Django ya existe y el concepto del frontend
encaja razonablemente, aunque falta la capa de API):
- `indicators.*` ↔ el contrato de indicadores del builder/chart (con la salvedad de la
  traducción a las 5 formas, sección 2.10).
- `brokers.*` ↔ conexión a exchanges, órdenes, fills, posiciones (sección 2.8 portfolio y
  ejecución real del builder, sección 2.1).
- `backtesting.*` ↔ `BacktestResult` (sección 2.7), con trabajo pendiente de reemplazar el
  motor de simulación de juguete del frontend por algo real.

**Colisión de nombre a resolver explícitamente, no asumir resuelta**:
- `strategies.Strategy` (Django) = symbol, capital, fecha de inicio, side, is_active.
  **Ya NO tiene el FK `fractal`** (removido — IPDA no es un tipo/atributo especial de
  Strategy, es una instancia más; el contexto macro/fractal ahora se configura en el
  propio nodo del grafo, ver `workflows/execution/nodes/risk.py::FractalKillSwitchExecutor`
  y el param `high`/`low` del `NodeDefinition` "fractal").
- `Strategy` (frontend, sección 2.3) = un bot de trading con pnl/win rate/config DCA/tags.
- Siguen siendo dos conceptos distintos que comparten nombre — esa parte de la decisión
  sigue abierta (no se resolvió acá, fue deliberadamente fuera de alcance). Probablemente
  el modelo correcto sea algo como "un `strategies.Strategy` de Django puede tener 0..N
  bots/automatizaciones corriendo con esa configuración", pero eso sigue siendo una
  decisión de diseño pendiente, no algo para asumir.

**Sin cobertura en absoluto** (requieren app(s)/modelos nuevos, sin propuesta de campos
aquí — queda a criterio del agente de backend, siguiendo el estilo ya usado en el repo:
`OwnedModel`/`TimestampedModel`, `TextChoices`, una app por dominio):
- Persistencia del grafo del builder (`StrategyGraph`: nodes/edges/config por nodo).
- Sesiones de chat del AI Copilot.
- Catálogo de mercados/instrumentos.
- Alertas (reglas + historial) y feed de notificaciones (dos dominios separados).
- Correlación entre símbolos.
- Noticias + sentimiento de mercado.
- Marketplace de estrategias publicadas + reviews.
- Copy-trading (perfiles de traders, following, copias activas).
- Portfolio (holdings, resumen, exchanges conectados, transacciones).
- Settings de usuario: perfil real, API keys (con scopes), sesiones activas por
  dispositivo, planes de suscripción.

**Auth**: `security.User` es un punto de partida razonable (extiende `AbstractUser` +
avatar), pero como se explica en 2.9, el frontend no tiene hoy ningún cliente real de
JWT/sesión — esa integración se construye desde cero, no se "conecta" a algo existente.

## 4. Decisiones de arquitectura abiertas

Estas cuatro decisiones cambian el diseño de modelos resultante — vale la pena que el
usuario las revise/confirme antes de que el agente de backend arranque a construir las
áreas nuevas de la sección 3.

### 4a. ¿Ejecución de `StrategyGraph` (workflow) como app del monolito o servicio aparte?

No hay ningún acoplamiento existente a n8n que condicione esta decisión — se verificó
explícitamente que **no existe ninguna integración real con n8n** en ningún lado del
frontend ni del backend; las únicas menciones son comentarios de inspiración de UX
("n8n-style floating action rail") y documentación de producto que dice literalmente que
Luarix no pretende sustituir a n8n. Así que el formato de wire de n8n no es una restricción
a respetar.

Requisitos mínimos que cualquiera de las dos opciones (app Django vs. servicio separado)
tiene que cumplir, sin importar cuál se elija:
- Persistir y versionar un `StrategyGraph` por estrategia (hoy vive solo en `localStorage`).
- Poder disparar un backtest sobre ese grafo y devolver algo shape-compatible con
  `backtesting.BacktestRun`.
- Soportar transición de estados `draft → backtest → live → paused` (el `status` que ya
  existe en el `Strategy` del frontend, sección 2.3).
- Eventualmente, interpretar de verdad las categorías de nodos que hoy son no-ops
  simulados (riesgo, ejecución, notificaciones, storage) contra `brokers.*` real.

Trade-off, sin inclinar la balanza: empezar como app Django dentro del monolito es más
simple de iterar mientras el catálogo de nodos sigue cambiando rápido (sigue siendo el
área más nueva del frontend); separarlo desde ya como servicio evita tener que migrar
un motor de ejecución con estado (posiciones, órdenes en vuelo) fuera del monolito más
adelante, que suele ser más doloroso que separar código sin estado.

### 4b. Reconciliar el nombre `Strategy` duplicado

Ver sección 3. Sigue sin resolverse (¿son dos modelos con nombres distintos? ¿uno
contiene al otro?) — lo único que se corrigió fue quitar el FK `fractal` de
`strategies.Strategy`, porque modelaba IPDA como si fuera un atributo/tipo especial de
Strategy en vez de una instancia más (el contexto macro ahora vive en el grafo, como
nodo). Esa corrección puntual no resuelve la colisión de nombre en sí, que sigue siendo
una decisión de diseño pendiente antes de seguir tocando la app `strategies` de Django.

### 4c. ¿Django reemplaza a FastAPI para servir el chart, o FastAPI se queda como motor de cómputo?

Los modelos de `indicators` ya persisten `DetectionRun` (corridas de detección con config
snapshot, estado, timestamps) — eso sugiere que la intención original era que Django
guardara historial de corridas, no necesariamente que sirviera el contrato de 5 formas en
vivo. Pero nada impide que, a futuro, una serializer de Django devuelva directamente
`{"elements": [...]}` sobre los modelos ya persistidos, reemplazando a FastAPI para ese
endpoint. Ninguna opción está descartada por el código actual; es una decisión pendiente.

### 4d. Encaje de `django-notifications-hq` con "Notifications" (feed) y "Alerts" (reglas)

El paquete ya está en `INSTALLED_APPS` pero sin ningún uso todavía. En el frontend son dos
dominios separados (sección 2.4): reglas de alerta configurables vs. feed de actividad.
Hay que decidir si comparten el mismo backend (p. ej., un disparo de alerta genera una
notificación en el feed) o si son dos sistemas independientes.

### Nota aparte — posible venv desincronizado (no bloqueante para el diseño de modelos, pero si bloquea correr el proyecto)

`luarix_rest_api/luarix_rest_api/settings.py` referencia en `INSTALLED_APPS` varios
paquetes (`rest_framework`, `rest_framework_simplejwt` + `token_blacklist`, `corsheaders`,
`django_filters`, `django_celery_beat`, `notifications`) que **no aparecen** en el
`requirements.txt` de `nexora-trading-framework` ni en el venv (`env/Lib/site-packages`)
verificado durante esta exploración — solo están `celery` y `channels` "pelados". Las
migraciones ya existen y se ven completas para las 6 apps, así que probablemente se
generaron en un entorno distinto (o los paquetes se desinstalaron después). Vale la pena
que el usuario lo confirme antes de que el agente de backend intente correr
`migrate`/`runserver`, para no perder tiempo debuggeando un `ImportError` que no tiene que
ver con el diseño de modelos. (También se encontró que `EXCEPTION_HANDLER` en
`REST_FRAMEWORK` apunta a `apps.security.exceptions.exception_404_handler`, una ruta que no
existe en este proyecto — probablemente residuo de una plantilla o de otro proyecto.)

## 5. Requisitos funcionales por área nueva (sin proponer campos)

Para cada área listada como "sin cobertura" en la sección 3, esto es lo que el frontend
necesita poder hacer contra el backend — el diseño concreto de modelos (campos, choices,
relaciones exactas) queda a criterio del agente de backend, siguiendo el estilo ya
establecido en el repo:

- **Grafo de estrategia (builder)**: guardar/reemplazar el grafo completo de una
  estrategia; versión incremental (ya existe un campo `version` en el tipo frontend);
  quién es el dueño (relación con `strategies.Strategy` o con el bot, según se resuelva 4b).
- **Sesiones de chat del AI Copilot**: una lista de sesiones por estrategia, cada una con
  mensajes ordenados y su rol (user/assistant); no necesita relacionarse con nada más que
  la estrategia y el dueño.
- **Mercados/instrumentos**: catálogo de símbolos con metadata de exchange/tipo de activo;
  probablemente compartido entre el módulo de mercados y el de portfolio/órdenes (mismo
  símbolo referenciado desde varios lados).
- **Alertas**: reglas (pertenecen a una estrategia, tienen tipo y condición evaluable,
  canal de notificación, on/off) + historial de disparos (con severidad y mensaje,
  encadenado a la regla y/o a la estrategia).
- **Notificaciones (feed)**: eventos de distintas categorías (fill de orden, alerta de
  estrategia, evento de mercado) por usuario, con estado leído/no leído.
- **Correlación**: una forma de calcular/servir una matriz de coeficientes entre un
  conjunto de símbolos (fijo o dinámico).
- **Noticias**: artículos con fuente, fecha, sentimiento etiquetado, símbolos
  relacionados — necesita algún pipeline de ingesta, no solo el modelo.
- **Sentimiento de mercado**: un score periódico con sub-componentes.
- **Marketplace**: estrategias publicadas (por un usuario/autor) con métricas de
  performance, precio, rating; reviews asociadas a una estrategia publicada y a un autor
  de review.
- **Copy-trading**: perfil público de trader con métricas; relación de "seguir" entre
  usuarios; "copia activa" con monto asignado, pnl y fecha de inicio.
- **Portfolio**: holdings por usuario (o por exchange conectado), resumen agregado,
  exchanges conectados con su estado de sincronización, historial de transacciones.
- **Settings**: perfil de usuario real (más allá de lo que ya da `AbstractUser`), API keys
  con scopes granulares (los scopes vistos en el frontend son una buena referencia:
  `strategies:read`, `strategies:execute`, `portfolio:read`, `backtests:run`), sesiones
  activas por dispositivo, y planes de suscripción con sus límites/highlights.

## 6. Cómo verificar que este documento cumple su propósito

Antes de pasarlo al agente que va a construir los modelos:
1. Confirmar con el usuario las 4 decisiones de la sección 4 (al menos marcar una postura
   inicial, aunque sea reversible) — cambian el diseño resultante.
2. Confirmar la ruta/nombre de archivo del documento con el equipo de backend si van a
   tener su propia convención de dónde viven estos docs de traspaso.
3. Si el agente de backend tiene dudas de campo-a-campo sobre un tipo específico del
   frontend, los archivos fuente citados en cada sección (`lib/*-data.ts`,
   `lib/ai-copilot/*`, `lib/luarix-api/*`, `docs/markets-chart-elements-contract.md`) son
   la referencia autoritativa — este documento resume, no reemplaza esas fuentes.
