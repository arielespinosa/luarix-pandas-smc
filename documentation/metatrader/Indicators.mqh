//+------------------------------------------------------------------+
//| Indicators.mqh                                                   |
//| Réplica de bbands.py + stochastic_oscillator.py                 |
//| Wrappers sobre indicadores nativos MT5                           |
//+------------------------------------------------------------------+
#ifndef INDICATORS_MQH
#define INDICATORS_MQH

//+------------------------------------------------------------------+
//| BB50 — réplica de bb50() en bbands.py                           |
//| Bollinger Bands 50 períodos, 2 desviaciones estándar             |
//+------------------------------------------------------------------+

//--- Crear handle del indicador (llamar en OnInit)
int BB50_Init(string symbol, ENUM_TIMEFRAMES tf)
  {
   return iBands(symbol, tf, 50, 0, 2.0, PRICE_CLOSE);
  }

//--- Obtener upper/middle/lower para una barra (shift=0 → barra actual)
//--- Réplica de bb50(close_series) → (upper, middle, lower)
bool BB50_Get(int handle, double &upper, double &middle, double &lower, int shift = 0)
  {
   double u[1], m[1], l[1];
   if(CopyBuffer(handle, 0, shift, 1, u) != 1) return false;  // upper
   if(CopyBuffer(handle, 1, shift, 1, m) != 1) return false;  // middle (SMA50)
   if(CopyBuffer(handle, 2, shift, 1, l) != 1) return false;  // lower
   upper  = u[0];
   middle = m[0];
   lower  = l[0];
   return true;
  }

//+------------------------------------------------------------------+
//| Stochastic — réplica de stochastic_oscillator.py                |
//| Port de Pine Script v3: K=14, D=3, slowing=3, SMA, Low/High    |
//+------------------------------------------------------------------+

//--- Crear handle del indicador (llamar en OnInit)
int Stoch_Init(string symbol, ENUM_TIMEFRAMES tf)
  {
   return iStochastic(symbol, tf, 14, 3, 3, MODE_SMA, STO_LOWHIGH);
  }

//--- Obtener slow_k para una barra
//--- Réplica de stoch["slow_k"].iloc[-1]
bool Stoch_K(int handle, double &slow_k, int shift = 0)
  {
   double buf[1];
   if(CopyBuffer(handle, 0, shift, 1, buf) != 1) return false;
   slow_k = buf[0];
   return true;
  }

//--- Obtener array de slow_k para 'count' barras (más reciente en índice 0)
//--- Réplica del slice stoch["slow_k"] usado en divergencia
bool Stoch_K_Array(int handle, double &out[], int count)
  {
   ArrayResize(out, count);
   ArraySetAsSeries(out, true);
   return CopyBuffer(handle, 0, 0, count, out) == count;
  }

#endif // INDICATORS_MQH
