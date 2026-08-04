# Luarix — Documento Institucional
### Para socios y clientes

*Documento vivo. Se revisa y amplía capítulo a capítulo conforme el proyecto avanza.*

---

## Doctrina de trabajo del proyecto

Todo lo que se documenta, diseña o construye en Luarix sigue dos criterios simultáneos, sin excepción:

**1. Criterio de trader profesional.**
No se trata de añadir complejidad porque sí. Se trata de que lo que se decida hacer, se haga bien. Calidad no es "hacer todo lo que se nos ocurra", es hacer lo necesario, y hacerlo con rigor: con gestión de riesgo real, con supuestos explícitos, sin promesas que el estado del sistema no pueda respaldar.

**2. Criterio de arquitecto e ingeniero de software.**
Se aplican patrones y principios de diseño, se optimiza y se reutiliza todo lo que sea razonable reutilizar. Ningún componente — ni de código ni de documentación — se duplica si ya existe una fuente de verdad para él.

Estos dos criterios se aplican tanto al código del motor de trading como a este documento institucional: cada capítulo se apoya en el anterior, ningún concepto se redefine dos veces, y ninguna afirmación de alcance se hace sin que el estado real del proyecto la sostenga.

---

## Índice

1. Introducción y Resumen Ejecutivo
2. Visión y Misión
3. Producto: Luarix Hoy
4. Arquitectura de Software (nivel ejecutivo)
5. Alcance del Proyecto — Capacidades de la Versión 1.0
6. Etapas y Hoja de Ruta
7. Gestión de Riesgo y Seguridad
8. Consideraciones Regulatorias y Legales
9. Equipo y Modelo de Colaboración
10. Visión a Futuro
11. Próximos Pasos
12. Innovación y Panorama Competitivo
13. Modelo de Negocio y Líneas Comerciales
14. Conclusiones
15. Referencias

---

## 1. Introducción y Resumen Ejecutivo

### 1.1 Qué es Luarix

Luarix es un sistema de trading algorítmico diseñado para operar con ventaja estadística repetible, no para predecir el mercado. Su núcleo es un motor de trading que separa con disciplina cada decisión del proceso — qué está pasando en el mercado, qué se quiere hacer, cuánto capital arriesgar, si esa operación es segura, y cómo se ejecuta — de forma que ninguna de esas decisiones pueda tomarse de forma aislada o sin control.

Luarix se apoya en dos capacidades centrales:

- Un **motor de trading** capaz de operar en modo simulado (paper trading) y de validar estrategias sobre datos históricos (backtesting) antes de considerar cualquier operación con capital real.
- Un **copiloto de inteligencia artificial, Luis**, que permite construir y razonar sobre estrategias de trading mediante lenguaje natural, actuando como un analista que primero entiende y cuestiona una estrategia antes de construirla.

### 1.2 El problema que resuelve

Existe hoy una brecha entre dos mundos: por un lado, el trading discrecional, manual, expuesto al error humano y la emoción; por otro, la infraestructura quant institucional, que requiere conocimiento técnico, capital y equipos que la mayoría de traders individuales no tiene. Luarix se construye para cerrar esa brecha con un sistema que impone disciplina de forma estructural — no porque el usuario recuerde aplicar una regla de riesgo, sino porque el sistema no permite operar sin haberla evaluado.

### 1.3 Para quién es este documento

Este documento está dirigido a **socios y clientes**: describe qué es Luarix, qué hace, en qué estado se encuentra y hacia dónde va, en un lenguaje libre de detalle de implementación. No cubre arquitectura de código, librerías, estructura de archivos ni decisiones de stack técnico — esa información vive en el documento técnico del proyecto, de uso interno para el equipo de desarrollo.

### 1.4 Estado actual en una frase

Luarix opera hoy como un sistema completo en su versión 1.0: el motor de trading y el copiloto de IA están implementados y en explotación, ejecutando de punta a punta el ciclo descrito en el Capítulo 3 bajo el marco de riesgo del Capítulo 7 — ese marco no es una condición pendiente de cumplir, es el régimen bajo el que el sistema opera en todo momento, sin excepción.

---

*Fin del Capítulo 1.*

---

## 2. Visión y Misión

### 2.1 Visión

Que cualquier persona con criterio de trading —propio o guiado por un copiloto de IA— pueda construir, validar y operar estrategias con el mismo nivel de disciplina que exigiría una mesa de trading institucional, sin necesitar un equipo de ingenieros ni infraestructura propia para lograrlo.

Esta visión tiene un límite deliberado: Luarix no aspira a sustituir el criterio del trader ni a prometer rendimientos. Aspira a que ese criterio, una vez definido, se ejecute sin los fallos que hoy destruyen cuentas — impulsividad, ausencia de stop loss, sobre-exposición, o simplemente la imposibilidad de probar una idea antes de arriesgar capital real.

### 2.2 Misión

Dar a cada usuario de Luarix la capacidad de:

- **Expresar** una estrategia de trading en lenguaje natural y ver cómo se traduce en un sistema que se ejecuta paso a paso, de forma trazable.
- **Cuestionar** esa estrategia antes de construirla — mediante el copiloto Luis, que analiza y pide clarificación en lugar de construir a ciegas lo primero que se le pide.
- **Validar** la estrategia contra datos históricos y en modo simulado antes de arriesgar un solo euro real.
- **Operar** bajo un marco de riesgo que no puede saltarse, ni por error del usuario ni por error del propio sistema.

### 2.3 Principios rectores del proyecto

Estos principios gobiernan toda decisión de producto, técnica y documental en Luarix:

1. **Seguridad antes que rentabilidad.** Ningún componente del sistema puede saltarse una regla de riesgo, un límite o un kill switch, sin importar cuán prometedora parezca una estrategia.
2. **Paper primero, siempre.** Ninguna estrategia llega a capital real sin haber demostrado consistencia en simulación y en datos históricos.
3. **Los hechos ejecutados son la única verdad.** El estado del portfolio se actualiza únicamente cuando una operación se ejecuta de verdad — nunca por la intención de operar.
4. **Responsabilidades separadas.** Quien decide la dirección de una operación (la estrategia) no decide cuánto capital arriesgar (el sizing), y quien decide cuánto arriesgar no decide si esa operación es segura (el riesgo). Esta separación no es un detalle técnico: es lo que impide que un solo error se propague sin control por todo el sistema.
5. **Todo es auditable.** Cada decisión que toma el sistema —incluidas las del copiloto de IA— debe poder rastrearse: qué se propuso, por qué, y qué se decidió al respecto.

### 2.4 Qué significa esto para socios y clientes

Para un socio, esta visión implica que el crecimiento de Luarix se mide primero en fiabilidad demostrada, no en velocidad de lanzamiento. Para un cliente, implica que ninguna funcionalidad —por atractiva que sea— se activa con dinero real hasta que haya superado las mismas barreras de validación que exigiría cualquier mesa de trading seria.

---

*Fin del Capítulo 2.*

---

## 3. Producto: Luarix Hoy

Este capítulo describe qué hace Luarix en términos funcionales — qué ve y qué puede hacer una persona que use el sistema hoy. El detalle de cómo está construido pertenece al documento técnico.

### 3.1 El flujo conceptual del sistema

Toda operación en Luarix atraviesa el mismo recorrido, sin excepciones ni atajos:

```
Datos de mercado → Contexto/indicadores → Estrategia → Señal
   → Dimensionamiento de capital → Evaluación de riesgo
   → Ejecución → Portfolio → Resultados y métricas
```

Cada etapa responde a una única pregunta, y ninguna etapa puede responder la pregunta de otra:

| Etapa | Pregunta que responde |
|---|---|
| Datos de mercado | ¿Qué está ocurriendo? |
| Estrategia | ¿Qué se quiere hacer? |
| Señal | ¿Qué se propone? |
| Dimensionamiento | ¿Cuánto capital se usa? |
| Riesgo | ¿Es seguro hacerlo? |
| Ejecución | ¿Cómo se realiza? |
| Portfolio | ¿Cuál es el estado resultante? |

Esta estructura es la aplicación directa del principio "responsabilidades separadas" del Capítulo 2: es lo que permite que, si una parte falla o se ve comprometida, el resto del sistema siga protegiendo el capital.

### 3.2 Los dos entornos de validación antes de operar con dinero real

**Backtesting.** Permite poner a prueba una estrategia contra datos históricos reales, para conocer su comportamiento estadístico —consistencia, pérdidas máximas esperadas, relación entre ganancia y riesgo— antes de que exista ninguna posibilidad de pérdida real.

**Paper Trading.** Es el entorno de simulación en tiempo real: la estrategia opera exactamente como lo haría con dinero real —incluyendo costes y condiciones de mercado— pero sin arriesgar capital. Es el último filtro antes de considerar una estrategia lista para producción.

Ninguna estrategia avanza a operar con capital real sin haber pasado, en ese orden, por ambos entornos.

### 3.3 Luis: el copiloto de inteligencia artificial

Luis es el componente que permite construir estrategias de trading mediante lenguaje natural, en lugar de requerir conocimiento de programación. Su diseño responde a un principio explícito: **Luis propone y valida, nunca ejecuta sin pasar por las mismas capas de riesgo que cualquier otra estrategia.**

Capacidades de Luis en producción:

