Estrategia IPDA Luis  

1. Filosofía principal del sistema
La estrategia NO busca predecir el mercado. Busca explotar desequilibrios probabilísticos derivados de:  
● Liquidez institucional  
● Volatilidad extrema  
● Contexto temporal HTF  
● Timing reactivo  
El objetivo es construir un sistema con ventaja estadística repetible, no un bot que adivine el precio.  

2. Contexto temporal macro
La estrategia utiliza una estructura temporal anual/semestral:  
● Primer semestre: alto y bajo de la vela semestral.  
● Segundo semestre: alto y bajo de la vela anual.  
Esto permite determinar:  
● Dirección dominante  
● Intención institucional  
● Probabilidad direccional   
La lógica no es predictiva; es contextual y probabilística.  

3. Temporalidad mensual
En mensual no se buscan entradas. Se construye un mapa institucional del mercado. Se marcan:  
● Order Blocks de fractales  
● Oferta (alto del fractal)  
● Demanda (bajo del fractal)  
Estas zonas funcionan como referencias institucionales HTF.  

4. Temporalidad diaria
La temporalidad diaria es el núcleo operativo del sistema. Se identifican:
● Altos iguales  
● Bajos iguales  
● Fractales relevantes  
● Liquidez cercana    
Indicadores principales:  
● BB50   
● Volumen Oscillator    

5. Lógica direccional
La dirección HTF filtra todas las operaciones.  
● En contexto bajista:  
○ Prioridad a ventas  
○ Compras solo tras barridas de liquidez  
● En contexto alcista:  
○ Prioridad a compras  
○ Ventas solo tras barridas de liquidez  

6. Entradas Short  
Confluencias necesarias:  
● Banda superior BB50  
● Liquidez superior  
● Order Block Oscillator en sobrecompra o Divergencia bajista  
Preferiblemente entrada de volumen. Evitar ventas directamente sobre altos iguales no barridos.  

7. Entradas Long contratendencia  
Solo se permiten compras tras barrida de liquidez. Confluencias:  
● Sweep por debajo del fractal o bajo igual  
● Banda inferior BB50  
● Oscillator en sobreventa o divergencia alcista  
● Reacción rápida institucional  

8. EMA media del BB50 (7 indicadores)  
También se ejecutan operaciones sobre la EMA media del BB50 cuando coinciden:  
● Dirección HTF  
● Order Block  
● Oscillator extremo (RSI)  
● Contexto favorable  

9. Gestión del sistema  
El objetivo es capturar volatilidad rápida y minimizar tiempo de exposición. Distribución en entradas:  
● 30% entrada inicial  
● 40% confirmación  
● 30% continuación  

10. Stop Loss dinámico  
El Stop Loss NO debe ser fijo. Debe basarse en:  
● Estructura  
● Liquidez  
● Fractales  
● Invalidación real  
● Además se incorpora ATR dinámico como buffer adaptativo de volatilidad.  


----------------------------Otros datos de interes y configuración---------------------------------------

BB50:
- Media central = SMA(close, 50)
- Desviación = desviación estándar de los últimos 50 cierres
- Banda superior = SMA50 + 2 × desviación
- Banda inferior = SMA50 - 2 × desviación

Precio cerca de banda:
- Cerca banda superior si: abs(close - banda_superior) / close <= 0.005
- Cerca banda inferior si: abs(close - banda_inferior) / close <= 0.005

Liquidez:  
- Máximos iguales:
- Dos máximos son iguales si: abs(high1 - high2) / high1 <= 0.003

Mínimos iguales:  
- Dos mínimos son iguales si: abs(low1 - low2) / low1 <= 0.003

ATR Stop Loss: 
- ATR = ATR(14)

Compra: SL = min(OB_low, último swing low) - 0.5 × ATR
Venta: SL = max(OB_high, último swing high) + 0.5 × ATR

Explicación sencilla de la estrategia LUARIX

Objetivo

La estrategia intenta ponerse del lado del dinero institucional. No busca adivinar el mercado ni entrar en cualquier movimiento, sino esperar pacientemente a que coincan varios factores que aumenten la probabilidad de éxito.

Cómo piensa la estrategia:  
Imagina que el mercado es una carretera. No queremos subirnos al coche en mitad de la autopista. Queremos esperar a que llegue a una zona donde sea más probable que vuelva a arrancar en la dirección principal.

Por eso la estrategia siempre sigue el mismo proceso:

1. Primero identifica la dirección  
Lo primero que hace es preguntarse: ¿Hacia dónde quiere ir realmente el mercado?  
Si el mercado está subiendo, solo buscará compras.  
Si está bajando, solo buscará ventas.    
Nunca intenta luchar contra la tendencia principal.

⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

2. Después busca las zonas donde probablemente actúe el dinero institucional.  
No cualquier precio es interesante. La estrategia marca zonas donde históricamente los grandes participantes suelen dejar órdenes, como:

* Order Blocks.
* Zonas de oferta y demanda.
* Liquidez.
* Máximos y mínimos importantes.  

  Estas zonas funcionan como posibles puntos de reacción.

⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

3. Espera a que el precio llegue  
Aquí la estrategia no hace nada.  
Puede pasar horas o incluso días esperando.  
No persigue el precio.  
Es el precio el que debe venir hasta la zona que interesa.  

⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

4. Utiliza la BB50 como filtro  
La BB50 no dice cuándo comprar o vender. Simplemente ayuda a saber si el precio está demasiado alejado de su comportamiento normal o si se encuentra en una posición más favorable para buscar una entrada. Es un filtro adicional que aumenta la calidad de la operación.

⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

5. Espera una confirmación.  
   Aunque el precio llegue a un Order Block, todavía no entra.

Primero necesita que el propio mercado confirme que realmente quiere girarse o continuar.

Para eso observa cambios de estructura como CHoCH o BOS.

Solo cuando el mercado demuestra esa intención se plantea la entrada.

⸻

1. Calcula la calidad de la operación

Cada elemento suma confianza.

Por ejemplo:

* Tendencia alineada.
* Order Block válido.
* BB50 favorable.
* Liquidez cercana.
* CHoCH.
* BOS.
* Volumen.

Cuantas más condiciones coincidan, mayor será la puntuación de la operación.

Si la puntuación es baja, simplemente no opera.

⸻

7. Gestiona automáticamente el riesgo

Antes de abrir cualquier operación ya sabe:

* Dónde está el Stop Loss.
* Dónde están los objetivos.
* Qué relación beneficio/riesgo tiene.

Nunca entra sin conocer el riesgo que está asumiendo.

⸻

Filosofía de la estrategia

La estrategia no pretende operar mucho.

Prefiere dejar pasar diez oportunidades antes que entrar en una mala.

Su objetivo es operar únicamente cuando coinciden suficientes factores que indiquen que la probabilidad está a favor.

En otras palabras:

No busca encontrar todas las operaciones del mercado.

Busca encontrar únicamente las mejores.