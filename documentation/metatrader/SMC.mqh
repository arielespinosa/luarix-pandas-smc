//+------------------------------------------------------------------+
//| SMC.mqh                                                          |
//| Réplica de las funciones SMC en strategy.py                     |
//| exist_equals(), exist_orderblock()                               |
//+------------------------------------------------------------------+
#ifndef SMC_MQH
#define SMC_MQH

//+------------------------------------------------------------------+
//| exist_equals                                                     |
//| Réplica de exist_equals(tick, context) en strategy.py           |
//|                                                                  |
//| Detecta Equal Lows: dos mínimos similares dentro del umbral      |
//| cuya zona fue barrida por el tick actual (low < eql_price).     |
//| Solo busca setup LONG (equal lows = liquidez alcista).           |
//|                                                                  |
//| Retorna: precio del equal low barrido, o 0.0 si no existe       |
//+------------------------------------------------------------------+
double exist_equals(string symbol, ENUM_TIMEFRAMES tf,
                    int eq_length, double eq_thresh)
  {
   int    total = eq_length * 2 + 1;
   double lows[];
   ArraySetAsSeries(lows, true);
   if(CopyLow(symbol, tf, 0, total, lows) != total)
      return 0.0;

   // Mínimo ventana reciente [0 .. eq_length-1]
   double low1 = lows[0];
   for(int i = 1; i < eq_length; i++)
      if(lows[i] < low1) low1 = lows[i];

   // Mínimo ventana anterior [eq_length .. 2*eq_length-1]
   double low2 = lows[eq_length];
   for(int i = 1; i < eq_length; i++)
      if(lows[eq_length + i] < low2) low2 = lows[eq_length + i];

   if(low2 == 0.0) return 0.0;

   // Verificar igualdad dentro del umbral
   if(MathAbs(low1 - low2) / low2 >= eq_thresh) return 0.0;

   double eql_price = MathMin(low1, low2);

   // Barrido: el low actual rompió por debajo del nivel (liquidez tomada)
   // Réplica de: if eql.price > tick.low → return eql
   bool swept = lows[0] < eql_price;
   return swept ? eql_price : 0.0;
  }

//+------------------------------------------------------------------+
//| exist_orderblock                                                  |
//| Réplica de exist_orderblock(tick, context) en strategy.py       |
//|                                                                  |
//| Un OB alcista = última vela bajista antes de impulso alcista,    |
//| situada debajo del EQL, cuyo rango no ha sido mitigado.          |
//|                                                                  |
//| Actualiza ob_top, ob_bot, ob_valid por referencia.              |
//| Retorna: true si hay OB activo                                   |
//+------------------------------------------------------------------+
bool exist_orderblock(string symbol, ENUM_TIMEFRAMES tf,
                      double eql_price,
                      double &ob_top, double &ob_bot, bool &ob_valid)
  {
   // Sin equal low activo → no hay OB que buscar
   // Réplica de: if not equal: return None
   if(eql_price == 0.0)
     {
      ob_valid = false;
      return false;
     }

   // Últimas 3 velas: [0]=actual [1]=anterior [2]=previa
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(symbol, tf, 0, 3, rates) != 3)
      return ob_valid;

   // Condiciones para nuevo OB (réplica de la detección en Python/SMCIndicator)
   bool bearish_candle  = rates[1].close < rates[1].open;   // vela [1] bajista
   bool bullish_impulse = rates[0].close > rates[1].open;   // impulso alcista desde [1]
   bool below_eql       = rates[1].high  < eql_price;       // OB debajo del equal low

   // Mitigación: precio actual entró en el rango del OB previo
   // Réplica de: if ob.mitigated: continue
   bool mitigated = ob_valid
                    && rates[0].low <= ob_top
                    && rates[0].low >= ob_bot;

   if(mitigated)
     {
      ob_valid = false;
      ob_top   = 0.0;
      ob_bot   = 0.0;
      return false;
     }

   if(bearish_candle && bullish_impulse && below_eql)
     {
      ob_top   = rates[1].open;    // techo = open de la vela bajista
      ob_bot   = rates[1].close;   // suelo = close de la vela bajista
      ob_valid = true;
     }

   return ob_valid;
  }

#endif // SMC_MQH
