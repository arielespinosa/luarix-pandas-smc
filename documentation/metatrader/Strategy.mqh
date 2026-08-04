//+------------------------------------------------------------------+
//| Strategy.mqh                                                     |
//| Réplica de strategy.py — scoring, TP/SL, sizing                 |
//| stoch_oversold, stoch_divergence, bb50_entry_exist,             |
//| calc_strategy_score, calc_take_profit, calc_stop_loss,          |
//| calc_quantity                                                    |
//+------------------------------------------------------------------+
#ifndef STRATEGY_MQH
#define STRATEGY_MQH
#include "Indicators.mqh"

//+------------------------------------------------------------------+
//| stoch_oversold                                                   |
//| Réplica de is_stochastic_oscillator_in_over_sell(df)            |
//+------------------------------------------------------------------+
bool stoch_oversold(double slow_k)
  {
   return slow_k < 20.0;
  }

//+------------------------------------------------------------------+
//| stoch_divergence                                                 |
//| Réplica de stochastic_oscillator_have_divergence(df)            |
//|                                                                  |
//| Divergencia alcista LONG:                                        |
//|   precio hace mínimo más bajo, estocástico hace mínimo más alto  |
//+------------------------------------------------------------------+
bool stoch_divergence(string symbol, ENUM_TIMEFRAMES tf,
                      int stoch_handle, int div_len)
  {
   double closes[];
   ArraySetAsSeries(closes, true);
   if(CopyClose(symbol, tf, 0, div_len, closes) != div_len) return false;

   double slow_k[];
   if(!Stoch_K_Array(stoch_handle, slow_k, div_len)) return false;

   int mid = div_len / 2;

   // 1ª mitad = barras más recientes [0 .. mid-1]
   double price_l1 = closes[0],   k_l1 = slow_k[0];
   for(int i = 1; i < mid; i++)
     {
      if(closes[i]  < price_l1) price_l1 = closes[i];
      if(slow_k[i]  < k_l1)    k_l1     = slow_k[i];
     }

   // 2ª mitad = barras más antiguas [mid .. div_len-1]
   double price_l2 = closes[mid], k_l2 = slow_k[mid];
   for(int i = 1; i < mid; i++)
     {
      if(closes[mid + i]  < price_l2) price_l2 = closes[mid + i];
      if(slow_k[mid + i]  < k_l2)    k_l2     = slow_k[mid + i];
     }

   // Réplica de: close_low_second < close_low_first and k_low_second > k_low_first
   // (second = más antiguo = l2, first = más reciente = l1)
   return (price_l1 < price_l2) && (k_l1 > k_l2);
  }

//+------------------------------------------------------------------+
//| bb50_entry_exist                                                 |
//| Réplica de bb50_entry_exist(tick, df, context) — solo LONG      |
//+------------------------------------------------------------------+
bool bb50_entry_exist(double current_close, double bb_lower)
  {
   return current_close <= bb_lower;
  }

//+------------------------------------------------------------------+
//| calc_strategy_score                                              |
//| Réplica de calc_strategy_score(tick, df, context)               |
//| Sistema de puntuación 0-80. Umbral de entrada: > 50             |
//+------------------------------------------------------------------+
int calc_strategy_score(double eql_price, bool ob_valid,
                        bool div_bull, bool stoch_os, bool bb_entry)
  {
   int score = 0;
   if(eql_price > 0.0) score += 30;  // Equal Lows barridos
   if(ob_valid)        score += 20;  // Order Block presente
   if(div_bull)        score += 15;  // Divergencia alcista estocástico
   if(bb_entry)        score += 10;  // Precio ≤ BB50 banda inferior
   if(stoch_os)        score +=  5;  // Sobreventa (slow_k < 20)
   return score;
  }

//+------------------------------------------------------------------+
//| calc_take_profit                                                 |
//| Réplica de calc_take_proffit(entry, candle_df)                  |
//| TP = min(precio × (1 + tp_pct), bb50_middle)                   |
//+------------------------------------------------------------------+
double calc_take_profit(double entry_price, double tp_pct, double bb_middle)
  {
   double tp_by_pct = entry_price * (1.0 + tp_pct);
   return (bb_middle > 0.0 && bb_middle < tp_by_pct) ? bb_middle : tp_by_pct;
  }

//+------------------------------------------------------------------+
//| calc_stop_loss                                                   |
//| Réplica de calc_stop_loss(context, entry)                       |
//+------------------------------------------------------------------+
void calc_stop_loss(double entry_price, double sl_pct, double sl_limit_pct,
                    double &stop_price, double &stop_limit_price)
  {
   stop_price       = entry_price * (1.0 - sl_pct);
   stop_limit_price = entry_price * (1.0 - sl_limit_pct);
  }

//+------------------------------------------------------------------+
//| calc_quantity                                                    |
//| Réplica de calc_quantity(price, capital, percent)               |
//| Devuelve volumen normalizado al step del símbolo                 |
//+------------------------------------------------------------------+
double calc_quantity(string symbol, double price, double capital, double percent)
  {
   double raw      = (capital * percent) / price;
   double min_vol  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double step_vol = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   int    digits   = (int)MathRound(-MathLog10(step_vol));

   double lot = MathFloor(raw / step_vol) * step_vol;
   lot = MathMax(lot, min_vol);
   return NormalizeDouble(lot, digits);
  }

#endif // STRATEGY_MQH