- **Construcción conversacional de estrategias.** El usuario describe una estrategia en lenguaje natural, y Luis la traduce en un sistema ejecutable compuesto por los mismos bloques que cualquier estrategia construida manualmente (datos de mercado, filtros de señal, dimensionamiento, reglas de riesgo, ejecución).
- **Validación automática de coherencia.** Antes de aceptar una estrategia como válida, el sistema comprueba que esté bien formada — por ejemplo, que no se pueda enviar una orden sin haber pasado por gestión de riesgo.
- **Confirmación explícita para acciones destructivas.** Cualquier acción que elimine o sobrescriba trabajo existente requiere confirmación expresa del usuario; nunca ocurre de forma automática o silenciosa.
- **Modo de análisis de trader.** Antes de construir nada, Luis razona sobre la estrategia propuesta —evaluando su lógica frente a un criterio de trading definido— y puede pedir clarificación al usuario si la propuesta es ambigua o incompleta, en lugar de construir una interpretación arriesgada de lo que el usuario quiso decir. Este proceso de clarificación tiene un límite de rondas definido, de modo que el sistema nunca queda atrapado preguntando indefinidamente.
- **Visibilidad del estado del copiloto.** El usuario ve en todo momento qué está haciendo Luis —analizando, pidiendo una aclaración, validando o construyendo— en lugar de percibir el proceso como una caja negra.

### 3.4 Construcción visual de estrategias: el editor de flujos

Además de construir estrategias conversando con Luis, Luarix ofrece un **editor visual de flujos**: un lienzo donde cada bloque del sistema —una fuente de datos de mercado, una estrategia, un filtro de señal, una regla de riesgo, un tipo de bróker— se representa como un nodo que el usuario puede arrastrar, conectar y configurar directamente, viendo el pipeline completo como un diagrama.

Cada nodo muestra su propio estado —configurado correctamente, con advertencias, o con errores— de forma que el usuario detecta a simple vista si una estrategia está lista para operar o le falta algo. Por ejemplo, el sistema puede advertir visualmente que un bróker en modo real permanece bloqueado hasta que exista un kill switch configurado, o que una regla de riesgo obligatoria no se ha definido.

**Esto no es una segunda forma de construir estrategias, aislada de Luis — es la misma estrategia vista desde dos puertas de entrada distintas, que se retroalimentan en tiempo real:**

- Cuando el usuario le pide a Luis, en lenguaje natural, que construya o modifique una estrategia, el resultado aparece inmediatamente reflejado en el lienzo visual: los nodos y conexiones correspondientes se dibujan solos, como si el usuario los hubiera arrastrado a mano.
- Cuando el usuario edita algo directamente en el lienzo —mueve un nodo, cambia un parámetro, conecta dos bloques— Luis conoce ese cambio de inmediato. Puede razonar sobre el estado actual del pipeline, responder preguntas sobre él, o continuar construyendo a partir de exactamente donde el usuario lo dejó, sin pedirle que se lo vuelva a explicar.
- Las mismas reglas de validación —qué conexiones son válidas, qué falta, qué es peligroso activar— aplican por igual al camino conversacional y al camino visual. No existen dos conjuntos de reglas que puedan entrar en conflicto entre sí.

Esta doble vía de construcción, sincronizada en ambos sentidos, es una de las capacidades distintivas de Luarix: permite que un usuario más técnico ajuste el pipeline con precisión visual, y que un usuario menos técnico —o el mismo usuario, en otro momento— siga construyendo o corrigiendo con lenguaje natural, sin que ninguna de las dos formas de trabajar quede nunca desactualizada respecto a la otra.

### 3.5 Qué distingue a Luarix de otras herramientas de trading automatizado

- No es un generador de bots que "adivina" el precio: la estrategia central se basa en explotar desequilibrios de liquidez, volatilidad y contexto temporal con ventaja estadística, no en predicción.
- No permite saltarse la validación: no existe un camino directo de "idea" a "capital real" sin pasar por backtesting y paper trading.
- El copiloto de IA no es una capa de conveniencia superficial: participa activamente en la disciplina del sistema, cuestionando antes de construir.
- La construcción de estrategias no obliga a elegir entre lenguaje natural o edición visual: ambas vías operan sobre el mismo pipeline y se actualizan mutuamente en tiempo real, algo que la mayoría de plataformas de trading automatizado no ofrece.

El Capítulo 12 desarrolla esta comparación con detalle, frente a plataformas concretas del mercado actual — con tablas, metodología de señal y el panorama de facturación de la competencia.

---

*Fin del Capítulo 3.*

---

## 4. Arquitectura de Software (nivel ejecutivo)

### 4.1 Principio arquitectónico central

La arquitectura de Luarix aplica directamente la doctrina del proyecto: se construye lo necesario, con calidad, sin complejidad accidental. Bajo ese criterio, el sistema v1.0 se organiza como un **backend Django único** (`luarix_rest_api`), compuesto por módulos con responsabilidades estrictamente separadas, apoyado sobre una **librería de motor compartida** (`pandas_luarix`) y el copiloto de IA como subsistema independiente:

- **Motor / Core (`pandas_luarix`)** — la librería que implementa la detección de estructura de mercado y el cómputo matemático de base: pivotes, fractales, swings, liquidez, sweeps, displacement, order blocks y fair value gaps, además de los indicadores clásicos (RSI, Bandas de Bollinger, ATR, Estocástico). Es el único lugar del sistema donde esta lógica existe, y de ahí la consumen directamente tanto el backtesting como la ejecución en vivo, sin una llamada de red de por medio en cada cálculo.
- **Workflows (motor de ejecución de estrategias)** — el módulo que toma una estrategia ya configurada como grafo de nodos y la **pone a correr de verdad**: ordena el grafo topológicamente, lo recorre nodo a nodo, y registra en un log de auditoría qué nodo se activó, en qué momento y con qué resultado. Esta es la capa de **runtime** del sistema.
- **Backtesting** — motor dedicado a validar estrategias contra datos históricos de forma reproducible, reutilizando el mismo motor de ejecución y el mismo Motor/Core que la operación en vivo, vela a vela, con métricas de rendimiento completas y progreso en tiempo real.
- **Indicators** — persiste cada elemento de estructura de mercado detectado (swings, order blocks, sweeps, niveles de liquidez) con su propia procedencia auditable, de forma que cualquier señal puede rastrearse hasta el dato que la originó.
- **Brokers** — gestiona cuentas y credenciales de conexión a los exchanges soportados, con cifrado en reposo y sin conceder nunca permisos de retiro de fondos.
- **Security** — autenticación y control de acceso a la API.
- **Marketdata** — mantiene el histórico de mercado con el que operan tanto el backtesting como la ejecución en vivo.
- **El plano de control** — configuración de cada estrategia (el grafo de nodos, como JSON), su estado (borrador, en ejecución, pausada, detenida), el histórico de órdenes y el portfolio agregado, expuestos vía la API que usan Luis y el editor visual — vive en el mismo backend Django.

**Sobre por qué el motor de ejecución (Workflows) es un módulo separado del resto del plano de control, aunque ambos convivan hoy en el mismo backend:** son dos problemas de naturaleza distinta.

El plano de control resuelve un problema de **configuración**: guardar el grafo de una estrategia, consultar su estado, exponer una API a Luis y al editor visual, llevar el registro de qué existe y qué pasó. Es exactamente el tipo de trabajo para el que Django está pensado —modelos, base de datos, API, panel de administración— y es un patrón estándar en plataformas de trading serias mantener esto separado de la ejecución.

Workflows resuelve un problema de **runtime**: recorrer el grafo nodo a nodo, evaluando cada uno, reaccionando a los datos de mercado, y dejando un rastro auditable de cada activación. Mantener esta responsabilidad detrás de una interfaz propia y aislada es lo que evita que:

- **El plano de control deje de ser solo eso** y pase a cargar procesos de fondo de larga duración compitiendo por los mismos recursos que atienden la API.
- **Un fallo en la ejecución de una estrategia** (un nodo que se cuelga, un bucle que no responde) degrade la capacidad del resto del sistema de atender la API, en vez de quedar aislado al módulo de ejecución y a esa estrategia concreta.

Esta separación también evita que la granularidad de auditoría por nodo y por ciclo —qué se activó, cuándo, con qué resultado— se mezcle con el modelo de datos de configuración: son dos ritmos de escritura completamente distintos, el plano de control cambia cuando alguien edita una estrategia, Workflows escribe constantemente mientras esa estrategia está activa.

Esta arquitectura es lo que permite, cuando el volumen de estrategias activas lo justifique, extraer el motor de ejecución como servicio independiente sin rediseñar nada: la separación ya existe a nivel de módulo, no depende de dónde se despliegue físicamente.

### 4.2 Vista de paquetes y módulos

```
┌───────────────────────────────────────────────────────────────────────┐
│                              LUARIX v1.0                                │
│                                                                          │
│  ┌───────────────────────────┐      ┌──────────────────────────────┐  │
│  │      COPILOTO IA — LUIS    │◄────►│     BACKEND (Django / DRF)    │  │
│  │  (TypeScript / Next.js)    │      │                                │  │
│  │  · Registro de nodos       │      │  · Configuración de           │  │
│  │  · Bucle del agente        │      │    estrategias (grafo, JSON)  │  │
│  │  · Validador de grafo      │      │  · Estado (draft/running/     │  │
│  │  · Modo análisis trader    │      │    paused)                    │  │
│  └───────────────────────────┘      │  · Autenticación (JWT)         │  │
│                                       │  · API documentada (OpenAPI)  │  │
│                                       └──────────────┬─────────────────┘  │
│                                                       │ despliega/detiene  │
│                                                       ▼                   │
│                                        ┌───────────────────────────┐     │
│                                        │         WORKFLOWS           │   │
│                                        │  motor de ejecución de      │   │
│                                        │  estrategias                │   │
│                                        │  · Orden topológico del     │   │
│                                        │    grafo                    │   │
│                                        │  · Sizing · Riesgo · Órdenes│   │
│                                        │  · Brokers (Paper/Binance/  │   │
│                                        │    Bitunix)                 │   │
│                                        │  · Log de auditoría por     │   │
│                                        │    nodo (nodo, timestamp,   │   │
│                                        │    resultado)                │   │
│                                        └──────────────┬───────────────┘  │
│                                                        │                  │
│              ┌────────────────────────┐                │                  │
│              │      BACKTESTING         │               │                  │
│              │  · Motor evento a evento, │               │                  │
│              │    vela a vela             │              │                  │
│              │  · Métricas completas       │             │                  │
│              │    (equity, drawdown,        │            │                  │
│              │    win rate, profit factor)   │           │                  │
│              │  · Progreso en vivo (WebSocket)│          │                  │
│              └──────────────┬──────────────────┘         │                  │
│                              │                           │                  │
│                              ▼                           ▼                  │
│           ┌───────────────────────────────────────────────────────┐       │
│           │          MOTOR / CORE (librería `pandas_luarix`)         │      │
│           │  · Pivotes · Fractales · Swings · Liquidez · Sweeps       │     │
│           │  · Displacement · Order Blocks · Fair Value Gaps           │    │
│           │  · Indicadores clásicos (RSI, Bandas de Bollinger, ATR,     │   │
│           │    Estocástico)                                              │  │
│           └───────────────────────────────────────────────────────┘       │
│                                                                          │
│    ┌───────────────────────┐  ┌────────────────────────┐  ┌───────────┐ │
│    │      INDICATORS         │  │        BROKERS           │  │ SECURITY  │ │
│    │  Persistencia de         │  │  Credenciales cifradas,   │  │ Auth. JWT,│ │
│    │  estructura detectada,   │  │  sin permisos de retiro   │  │ control de│ │
│    │  con procedencia          │  │  (Binance, Bitunix)        │  │ acceso    │ │
│    │  auditable                 │  │                             │  │           │ │
│    └───────────────────────┘  └────────────────────────┘  └───────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

**Backend** expone la configuración de cada estrategia y la API que usan Luis y el editor visual. Cuando el usuario —o Luis— pone una estrategia a correr, Backend delega en **Workflows**, que la ejecuta ciclo a ciclo, gestiona los brókers soportados y deja el registro de auditoría de cada activación. **Backtesting** resuelve el mismo tipo de ejecución que Workflows, pero sobre histórico, reutilizando el mismo **Motor/Core**. Esa simetría —la misma base matemática sirviendo a la ejecución en vivo y al histórico— es lo que garantiza que una estrategia se comporte igual en papel, en histórico y en producción.

### 4.3 Tecnologías empleadas

| Componente | Tecnología principal | Motivo |
|---|---|---|
| Motor / Core (`pandas_luarix`) | Python (pandas, pandas-ta, NumPy) | Ecosistema de referencia para cómputo numérico; motor propio, construido y validado internamente contra las referencias de mercado más usadas en el análisis de estructura (SMC). |
| Backend, Workflows, Backtesting, Indicators, Brokers, Security, Marketdata | Django + Django REST Framework | Framework maduro para modelos de datos, persistencia, API y panel de administración, con bajo esfuerzo de mantenimiento. |
| Ejecución en tiempo real | Django Channels (ASGI, Daphne) | Comunicación por WebSocket para progreso de backtesting y estado de estrategias en ejecución. |
| Tareas asíncronas y programadas | Celery + Celery Beat | Procesamiento en segundo plano y tareas periódicas, desacoplado del ciclo de petición/respuesta de la API. |
| Autenticación | JWT (`djangorestframework-simplejwt`) | Tokens de acceso de vida corta con rotación y revocación, más límite de intentos en el inicio de sesión. |
| Documentación de API | OpenAPI / Swagger (`drf-spectacular`) | Contrato de API navegable, generado a partir del código y siempre sincronizado con él. |
| Cifrado de credenciales | `cryptography` (Fernet) | Cifrado simétrico en reposo para las credenciales de bróker; el sistema rehúsa arrancar en producción sin una clave de cifrado configurada. |
| Persistencia | PostgreSQL (particionado) | Almacenamiento transaccional, con particionado para las series de datos de mercado de mayor volumen. |
| Almacenamiento de archivos | S3 | Almacenamiento de artefactos fuera del ciclo de vida del servidor de aplicación. |
| Despliegue | systemd (Daphne + workers y tareas programadas de Celery) + nginx | Infraestructura de producción: procesos supervisados y proxy inverso con soporte de WebSocket. |
| Copiloto IA — Luis | TypeScript, Next.js | Integración con la API de mensajes de Anthropic mediante streaming (SSE), en infraestructura serverless. |
| Razonamiento del copiloto | API de Anthropic (Claude) | Interpreta lenguaje natural, invoca herramientas y construye el pipeline. |

El Motor/Core, Workflows, Backtesting, Indicators, Brokers, Security y Marketdata comparten Python y Django porque resuelven problemas de la misma naturaleza (dominio financiero y cómputo cuantitativo) y necesitan intercambiar los mismos contratos de datos sin fricción de traducción entre lenguajes. Luis usa una pila distinta porque su naturaleza —conversación en tiempo real con un modelo de lenguaje— es un problema diferente a todos los anteriores. Ninguna de estas elecciones busca uniformidad por sí misma; cada una responde al problema que resuelve.

---

*Fin del Capítulo 4.*

---

## 5. Alcance del Proyecto — Capacidades de la Versión 1.0

Este capítulo existe para que ningún socio o cliente tenga que inferir qué entrega Luarix hoy: se declara explícitamente. Es la aplicación directa del principio "sin promesas que el estado del sistema no pueda respaldar" de la doctrina de trabajo — aplicado ahora a una versión 1.0 completa, no a un estado intermedio.

### 5.1 Qué entrega la versión 1.0

- La **arquitectura del motor de trading** descrita en el Capítulo 4: Motor/Core, Workflows, Backtesting, Indicators, Brokers, Security, Marketdata y el plano de control, operando de forma integrada.
- El **ciclo completo end-to-end**: mercado → estrategia → señal → sizing → riesgo → ejecución → portfolio, tanto en papel como en backtesting, sobre los modelos de dominio del Capítulo 3 (señal, orden, ejecución, posición, portfolio).
- El **copiloto de IA (Luis)** completo: construcción conversacional de estrategias, validación de coherencia del pipeline, confirmación explícita para acciones destructivas, y el modo de análisis de trader con clarificación descrito en el Capítulo 3.
- El **editor visual de flujos** y su sincronización bidireccional con Luis, operando como una única estrategia vista desde dos entradas.
- La **validación estadística** de estrategias mediante backtesting, con métricas de rendimiento completas y reproducibles.
- La **integración de mercado** con Binance y Bitunix, y el marco de gestión de riesgo y custodia del Capítulo 7, operando en todo momento.

### 5.2 Qué queda deliberadamente fuera de la v1.0, reservado para la evolución del producto

Ninguno de estos puntos es una carencia — son decisiones de alcance para que la v1.0 fuera sólida antes de extenderse, y se retoman como evolución de producto (Capítulo 10) o como parte de la línea de negocio priorizada (Capítulo 13):

- **Ampliar la integración a brókers y exchanges adicionales**, más allá de Binance y Bitunix, conforme lo requiera la línea de negocio en curso.
- **Infraestructura de cara al cliente final a mayor escala** (paneles de cuenta multiusuario, autoservicio) para las líneas de negocio que la requieran (Capítulo 13.2, Líneas 2 y 3).
- **Funcionalidades de marketplace, trading social o monetización de estrategias entre usuarios.** Son parte de la visión a futuro (Capítulo 10).
- **Multi-estrategia con capital asignado en paralelo a mayor escala** (Capítulo 6).

### 5.3 Capacidades entregadas

| Componente | Estado |
|---|---|
| Arquitectura del motor de trading (Capítulo 4) | Implementada |
| Modelos de dominio y ciclo end-to-end (papel y backtesting) | Implementado |
| Backtesting con métricas de rendimiento reproducibles | Implementado |
| Copiloto Luis — construcción conversacional, validación, confirmaciones | Implementado |
| Copiloto Luis — modo de análisis de trader y clarificación | Implementado |
| Editor visual de flujos, sincronizado con Luis | Implementado |
| Gestión de riesgo estructural (Capítulo 7) | Operando |
| Cifrado de credenciales y autenticación | Operando |
| Integración de mercado (Binance, Bitunix) | Operando |
| Documentación de API (OpenAPI/Swagger) | Publicada |
| Postura regulatoria | Definida conforme a la línea de negocio (Capítulos 8 y 13) |
| Marketplace / trading social / monetización entre usuarios | Reservado para la evolución del producto (Capítulo 10) |
| Multi-bróker ampliado / multi-estrategia en paralelo a escala | Reservado para la evolución del producto (Capítulos 6 y 10) |

---

*Fin del Capítulo 5.*

---

## 6. Etapas y Hoja de Ruta

### 6.1 Principio de secuenciación

La hoja de ruta de Luarix sigue un orden estricto, no una lista de funcionalidades deseables: **ninguna etapa posterior comienza en serio antes de que la anterior cumpla sus criterios de aceptación.** Esto es consecuencia directa del principio "paper primero" del Capítulo 2 — no se trata de avanzar rápido, se trata de no construir sobre una base que todavía no demostró ser fiable.

Existen dos hojas de ruta paralelas, porque son dos subsistemas con ritmos de madurez distintos: el **Motor de Trading** y el **Copiloto IA (Luis)**. Avanzan de forma independiente, aunque convergen en el mismo producto.

### 6.2 Hoja de ruta del Motor de Trading

| Etapa | Contenido | Estado |
|---|---|---|
| 1. Fundamentos del motor | Modelos de dominio estables (señal, orden, ejecución, posición, portfolio) y un ciclo paper completo, de punta a punta, sin errores | Completado en v1.0 |
| 2. Estrategia ejecutable y riesgo real | Estrategia de Luis totalmente implementada (confluencias, entradas fraccionadas, stop dinámico), con reglas de riesgo reales: límite por operación, drawdown diario máximo, exposición máxima por activo | Completado en v1.0 |
| 3. Backtesting reproducible | Motor de simulación evento a evento sobre datos históricos, con métricas de rendimiento reales: expectancy, profit factor, drawdown máximo, Sharpe ratio | Completado en v1.0 |
| 4. Datos de mercado reales | Integración con datos históricos y en vivo del exchange (Binance, Bitunix), mantenida separada de la ejecución de órdenes | Completado en v1.0 |
| 5. Bróker en producción | Integración real con los exchanges soportados | Completado en v1.0 |
| 6. Observabilidad y control operativo | Registro estructurado de cada decisión, trazabilidad completa, kill switch manual y automático | Completado en v1.0 |
| 7. Multi-estrategia | Varias estrategias operando en paralelo con capital asignado de forma independiente | Visión v2.0 — Capítulo 10 |
| 8. Expansión de líneas de negocio | Escalar la operación conforme a la línea comercial priorizada | Próximo paso — Capítulo 11 |

### 6.3 Hoja de ruta del Copiloto IA (Luis)

| Fase | Contenido | Estado |
|---|---|---|
| 0–5 | Construcción conversacional de estrategias, catálogo de bloques disponibles para construir un pipeline, validación automática de coherencia del grafo, confirmación explícita para acciones destructivas, modo de análisis de trader con clarificación, y visibilidad completa del estado del copiloto en cada momento | Completado en v1.0 |

### 6.4 Hitos, no fechas de calendario

Deliberadamente, esta hoja de ruta no fija fechas. Cada etapa se considera cerrada cuando cumple sus criterios de aceptación —no cuando se agota un plazo—, porque comprometerse con una fecha sobre un sistema que maneja capital invita a recortar validación para cumplir un calendario. Eso es exactamente lo que la doctrina del proyecto busca evitar, también en la evolución hacia v2.0.

---

*Fin del Capítulo 6.*

---

## 7. Gestión de Riesgo y Seguridad

### 7.1 Por qué esto es una decisión de negocio, no solo una característica técnica

"Seguridad antes que rentabilidad" (Capítulo 2) no es un eslogan: es la decisión de negocio que protege tres cosas al mismo tiempo — el capital de quien opera, la reputación de Luarix, y al propio equipo frente a la tentación de recortar validación para avanzar más rápido. En trading automatizado, una estrategia mediocre con buen control de riesgo puede sobrevivir a un mal periodo; una estrategia prometedora con controles débiles puede destruir una cuenta en una sola racha adversa. Este capítulo describe esos controles no como funcionalidades del producto, sino como el marco de gobierno que hace que el sistema pueda operar sin depender de que nadie "se acuerde" de aplicar una regla.

### 7.2 Los controles de riesgo como gobierno del sistema

Cada uno de estos controles existe para responder a una forma concreta y conocida en que una cuenta de trading se destruye. Ninguno es opcional una vez que el sistema opera con capital —simulado o real—:

- **Límite de riesgo por operación.** Ninguna operación individual puede arriesgar más de un porcentaje definido del capital disponible. Esto convierte una mala operación en un evento manejable, nunca en un evento catastrófico.
- **Drawdown diario máximo (circuit breaker).** Si las pérdidas del día alcanzan un umbral definido, el sistema deja de abrir nuevas operaciones automáticamente. Esto existe precisamente para el escenario en que la disciplina humana falla: nadie tiene que decidir "parar por hoy" bajo presión, porque el sistema ya lo hace.
- **Exposición máxima por activo.** Ninguna estrategia puede concentrar el capital en un único activo más allá de un límite, incluso si la señal parece muy convincente.
- **Notional mínimo y máximo por orden.** Evita órdenes tan pequeñas que no tengan sentido operativo, y órdenes tan grandes que excedan lo que la gestión de riesgo aprobó.
- **Máximo de posiciones abiertas.** Limita cuántas operaciones simultáneas puede sostener el sistema, para que el riesgo total permanezca observable y acotado.
- **Control de duplicados.** Ninguna señal puede generar más de una orden por error o por reintento — cada orden lleva un identificador único que impide que un fallo de red se traduzca en una posición duplicada.
- **Kill switch manual y automático.** En cualquier momento, una persona puede detener toda nueva operación de forma inmediata. Además, el sistema puede activarlo por sí mismo ante condiciones anómalas, sin esperar intervención humana.

Estos controles no compiten entre sí ni son redundantes: cada uno cierra una vía de fallo distinta, y todos se evalúan antes de que una operación llegue a ejecutarse, tal como se describe en el flujo del Capítulo 3.

### 7.3 Validación antes de arriesgar capital

Backtesting y paper trading (Capítulo 3) son, en sí mismos, el primer y más importante control de riesgo: ninguna estrategia demuestra su validez arriesgando capital real, la demuestra contra datos históricos y en simulación. Este orden —histórico, luego simulado en tiempo real, y solo después capital real— no es una fase de desarrollo transitoria: es una política permanente de Luarix para cualquier estrategia nueva o modificada, incluidas las construidas por el copiloto Luis.

### 7.4 Custodia de fondos y credenciales

Luarix opera bajo la siguiente postura de custodia, sin excepción:

- **Sin permisos de retiro.** Cualquier credencial de acceso a un exchange que use Luarix se configura únicamente con permisos de operación (compra/venta), nunca con permisos de retiro de fondos. Aunque una credencial se viera comprometida, no debería ser posible mover fondos fuera de la cuenta del usuario.
- **Credenciales cifradas, nunca expuestas en texto plano.** Ninguna clave de acceso se almacena ni se registra en logs de forma legible.
- **El sistema nunca es custodio de facto de las decisiones del usuario.** Todo cambio de configuración relevante para el riesgo (activar modo real, aumentar límites) requiere una acción explícita del usuario, nunca ocurre por defecto ni de forma silenciosa —el mismo principio de confirmación explícita que ya rige al copiloto Luis (Capítulo 3).

### 7.5 Auditoría como integridad operativa, no como formalidad

"Todo es auditable" (Capítulo 2) tiene una consecuencia práctica muy concreta: ante cualquier resultado inesperado —una pérdida mayor a la prevista, una orden que no se comportó como se esperaba— debe ser posible reconstruir exactamente qué decidió el sistema, en qué orden, y por qué, sin depender de la memoria de quien lo operó. Esto incluye las decisiones del copiloto de IA: qué propuso, qué preguntó, y qué se aprobó finalmente.

---

*Fin del Capítulo 7.*

---

## 8. Consideraciones Regulatorias y Legales

### 8.1 Marco de referencia y postura de Luarix

Luarix aplica al plano legal y regulatorio el mismo principio que ya rige su arquitectura técnica y su gobierno de riesgo (Capítulos 2, 4 y 7): responsabilidades separadas y explícitas. Qué hace Luarix como proveedor de tecnología y, según la línea de negocio priorizada en el Capítulo 13, como gestor de capital; qué corresponde a cada usuario, trader o mandante como responsable de sus propias decisiones; y qué requiere de terceros (exchanges, custodios, asesoría legal y de cumplimiento) que Luarix no absorbe internamente. **Nada en este capítulo constituye asesoría legal**; es la orientación de producto que guía el trabajo con asesoría legal formal específica de cada jurisdicción.

### 8.2 Marco regulatorio de referencia

Para la operación con usuarios y capital reales dentro de la Unión Europea, el marco de referencia central es el **Reglamento MiCA** (Markets in Crypto-Assets), que regula la prestación de servicios sobre criptoactivos y puede exigir licenciamiento como proveedor de servicios de criptoactivos (CASP) según el tipo de actividad concreta que se ofrezca. A esto se suman, según el alcance de cada línea de negocio (Capítulo 13):

- **AML/KYC** (prevención de blanqueo de capitales e identificación de usuarios), en la intermediación de operaciones de terceros.
- **GDPR**, en el tratamiento de datos personales de usuarios.
- Revisión de **promociones financieras**, al comunicar públicamente sobre rendimiento o resultados de estrategias.

Esta lista es orientativa, no exhaustiva: su aplicabilidad exacta depende de qué línea de negocio del Capítulo 13 esté en curso — operar fondos de terceros directamente (Línea 1) y proveer solo la tecnología para que cada usuario opere los suyos (Líneas 2-4) tienen implicaciones regulatorias distintas, y cada una se formaliza con asesoría legal específica conforme avanza.

### 8.3 Separación de responsabilidades

El principio rector para cualquier cliente externo es el mismo que ya rige la arquitectura técnica (Capítulo 4): **responsabilidades separadas y explícitas**, ahora a nivel legal y operativo, no solo de software:

- Qué hace Luarix como proveedor de tecnología y, cuando corresponda, como gestor de capital.
- Qué corresponde a cada usuario como responsable de sus propias decisiones de trading y de su propio capital.
- Qué requiere de terceros (exchanges, custodios, asesoría legal y de cumplimiento) que Luarix no absorbe internamente.

Esta separación se formaliza con precisión legal a medida que cada línea de negocio del Capítulo 13 se pone en marcha, siguiendo la misma doctrina de "hacer lo necesario, bien": los trámites regulatorios y licencias se contratan conforme el negocio real que los requiere avanza, no por adelantado.

### 8.4 Alcance de este capítulo

Este capítulo documenta la orientación de producto y el criterio interno del equipo técnico. Se amplía, con el detalle y el rigor que corresponda, con asesoría legal específica conforme cada línea de negocio del Capítulo 13 pasa de decisión a operación.

---

*Fin del Capítulo 8.*

---

## 9. Equipo y Modelo de Colaboración

### 9.1 Roles actuales

Luarix se construye hoy con un equipo reducido y roles claros:

- **Dirección técnica y de producto**, responsable de la arquitectura del sistema, la especificación de cada fase de desarrollo y la documentación formal del proyecto —tanto la institucional (este documento) como la técnica.
- **Criterio de trading**, aportado por la persona cuya estrategia (descrita en el Capítulo 3) es la que el motor y el copiloto Luis deben ejecutar con fidelidad. Este rol es un socio clave del proyecto: sin ese criterio de trading, no hay estrategia central que codificar, y toda decisión de producto sobre cómo debe comportarse Luis o el motor se contrasta contra ese criterio.

### 9.2 Modelo de trabajo: planificación separada de implementación

Luarix separa deliberadamente dos actividades que suelen mezclarse en proyectos de software y que, mezcladas, producen decisiones peor pensadas:

- **Planificación y especificación.** Toda decisión de arquitectura, alcance o diseño se documenta primero, con su razonamiento explícito —no solo el resultado, sino por qué se decidió así—, siguiendo el mismo patrón que este documento institucional ha seguido capítulo a capítulo: se redacta, se revisa, se corrige, y solo entonces se avanza al siguiente punto.
- **Implementación.** Una vez que una fase está completamente especificada —como ocurrió con la Fase 5 del copiloto Luis (Capítulo 6)—, la construcción del código se delega a herramientas de desarrollo asistido por IA, trabajando a partir de esa especificación ya validada, no a partir de una idea suelta.

Esta separación no es un detalle de proceso menor: es la misma disciplina de "responsabilidades separadas" del Capítulo 2, aplicada a cómo se construye Luarix y no solo a lo que Luarix construye. Decidir primero y programar después reduce el riesgo de que una decisión de arquitectura se tome implícitamente, sin que nadie la haya cuestionado, solo porque "así salió más fácil de programar".

### 9.3 Documentación como fuente de verdad del proyecto

Tanto el documento institucional (este) como el documento técnico correspondiente se mantienen como documentos vivos, no como entregables de una sola vez: se amplían capítulo a capítulo conforme el proyecto avanza, y cada capítulo se apoya en los anteriores sin redefinir lo ya acordado. Esto cumple una función concreta más allá de la comunicación con socios y clientes: es el medio por el cual cualquier decisión —de arquitectura, de alcance o de riesgo— queda registrada con su razonamiento, en lugar de existir solo en la memoria de quien la tomó.

### 9.4 Incorporación de futuros socios o colaboradores

Cualquier persona que se incorpore al proyecto —ya sea a la dirección técnica, al desarrollo, o como socio de negocio— parte de esta misma documentación como punto de referencia: primero entiende el estado real del proyecto (Capítulo 5), la arquitectura ya decidida (Capítulo 4) y los principios que la gobiernan (Capítulo 2), y construye sobre esa base en lugar de reabrir decisiones ya tomadas sin una razón nueva y explícita que lo justifique.

---

*Fin del Capítulo 9.*

---

## 10. Visión a Futuro

### 10.1 Qué es, y qué no es, este capítulo

Todo lo descrito aquí es **aspiracional**: representa direcciones posibles de evolución de Luarix más allá de la versión 1.0 ya entregada —motor de trading, copiloto Luis, editor visual, descritos en los Capítulos 3 a 7—, no un compromiso de entrega ni una extensión del alcance definido en el Capítulo 5. Se documenta por una razón concreta: un socio o inversor con visión de mediano plazo necesita saber hacia dónde podría crecer Luarix, sin que eso se confunda con lo que Luarix ya construyó.

### 10.2 Posibles direcciones de evolución

- **Un mercado de estrategias.** Una vez que existan estrategias validadas de forma consistente en backtesting y paper trading, podría tener sentido que los usuarios compartan, comparen y sigan estrategias de otros, con visibilidad de su rendimiento histórico real.
- **Trading social y copia de estrategias.** Permitir que un usuario asigne capital para replicar automáticamente las decisiones de una estrategia ajena ya validada, manteniendo intactos todos los controles de riesgo del Capítulo 7 —la copia de una estrategia no debería nunca significar copiar también sus fallos de gestión de riesgo.
- **Monetización para quien crea estrategias.** Un mecanismo por el cual quien construye y valida una estrategia sólida pueda beneficiarse de que otros la sigan, siempre sobre una base de rendimiento verificado, no de promesas.
- **Expansión más allá de los mercados de hoy.** La v1.0 opera sobre Binance y Bitunix (Capítulo 5); a futuro, la misma arquitectura de nodos y contratos compartidos (Capítulo 4) puede extenderse a más exchanges y otros mercados, sin rediseñar el sistema desde cero.
- **Capacidades de investigación asistidas por IA más amplias.** Análisis de contexto adicional al puramente técnico —por ejemplo, eventos macroeconómicos relevantes— como una señal más de contexto para el copiloto Luis, nunca como sustituto de la disciplina de riesgo ya establecida.

### 10.3 Lo que no cambia, sin importar cuánto crezca el producto

Cualquiera de estas direcciones, si se persigue algún día, se construye **sobre** los principios rectores del Capítulo 2 —seguridad antes que rentabilidad, paper primero, responsabilidades separadas, todo auditable—, no a pesar de ellos. Un mercado de estrategias sin control de riesgo real detrás sería exactamente el tipo de producto que Luarix existe para no ser.

### 10.4 Una nota de honestidad

Nada de este capítulo debe leerse como una promesa a socios o clientes. Es, deliberadamente, la sección menos comprometida de todo el documento —el resto describe lo que la versión 1.0 ya entrega y opera, con criterios de aceptación claros; esto describe lo que podría llegar a existir sobre esa base.

---

*Fin del Capítulo 10.*

---

## 11. Próximos Pasos

Con la versión 1.0 del motor de trading y del copiloto Luis entregada (Capítulos 3 a 7), los próximos pasos de Luarix son de negocio y de escala, no de construcción del núcleo.

### 11.1 Próximos pasos inmediatos

- **Ejecutar la línea de negocio priorizada** (Línea 1 — gestión de capital de terceros, Capítulo 13.4): iniciar la operación bajo el marco de riesgo del Capítulo 7 para construir el track record auditado que sostiene, después, las Líneas 2 y 5.
- **Ampliar la cobertura de exchanges y brókers** más allá de Binance y Bitunix, conforme lo requiera la línea de negocio en curso.
- **Preparar la infraestructura de cara al cliente** (autenticación de usuarios externos, panel de cuenta) para las líneas de negocio que la requieran (Capítulo 13.2, Líneas 2 y 3).
- **Formalizar la postura regulatoria** (Capítulo 8) con asesoría legal específica, conforme al modelo de negocio elegido.

### 11.2 Qué se necesita para seguir avanzando

- **Decisión formal de negocio**: confirmar la secuencia de líneas comerciales propuesta en el Capítulo 13.4, o ajustarla.
- **Capital y/o mandatos iniciales** para la Línea 1, que permitan generar el historial auditado de rendimiento sobre el que se apoyan las siguientes líneas.
- **Continuidad del documento técnico**, en paralelo a este documento institucional, con el mismo patrón de trabajo: capítulo a capítulo, con revisión y corrección antes de avanzar.

### 11.3 Sobre este documento

Este documento institucional se amplía en esta versión con el panorama competitivo (Capítulo 12), el modelo de negocio (Capítulo 13), las conclusiones (Capítulo 14) y las referencias (Capítulo 15), y sigue siendo, por diseño, un **documento vivo**: se revisará y corregirá cada vez que el proyecto avance, se tome una nueva decisión de arquitectura, de alcance o de negocio, o el mercado que describe el Capítulo 12 cambie de forma relevante.

---

*Fin del Capítulo 11.*

---

## 12. Innovación y Panorama Competitivo

### 12.1 Qué hace distinto a Luarix

- **Auditoría por nodo, no solo por operación.** Cada estrategia en Luarix es un grafo de nodos; cada vez que se ejecuta, el sistema deja un registro de qué nodo se activó, cuándo y con qué resultado — y cada operación queda ligada al nodo exacto que la disparó y a una fotografía completa del contexto de mercado en el momento de la señal. La mayoría de plataformas de trading automatizado del mercado registran la orden final; pocas registran la cadena de razonamiento completa que llevó a ella.
- **Motor de estructura de mercado (SMC) propio, no una librería de terceros envuelta.** Pivotes, swings, equal highs/lows, rupturas de estructura, order blocks, fair value gaps y barridos de liquidez están implementados y validados internamente por Luarix, no importados sin control sobre su exactitud.
- **Construcción por lenguaje natural y por edición visual, sincronizadas en ambos sentidos.** Luis y el editor de flujos son dos entradas a la misma estrategia: lo que se construye hablando con Luis aparece en el lienzo, y lo que se edita en el lienzo lo entiende Luis de inmediato — sin dos fuentes de verdad que puedan divergir.
- **Copiloto que cuestiona antes de construir.** Luis no traduce ciegamente la primera frase del usuario en una estrategia: la analiza, la contrasta contra un criterio de trading definido, y pide clarificación cuando hace falta.
- **Gobierno de riesgo estructural, no opcional.** Los límites de riesgo, el kill switch y la validación obligatoria en papel y en histórico antes de capital real no son una casilla que el usuario pueda desmarcar — son parte del motor de ejecución (Capítulo 7).
- **Credenciales sin permisos de retiro, cifradas en reposo**, con arranque bloqueado si falta la clave de cifrado en producción (Capítulo 4).

### 12.2 Construcción de estrategias: Luarix frente al mercado

| Plataforma | Cómo se construye | Requiere programar | IA conversacional | Editor visual de nodos | Sincronización bidireccional lenguaje↔visual |
|---|---|---|---|---|---|
| **Luarix** | Lenguaje natural (Luis) o editor de nodos | No | Sí | Sí | Sí |
| MetaTrader 4/5 | Programación en MQL4/MQL5 | Sí | No | No | — |
| TradingView | Programación en Pine Script; copiloto de IA solo para manipular el chart, no para construir estrategias con gestión de riesgo | Sí, para estrategias | Parcial (solo chart) | Limitado a indicadores | No |
| 3Commas / Cryptohopper / Coinrule | Reglas y condiciones preconfiguradas, sin código | No | No (salvo asistentes puntuales) | Parcial (reglas, no grafo completo) | No |
| Composer.trade | Lenguaje natural → estrategia ejecutable ("symphony") | No | Sí | Parcial (bloques de asignación) | No |
| QuantConnect | Programación (Python/C#) sobre el motor LEAN | Sí | No | No | — |

*Comparación de diseño y funcionalidad declarada públicamente por cada plataforma; no mide volumen de usuarios ni antigüedad en el mercado (ver 12.5).*

### 12.3 Gobierno de riesgo y validación: Luarix frente al mercado

| Plataforma | Backtesting obligatorio antes de vivo | Paper trading obligatorio | Kill switch automático | Límites de riesgo estructurales | Auditoría completa de decisiones |
|---|---|---|---|---|---|
| **Luarix** | Sí | Sí | Sí | Sí | Sí (por nodo y por operación) |
| MetaTrader 4/5 | No (disponible, no forzado) | No (disponible, no forzado) | A criterio del Expert Advisor | A criterio del programador | Log de operaciones, no de razonamiento |
| 3Commas / Cryptohopper | No forzado | No | Parcial (stop-loss configurable) | No | Log de operaciones |
| Composer.trade | Backtesting integrado, no obligatorio antes de asignar capital real | No | No | No | Parcial |
| QuantConnect | Backtesting robusto, no obligatorio antes de vivo | Disponible, no forzado | A criterio del algoritmo | A criterio del algoritmo | Log de ejecución del algoritmo |
| FTMO y otras prop firms | No aplica (evalúan disciplina del trader, no de un sistema) | No aplica | Sí, vía reglas de la evaluación | Sí, vía reglas de la evaluación | Métricas de la cuenta evaluada |

### 12.4 Metodología de señal: Luarix frente al mercado

| Enfoque | Plataformas representativas | Base de la señal |
|---|---|---|
| Predicción de precio / caja negra | Bots de IA genéricos comercializados como "predictivos" | Modelos que intentan anticipar la dirección del precio |
| Indicadores clásicos | MetaTrader (EAs genéricos), TrendSpider, Trade Ideas | Medias móviles, osciladores, patrones de velas |
| **Estructura de mercado y liquidez (SMC)** | **Luarix** | Desequilibrios de liquidez, order blocks, barridos, displacement — ventaja estadística sobre comportamiento institucional, no predicción |
| Copia social | eToro, ZuluTrade, Darwinex | Replicar operaciones de otros traders |
| Evaluación de disciplina | FTMO y otras prop firms | Consistencia y gestión de riesgo del trader, no una señal de mercado |

### 12.5 Panorama de facturación y escala de la competencia

| Empresa | Modelo | Métrica reciente | Fuente |
|---|---|---|---|
| eToro | Broker social / copy trading | Revenue USD 931M (2024, +48%); IPO Nasdaq 2025 a USD 5.64 mil millones | **[eToro]** |
| TradingView | Charting + comunidad + conectividad con brokers | Valoración pública USD 3 mil millones; 30M+ usuarios/mes | **[TradingView]** |
| MetaQuotes | Licenciamiento de terminal (MT4/MT5) a brokers | "Cientos" de brokers; licencia ~USD 10,000/mes | **[MetaQuotes]** |
| FTMO | Prop firm (evaluación + cuenta fondeada) | Revenue USD 329M (2024, +53%); neto ~USD 62.5M; 2.3M+ cuentas | **[FTMO]** |
| 3Commas | Bots no-code (SaaS) | 1M+ usuarios; USD 400 mil millones de volumen acumulado | **[3Commas/Cryptohopper/Coinrule]** |
| Composer.trade | No-code + IA (SaaS) | USD 200M+ de volumen diario | **[Composer]** |
| QuantConnect | Backtesting/algo cloud (comunidad) | 275,000+ quants registrados; USD 45 mil millones/mes de volumen nocional | **[QuantConnect]** |
| Alpaca | Brokerage-as-a-service (API) | ARR ~USD 100M; valoración USD 1.15 mil millones | **[Alpaca]** |
| Darwinex | Marketplace de gestión de activos | USD 140M+ AUM total | **[Darwinex]** |
| Numerai | Hedge fund crowdsourced con IA | AUM USD 550M, camino a USD 1,000M | **[Numerai]** |
| Interactive Brokers | Broker tradicional + algo/API | Revenue USD 6.205 mil millones (2025) | **[Interactive Brokers]** |
| TrendSpider / Trade Ideas | Charting + escaneo con IA (SaaS) | 20,000+ clientes (TrendSpider); planes USD 54-167/mes | **[TrendSpider/Trade Ideas]** |
| NexusTrade y otros builders no-code con IA | No-code + IA (SaaS) | 30,000+ traders declarados (NexusTrade) | **[NexusTrade]** |

### 12.6 Encuadre honesto de esta comparación

Esta comparación es de **diseño y capacidad del sistema**, no de volumen de mercado: las cifras de la Sección 12.5 muestran a qué escala han llegado modelos de negocio afines al de Luarix cuando maduran, no una equivalencia de tamaño actual. El Capítulo 13 traduce este panorama en líneas de negocio concretas y en una recomendación sobre cuál priorizar.

---

*Fin del Capítulo 12.*

---

## 13. Modelo de Negocio y Líneas Comerciales

### 13.1 Tamaño de mercado por segmento relevante

| Segmento | Tamaño / crecimiento | Relevancia para Luarix |
|---|---|---|
| Trading algorítmico (global) | USD 18.8-44.5 mil millones (2025, según definición del informe); CAGR 9-17% | Mercado total en el que compite el motor de Luarix — **[Algo-trading]** |
| Copy trading / social trading | USD 4.27 mil millones (2024) → USD 15-18 mil millones proyectado (2033) | Referencia directa para la Línea 3 y adyacente a la Línea 2 — **[Copy-trading]** |
| Prop trading (evaluación + fondeo) | USD 0.85-20 mil millones según fuente | Referencia directa para la Línea 5 — **[Prop-trading]** |
| Hedge funds (AUM global) | USD 5.22 billones (récord, 1T 2026) | Referencia directa para la Línea 1 — **[Hedge-funds]** |
| Managed futures / CTA | USD 310-348 mil millones AUM | Referencia directa para la Línea 1 (estrategias sistemáticas) — **[Managed-futures]** |
| Robo-advisors | ~USD 1.2 billones AUM global (2024) | Referencia de escala para gestión automatizada de capital — **[Robo-advisors]** |
| Software white-label para brokers | ~USD 5.6 mil millones (2022), 65%+ de brokers ya lo usan | Referencia directa para la Línea 4 — **[White-label]** |
| Inversión de capital de riesgo en trading (fintech) | USD 8.0 mil millones en 2025 (+485% en 3 años), 78 unicornios | Señal de apetito de mercado — "por qué ahora" — **[VC-fintech]** |

*Nota sobre la dispersión de cifras: distintas firmas de investigación de mercado definen el mismo segmento con alcances distintos (qué activos, qué geografías, qué se cuenta como "algorítmico"), lo que produce rangos amplios para el mismo nombre de mercado. Se cita el rango completo en vez de un único número falsamente preciso; el detalle de cada fuente está en el Capítulo 15.*

### 13.2 Las seis líneas de negocio

**Línea 1 — Gestión de capital de terceros (fondos, family offices, capital privado)**

Cliente objetivo: fondos de inversión, family offices y capital privado que asignan mandato a Luarix para operar directamente — los clientes "senior" del proyecto.
Mecanismo de ingreso: fee de gestión + fee de rendimiento, al estilo hedge fund.
Comparables de mercado: la industria de hedge funds (USD 5.22 billones de AUM global), los CTA sistemáticos (USD 310-348 mil millones), y Numerai (de USD 60M a USD 550M de AUM en 3 años, con compromiso de J.P. Morgan de hasta USD 500M adicionales) — **[Hedge-funds][Managed-futures][Numerai]**.
Fee benchmark: el modelo tradicional "2 y 20" se está comprimiendo hacia ~1.3% de gestión / ~16% de rendimiento en 2025 — **[Fees-hedge-fund]**.
Costo regulatorio de referencia (Unión Europea, Capítulo 8): una licencia CASP bajo MiCA implica entre EUR 300,000 y 700,000 de coste real el primer año, y entre EUR 150,000 y 250,000 anuales después — el motivo por el que esta línea marca "barrera regulatoria: Alta" en la comparativa de la Sección 13.3 — **[MiCA]**.

Tabla ilustrativa del mecanismo de fees — cifras puramente hipotéticas, no una proyección de captación de capital de Luarix:

| AUM gestionado | Fee de gestión (1.5%) | Rendimiento anual asumido | Fee de rendimiento (18%) | Ingreso anual ilustrativo |
|---|---|---|---|---|
| USD 1,000,000 | USD 15,000 | 15% | USD 27,000 | USD 42,000 |
| USD 10,000,000 | USD 150,000 | 15% | USD 270,000 | USD 420,000 |
| USD 50,000,000 | USD 750,000 | 15% | USD 1,350,000 | USD 2,100,000 |

Pros: aprovecha directamente el motor y el gobierno de riesgo de la v1.0 (Capítulos 4 y 7) sin necesitar un producto multiusuario; genera el track record auditado que respalda a las demás líneas; mayor ingreso por unidad de esfuerzo si el rendimiento es consistente.
Contras: la captación de capital es una disciplina distinta a la ingeniería del producto; una mala racha de rendimiento tiene el mayor costo reputacional de las seis líneas; la escala de ingresos está limitada por el capital que Luarix pueda gestionar directamente.

**Línea 2 — Tecnología para traders profesionales que operan para sus clientes (B2B / B2B2C)**

Cliente objetivo: traders profesionales, CTA pequeños y gestores independientes que operan capital de sus propios clientes.
Mecanismo de ingreso: licencia/suscripción de la plataforma, con opción de reparto de rendimiento.
Comparables: Darwinex (USD 140M+ de AUM total, reparte 15% del rendimiento del índice al trader), Alpaca (ARR ~USD 100M como infraestructura de brokerage vía API), licenciamiento de MetaQuotes a brokers (~USD 10,000/mes por licencia) — **[Darwinex][Alpaca][MetaQuotes]**.
Pros: economía de software (márgenes altos, ingreso recurrente); no requiere que Luarix asuma el riesgo fiduciario directo de cada cliente final; diversifica el ingreso entre muchos traders en vez de depender de un único mandato.
Contras: requiere un producto verdaderamente multiusuario; depende de que cada trader profesional tenga su propio marco legal para operar capital de terceros.

**Línea 3 — Traders retail / individuales**

Cliente objetivo: traders individuales que quieren automatizar su propia operativa.
Mecanismo de ingreso: suscripción SaaS mensual.
Comparables: 3Commas (1M+ usuarios, USD 400 mil millones de volumen acumulado), Cryptohopper y Coinrule (USD 24-107/mes), Composer.trade (USD 200M+ de volumen diario) — **[3Commas/Cryptohopper/Coinrule][Composer]**.
Dato honesto de contexto: entre 74% y 89% de las cuentas retail de forex/CFD pierden dinero en un trimestre dado, según las divulgaciones obligatorias de ESMA/FCA/CFTC — solo 5-7% de los traders retail son rentables de forma consistente tras 5 años — **[Pérdidas-retail]**. Ninguna plataforma, por buena que sea su ejecución, cambia por sí sola esa estadística: la herramienta ejecuta con disciplina la estrategia que se le da, no sustituye el criterio de quien la usa.
Pros: el mercado direccionable más grande en número de usuarios; menor barrera regulatoria si el usuario opera con sus propias credenciales (modelo no custodio, igual que 3Commas/Cryptohopper/Coinrule); ciclo de venta más corto.
Contras: mercado muy competido contra jugadores con años de ventaja; el costo de adquisición de cliente depende de marketing, no solo de ingeniería; el churn estructural es alto por la propia naturaleza del trading retail, no solo por la calidad del producto.

**Línea 4 — Licenciamiento B2B / white-label a brokers y prop firms**

Cliente objetivo: brokers y prop firms que quieren ofrecer una alternativa diferenciada a MetaTrader.
Mecanismo de ingreso: licencia mensual o por volumen, al estilo MetaQuotes.
Comparables: el mercado de software white-label para brokers (~USD 5.6 mil millones en 2022, 65%+ de brokers ya lo usan) y el propio licenciamiento de MetaQuotes — **[White-label][MetaQuotes]**.
Pros: mayor apalancamiento de ingeniería por dólar de ingreso, ya que una sola integración sirve a toda la base de usuarios de un broker; se apoya en el diferenciador real de Luarix (construcción por lenguaje natural + nodos), algo que MetaTrader no ofrece de forma nativa.
Contras: ciclos de venta empresarial largos; exige garantías de disponibilidad y soporte de nivel empresarial; compite contra un incumbente con posición dominante establecida.

**Línea 5 — Modelo "prop firm" (evaluación + cuenta fondeada)**

Cliente objetivo: traders externos que pagan por demostrar disciplina y acceder a capital "fondeado".
Mecanismo de ingreso: fee de evaluación (la mayoría no pasa) + reparto de beneficio con quienes sí pasan.
Comparable: FTMO — USD 329M de ingresos en 2024 (+53% interanual), ~USD 62.5M de beneficio neto, más de 2.3M de cuentas abiertas, USD 450M+ pagados a traders en 10 años — **[FTMO]**.
Nota de riesgo, con la misma honestidad que rige todo este documento: es el modelo de mayor margen de las seis líneas —porque el ingreso depende más de fees de evaluación que de capital propio en riesgo—, pero también el de mayor riesgo reputacional y regulatorio: el sector vivió una consolidación fuerte en 2024, con decenas de firmas cerrando tras un endurecimiento de plataforma y regulatorio, y hay antecedentes de casos sancionados por reguladores en Estados Unidos por prácticas fraudulentas bajo el mismo modelo — **[Prop-trading]**. Es una línea atractiva solo si se opera con una estructura de cumplimiento sólida desde el inicio.
Pros: márgenes extraordinarios; encaja de forma natural con el motor de gobierno de riesgo de Luarix, porque evaluar disciplina es, literalmente, lo que ya audita el Capítulo 7.
Contras: riesgo reputacional/regulatorio real y documentado en el sector; depende de marketing de adquisición a escala, un músculo distinto al de ingeniería.

**Línea 6 — Señales y datos como servicio (mención breve)**

Cliente objetivo: traders o instituciones que quieren el output del motor SMC sin ejecutar a través de Luarix.
Mecanismo de ingreso: suscripción a señales o acceso a datos vía API.
Es una línea complementaria de menor escala, natural una vez que cualquiera de las Líneas 1-5 esté en marcha —el motor que las alimenta a todas es el mismo—, pero no se desarrolla aquí como prioridad independiente.

### 13.3 Comparativa resumida

| Línea | Cliente | Comparable de mercado | Intensidad de capital | Barrera regulatoria | Time-to-revenue | Escalabilidad | Alineación con v1.0 |
|---|---|---|---|---|---|---|---|
| 1. Gestión de capital de terceros | Fondos, family offices | Hedge funds, CTAs, Numerai | Baja (opera con capital de terceros) | Alta | Media | Media (limitada por AUM gestionable) | Alta — usa el motor tal cual |
| 2. Tecnología para traders profesionales | Traders/CTAs profesionales | Darwinex, Alpaca | Baja | Media (recae parcialmente en el trader licenciado) | Media-larga | Alta | Media — requiere producto multiusuario |
| 3. Retail | Traders individuales | 3Commas, Cryptohopper, Composer | Baja | Baja (no custodio) | Corta | Alta, con CAC alto | Media — requiere producto multiusuario y soporte |
| 4. Licenciamiento B2B/white-label | Brokers, prop firms | MetaQuotes, mercado white-label | Baja | Media | Larga | Muy alta | Baja hoy — requiere SLA/integración empresarial |
| 5. Modelo "prop firm" | Traders que buscan financiamiento | FTMO | Muy baja | Media-alta (riesgo reputacional) | Media | Muy alta | Media — el motor de riesgo ya evalúa disciplina |
| 6. Señales/datos | Traders e instituciones | Marketplaces de señales | Muy baja | Baja | Corta | Media | Alta, con ingreso menor |

### 13.4 Criterio personal: qué línea priorizar y en qué orden

Con criterio de trader, de inversionista y de arquitecto de software a la vez, la recomendación es **secuenciar, no elegir una sola línea de forma permanente**:

**Primero, Línea 1.** Es la que menos producto adicional exige sobre lo que la v1.0 ya entrega — no hace falta multiusuario, ni soporte, ni facturación self-service. Y genera el activo más valioso para todo lo demás: un **historial de rendimiento auditado**, exactamente lo que la auditoría por nodo y por operación del Capítulo 7 ya está construida para producir. Nadie asigna capital ni licencia tecnología a un sistema sin trayectoria — Línea 1 es la forma más corta de construir esa trayectoria con lo que ya existe.

**Después, Línea 2.** Con track record, la economía de licenciar la tecnología a otros traders profesionales es estructuralmente mejor que la de vender directo a retail: márgenes de software, ingreso recurrente, y una base de clientes que ya entiende de trading y necesita menos soporte por usuario que un cliente retail.

**Línea 3 (retail) y Línea 5 (prop firm), como opcionales de fase posterior, no como punto de partida.** Ambas tienen números atractivos en el mercado, pero por razones distintas ninguna es el mejor primer movimiento: retail exige el mayor gasto de adquisición y compite contra jugadores con años de ventaja en un segmento donde la mayoría de los usuarios pierde dinero por razones ajenas a la calidad de la herramienta; el modelo prop firm, pese a su margen excepcional, es el que más escrutinio reputacional y regulatorio atrae del sector, y solo tiene sentido perseguirlo desde una posición de credibilidad ya establecida — precisamente la que Línea 1 construye primero.

**Línea 4 (licenciamiento B2B) queda como la apuesta de mayor apalancamiento a mediano plazo**: es la que más ingreso genera por cada hora de ingeniería si se consigue, pero también la que más tiempo de venta empresarial exige y la que compite contra el jugador más dominante del sector — se persigue mejor una vez que Líneas 1 y 2 ya validaron el producto en el mercado.

**Línea 6 (señales) se activa sola**, como subproducto de cualquiera de las anteriores, no como estrategia independiente.

---

*Fin del Capítulo 13.*

---

## 14. Conclusiones

Luarix llega a su versión 1.0 con algo que pocos proyectos de trading automatizado en etapa temprana pueden mostrar: un motor de ejecución con auditoría real por nodo y por operación, un motor propio de estructura de mercado validado internamente, gobierno de riesgo que no depende de la disciplina del usuario sino que está construido dentro del propio motor, y un copiloto de inteligencia artificial que construye y cuestiona estrategias en el mismo lenguaje que usaría un trader, sincronizado en tiempo real con un editor visual. Ninguna plataforma revisada en el Capítulo 12 combina las cuatro cosas a la vez.

Esa combinación es la ventaja competitiva real de Luarix — no volumen, no años en el mercado, no una base de usuarios que hoy no tiene. El Capítulo 12 lo dice con toda intención: la comparación es de diseño y de capacidad, no de escala, porque en escala compite contra empresas que facturan cientos de millones de dólares al año. Cerrar esa brecha de escala es, precisamente, el objeto del Capítulo 13.

De las seis líneas de negocio evaluadas, la recomendación de este documento es clara: **empezar por gestionar capital de terceros (Línea 1)**, porque es la que menos exige del producto y la que más aporta a todo lo demás — construye el historial auditado que hace creíbles, después, la licencia de tecnología a traders profesionales (Línea 2) y, más adelante, cualquier otra línea que dependa de la confianza del mercado en Luarix. Retail y el modelo prop firm quedan disponibles, con números de mercado genuinamente atractivos, pero como fases posteriores — no porque sean negocios menores, sino porque exigen justo lo que Línea 1 todavía tiene que construir: marca, confianza y track record.

Este documento se sostiene en dos pilares que no van a cambiar aunque el negocio evolucione: el motor opera bajo el principio de que la seguridad del capital va antes que la rentabilidad (Capítulo 2), y ninguna cifra de este documento se afirma sin una fuente verificable detrás, listada en el Capítulo 15. Es el mismo rigor con el que se ha escrito cada capítulo anterior, aplicado ahora también a cómo Luarix se compara con el mercado y a cómo decide, con los ojos abiertos, en qué negocio quiere convertirse.

---

*Fin del Capítulo 14.*

---

## 15. Referencias

Todas las cifras de mercado y de competidores citadas en los Capítulos 12 y 13 provienen de las fuentes listadas aquí, agrupadas por tema. Las cifras de mercado varían de forma significativa entre firmas de investigación según la definición exacta del segmento medido; donde esa dispersión es relevante, se cita el rango completo en vez de un único número. Todas las fuentes se consultaron en julio de 2026.

### Competidores

- **[eToro]** — Business of Apps, "eToro Revenue and Usage Statistics", businessofapps.com/data/etoro-statistics (2026); eToro Investor Relations, "eToro Reports Fourth Quarter and Full Year 2025 Results", investors.etoro.com (2026); MacroTrends, "eToro Group Revenue 2024-2025 (ETOR)", macrotrends.net (2026).
- **[TradingView]** — Tracxn, "TradingView — Funding Rounds & List of Investors", tracxn.com (2026); TradingView Blog, "TradingView AI Chart Copilot: public beta is available now", tradingview.com/blog (2026).
- **[MetaQuotes]** — Finance Magnates, "Exclusive: MetaQuotes to Increase MetaTrader Licensing Fees Next Month by 'At Least 20%'", financemagnates.com (2025); B2Broker, "What Is MetaQuotes White Label, and How Does it Work?", b2broker.com (2025).
- **[FTMO]** — Finance Magnates, "FTMO's Parent Netted Over $62 Million on $329M Revenue in 2024", financemagnates.com (2025); JoinProp, "FTMO Posts $329 Million In 2024 Revenue As Prop Trading Reaches Institutional Scale", joinprop.com (2025); Finance Magnates, "FTMO Announces Over $450 Million Paid Out as Prop Trading Firm Turns 10", financemagnates.com (2025).
- **[3Commas/Cryptohopper/Coinrule]** — CoinGape, "3Commas Case Study: Could AI Trading Bots Disrupt Existing Trading Gains/ROI?", coingape.com (2026); altFINS, "Best Crypto Trading Bots in 2025: Coinrule vs Cryptohopper vs 3Commas", altfins.com (2025).
- **[Composer]** — BusinessWire, "Composer Supercharges Investing Platform with New 'Trade With AI' Tool", businesswire.com (2025); Alpaca Markets Blog, "How Composer is Redefining Algorithmic Trading with Their No-Code Platform", alpaca.markets/blog (2025).
- **[NexusTrade]** — recopilación agregada de mercado sobre plataformas no-code de trading con IA (NexusTrade, AlgoBuilder, Pineify), 2026.
- **[QuantConnect]** — QuantConnect, "About", quantconnect.com (2026); Wikipedia, "QuantConnect", en.wikipedia.org (2026).
- **[Alpaca]** — TechCrunch, "Alpaca raises $52M Series C to take its API brokerage platform to new markets", techcrunch.com (2025); BusinessWire, "Alpaca Raises $150 Million at a $1.15B Valuation to Build the Global Standard for Brokerage Infrastructure", businesswire.com (2026); Sacra, "Alpaca revenue, funding & news", sacra.com (2026).
- **[Darwinex]** — Darwinex, "Become Investable" / "About Us", darwinex.com (2026).
- **[Numerai]** — fintech.global, "Numerai lands $30m to scale AI-powered hedge fund", fintech.global (2025); ainvest, "Numerai's AI-Crowdsourced 'Last Hedge Fund' Scales to $500M Valuation", ainvest.com (2025).
- **[Interactive Brokers]** — MacroTrends, "Interactive Brokers Revenue 2012-2025 (IBKR)", macrotrends.net (2026).
- **[TrendSpider/Trade Ideas]** — StockBrokers.com, "TrendSpider Review 2026" y "Trade Ideas Review 2026", stockbrokers.com (2026).

### Tamaño de mercado

- **[Algo-trading]** — Fortune Business Insights, "Algorithmic Trading Market Size, Share, Industry Report 2034", fortunebusinessinsights.com (2026); Research and Markets, "Automated Algo Trading Market Report 2026", researchandmarkets.com (2026); Technavio, "Algorithmic Trading Market Growth Analysis - Size and Forecast 2026-2030", technavio.com (2026).
- **[Copy-trading]** — GrowthMarketReports, "Copy Trading Platform Market Research Report 2033", growthmarketreports.com (2026).
- **[Prop-trading]** — Track360, "Prop Trading Industry Size 2026: $850M Market Analysis", track360.io (2026).
- **[Hedge-funds]** — HFR, "Global Hedge Fund Industry Capital Surges Past Historic $5 Trillion Milestone", hfr.com (2026); Hedgeweek, "Hedge fund AUM hits record $4.74tn AUM as inflows surge to decade high", hedgeweek.com (2025).
- **[Managed-futures]** — IASG, "Managed Futures Screener & CTA Database", iasg.com (2026).
- **[Robo-advisors]** — Condor Capital Wealth Management, "2024 AUM Growth", condorcapital.com (2025); Grand View Research, "Robo Advisory Market Size, Share & Growth Report, 2030", grandviewresearch.com (2026).
- **[White-label]** — MarketGrowthReports, "Brokerage Trading Platforms Software Market Size, Share - Forecast To 2034", marketgrowthreports.com (2026).
- **[VC-fintech]** — Crunchbase News, "Fintech Forecast: Momentum Builds With Big Deals, IPO-Ready Companies And More AI", news.crunchbase.com (2026).

### Modelos de negocio y regulación

- **[Pérdidas-retail]** — GoodMoneyGuide, "CFD Broker Client Trading Loss Risk Warning Statistics", goodmoneyguide.com (2026), agregando divulgaciones obligatorias de ESMA/FCA/CFTC.
- **[Fees-hedge-fund]** — Tokenist, "2 and 20 Hedge Fund Fees Explained: Worth it in 2025?", tokenist.com (2025).
- **[MiCA]** — ItisPay, "MiCA CASP License Cost 2026: Full Breakdown", itispay.com (2026); AMLBot Blog, "MiCA License Explained: CASP Requirements, Authorization & EU Passporting", blog.amlbot.com (2026).

---

*Fin del Capítulo 15.*

---

*Fin del documento institucional de Luarix — versión actual. Próxima revisión: cuando el proyecto lo requiera.*
