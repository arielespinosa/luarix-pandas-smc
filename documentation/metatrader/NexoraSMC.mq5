//+------------------------------------------------------------------+
//| NexoraSMC.mq5                                                    |
//| Expert Advisor — Réplica de pipeline.py                         |
//|                                                                  |
//| Flujo:                                                           |
//|   OnInit()              ≡ _setup()                              |
//|   InitIpdaContext()     ≡ strategy() + initialize_ipda_...      |
//|   On4HBar()             ≡ on_4h_kline()                         |
//|   OnTradeTransaction()  ≡ on_order_status_change()              |
//|   create_entries()      ≡ create_entries()                       |
//|                                                                  |
//| Aplicar en BTCUSDT (o cualquier par) en gráfico 4H.            |
//+------------------------------------------------------------------+
#property copyright "Nexora Trading Framework"
#property version   "1.00"
#property strict

#include "Models.mqh"
#include "Indicators.mqh"
#include "SMC.mqh"
#include "Strategy.mqh"

//==========================================================================
// INPUTS (≡ config/settings.py)
//==========================================================================
input group           "Risk Management"
input double          InpCapital       = 1000.0;  // Capital base (USDT)
input double          InpTPPct         = 6.0;     // Take Profit %
input double          InpSLPct         = 2.0;     // Stop Loss %
input double          InpSLLimitPct    = 2.2;     // Stop Limit %

input group           "Strategy"
input int             InpScoreThresh   = 50;      // Umbral de score (> N para entrar)

input group           "SMC Detection"
input int             InpEqLength      = 3;       // Barras para Equal Lows
input double          InpEqThresh      = 0.25;    // Umbral EQL % (0.25 = 0.25%)
input int             InpDivLen        = 20;      // Barras para divergencia

input group           "IPDA Lookback"
input int             InpAnnualDays    = 252;     // Días para annual high/low
input int             InpSemesterDays  = 126;     // Días para semester high/low

input group           "EA Settings"
input ulong           InpMagic         = 202401;  // Número mágico del EA

//==========================================================================
// GLOBALS
//==========================================================================
StrategyContext g_context;

int             g_bb50_handle  = INVALID_HANDLE;
int             g_stoch_handle = INVALID_HANDLE;
int             g_sma200_handle = INVALID_HANDLE;

datetime        g_last_bar_time = 0;   // Detector de nueva barra 4H
datetime        g_last_daily    = 0;   // Detector de nuevo día

//==========================================================================
// OnInit — réplica de _setup()
//==========================================================================
int OnInit()
  {
   g_bb50_handle   = BB50_Init(_Symbol, PERIOD_H4);
   g_stoch_handle  = Stoch_Init(_Symbol, PERIOD_H4);
   g_sma200_handle = iMA(_Symbol, PERIOD_H4, 200, 0, MODE_SMA, PRICE_CLOSE);

   if(g_bb50_handle   == INVALID_HANDLE ||
      g_stoch_handle  == INVALID_HANDLE ||
      g_sma200_handle == INVALID_HANDLE)
     {
      Print("Error inicializando indicadores: ", GetLastError());
      return INIT_FAILED;
     }

   InitIpdaContext();

   Print("NexoraSMC iniciado. Symbol=", _Symbol,
         " Annual H=", g_context.annual_high,
         " Annual L=", g_context.annual_low);
   return INIT_SUCCEEDED;
  }

//==========================================================================
// OnDeinit
//==========================================================================
void OnDeinit(const int reason)
  {
   if(g_bb50_handle   != INVALID_HANDLE) IndicatorRelease(g_bb50_handle);
   if(g_stoch_handle  != INVALID_HANDLE) IndicatorRelease(g_stoch_handle);
   if(g_sma200_handle != INVALID_HANDLE) IndicatorRelease(g_sma200_handle);
  }

//==========================================================================
// InitIpdaContext — réplica de strategy() + initialize_ipda_target_elements()
// Calcula annual/semester high/low sobre datos diarios.
//==========================================================================
void InitIpdaContext()
  {
   int idx_ah = iHighest(_Symbol, PERIOD_D1, MODE_HIGH, InpAnnualDays,   0);
   int idx_al = iLowest(_Symbol,  PERIOD_D1, MODE_LOW,  InpAnnualDays,   0);
   int idx_sh = iHighest(_Symbol, PERIOD_D1, MODE_HIGH, InpSemesterDays, 0);
   int idx_sl = iLowest(_Symbol,  PERIOD_D1, MODE_LOW,  InpSemesterDays, 0);

   if(idx_ah >= 0) g_context.annual_high   = iHigh(_Symbol, PERIOD_D1, idx_ah);
   if(idx_al >= 0) g_context.annual_low    = iLow(_Symbol,  PERIOD_D1, idx_al);
   if(idx_sh >= 0) g_context.semester_high = iHigh(_Symbol, PERIOD_D1, idx_sh);
   if(idx_sl >= 0) g_context.semester_low  = iLow(_Symbol,  PERIOD_D1, idx_sl);
  }

//==========================================================================
// OnTick — detector de nueva vela 4H → delega en On4HBar()
//==========================================================================
void OnTick()
  {
   datetime bar_time = iTime(_Symbol, PERIOD_H4, 0);
   if(bar_time == g_last_bar_time) return;
   g_last_bar_time = bar_time;
   On4HBar();
  }

//==========================================================================
// On4HBar — réplica de on_4h_kline(msg)
// Se ejecuta una vez por cada vela 4H.
//==========================================================================
void On4HBar()
  {
   // Refrescar contexto IPDA al inicio de cada día
   datetime daily_time = iTime(_Symbol, PERIOD_D1, 0);
   if(daily_time != g_last_daily)
     {
      g_last_daily = daily_time;
      InitIpdaContext();
     }

   // Indicadores de la última vela cerrada (shift=1)
   double bb_upper, bb_middle, bb_lower;
   if(!BB50_Get(g_bb50_handle, bb_upper, bb_middle, bb_lower, 1)) return;

   double slow_k;
   if(!Stoch_K(g_stoch_handle, slow_k, 1)) return;

   double current_close = iClose(_Symbol, PERIOD_H4, 1);

   if(g_context.amount_of_entries() == 0)
     {
      // Sin entradas — buscar nueva oportunidad
      // Réplica de: if context.amount_of_entries == 0:

      // Contexto alcista: precio > SMA200 en 4H
      // Réplica de: if context.trend != Trend.BULLISH: return
      double sma200[1];
      if(CopyBuffer(g_sma200_handle, 0, 1, 1, sma200) != 1) return;
      if(current_close <= sma200[0]) return;

      // Detectar estructura SMC
      // Réplica de: exist_equals → exist_orderblock → calc_strategy_score
      double eql = exist_equals(_Symbol, PERIOD_H4, InpEqLength, InpEqThresh / 100.0);
      exist_orderblock(_Symbol, PERIOD_H4, eql,
                       g_context.ob_top, g_context.ob_bot, g_context.ob_valid);
      g_context.eql_price = eql;

      bool div_bull = stoch_divergence(_Symbol, PERIOD_H4, g_stoch_handle, InpDivLen);
      bool stoch_os = stoch_oversold(slow_k);
      bool bb_entry = bb50_entry_exist(current_close, bb_lower);

      int score = calc_strategy_score(eql, g_context.ob_valid, div_bull, stoch_os, bb_entry);

      PrintFormat("Score=%d EQL=%.5f OB=%s Div=%s OS=%s BB=%s",
                  score, eql,
                  g_context.ob_valid ? "Y" : "N",
                  div_bull ? "Y" : "N",
                  stoch_os ? "Y" : "N",
                  bb_entry ? "Y" : "N");

      // Réplica de: if score > 50: create_entries(...)
      if(score > InpScoreThresh && g_context.ob_valid)
         create_entries(bb_middle);
     }
   else
     {
      // Con entradas — actualizar TP/SL dinámico en posiciones FILLED
      // Réplica de: for entry in context.entries: if entry.status == FILLED: update_oco
      UpdateEntryPosition(g_context.entry_first_30, g_context.has_entry_first_30, bb_middle);
      UpdateEntryPosition(g_context.entry_40,       g_context.has_entry_40,       bb_middle);
      UpdateEntryPosition(g_context.entry_last_30,  g_context.has_entry_last_30,  bb_middle);
     }
  }

//==========================================================================
// UpdateEntryPosition — réplica del update OCO en on_4h_kline() (bloque else)
// Actualiza TP dinámico (BB50 middle) y SL fijo en la posición abierta.
//==========================================================================
void UpdateEntryPosition(Entry &e, bool has_it, double bb_middle)
  {
   if(!has_it || e.status != FILLED || e.position_ticket == 0) return;

   double sl_price, sl_limit;
   calc_stop_loss(e.price, InpSLPct / 100.0, InpSLLimitPct / 100.0, sl_price, sl_limit);
   double tp_price = calc_take_profit(e.price, InpTPPct / 100.0, bb_middle);

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action   = TRADE_ACTION_SLTP;
   req.symbol   = _Symbol;
   req.position = e.position_ticket;
   req.sl       = NormalizeDouble(sl_price, _Digits);
   req.tp       = NormalizeDouble(tp_price, _Digits);
   if(!OrderSend(req, res))
      PrintFormat("Error actualizando TP/SL ticket=%d: %d", e.position_ticket, res.retcode);
  }

//==========================================================================
// create_entries — réplica de create_entries() en strategy.py
// Coloca 3 órdenes LIMIT con TP/SL calculados al momento de la señal.
//==========================================================================
void create_entries(double bb_middle)
  {
   double ob_top = g_context.ob_top;
   double ob_bot = g_context.ob_bot;

   double t1_price = ob_top;                   // Tranche 1 — techo del OB
   double t2_price = (ob_top + ob_bot) / 2.0; // Tranche 2 — midpoint (bug corregido)
   double t3_price = ob_bot;                   // Tranche 3 — suelo del OB

   PlaceLimitEntry(t1_price, 0.3, bb_middle,
                   g_context.entry_first_30, g_context.has_entry_first_30, "T1 OB Top");
   PlaceLimitEntry(t2_price, 0.4, bb_middle,
                   g_context.entry_40, g_context.has_entry_40, "T2 OB Mid");
   PlaceLimitEntry(t3_price, 0.3, bb_middle,
                   g_context.entry_last_30, g_context.has_entry_last_30, "T3 OB Bot");
  }

//==========================================================================
// PlaceLimitEntry — helper para create_entries
// Coloca una orden BUY LIMIT y rellena la Entry en el contexto.
//==========================================================================
void PlaceLimitEntry(double price, double capital_pct, double bb_middle,
                     Entry &e, bool &has_entry, string comment_str)
  {
   double sl_price, sl_limit;
   calc_stop_loss(price, InpSLPct / 100.0, InpSLLimitPct / 100.0, sl_price, sl_limit);
   double tp_price = calc_take_profit(price, InpTPPct / 100.0, bb_middle);

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action       = TRADE_ACTION_PENDING;
   req.symbol       = _Symbol;
   req.type         = ORDER_TYPE_BUY_LIMIT;
   req.type_time    = ORDER_TIME_GTC;
   req.type_filling = ORDER_FILLING_RETURN;
   req.magic        = InpMagic;
   req.deviation    = 10;
   req.volume       = calc_quantity(_Symbol, price, InpCapital, capital_pct);
   req.price        = NormalizeDouble(price,    _Digits);
   req.sl           = NormalizeDouble(sl_price, _Digits);
   req.tp           = NormalizeDouble(tp_price, _Digits);
   req.comment      = comment_str;

   if(OrderSend(req, res) && res.retcode == TRADE_RETCODE_PLACED)
     {
      e.ticket    = res.order;
      e.price     = price;
      e.volume    = req.volume;
      e.tp_price  = tp_price;
      e.sl_price  = sl_price;
      e.side      = ORDER_TYPE_BUY_LIMIT;
      e.status    = WAITING;
      e.start     = TimeCurrent();
      has_entry   = true;
      PrintFormat("%s colocado: ticket=%d price=%.5f vol=%.4f tp=%.5f sl=%.5f",
                  comment_str, res.order, price, req.volume, tp_price, sl_price);
     }
   else
      PrintFormat("Error %s: retcode=%d %s", comment_str, res.retcode, res.comment);
  }

//==========================================================================
// MarkEntryStatus — helper para OnTradeTransaction
// Actualiza el estado de la entrada indicada por índice (0/1/2).
//==========================================================================
void MarkEntryStatus(int idx, EntryStatus new_status, ulong pos_ticket)
  {
   if(idx == 0)
     {
      g_context.entry_first_30.status         = new_status;
      g_context.entry_first_30.end            = TimeCurrent();
      if(pos_ticket > 0) g_context.entry_first_30.position_ticket = pos_ticket;
     }
   else if(idx == 1)
     {
      g_context.entry_40.status               = new_status;
      g_context.entry_40.end                  = TimeCurrent();
      if(pos_ticket > 0) g_context.entry_40.position_ticket = pos_ticket;
     }
   else if(idx == 2)
     {
      g_context.entry_last_30.status          = new_status;
      g_context.entry_last_30.end             = TimeCurrent();
      if(pos_ticket > 0) g_context.entry_last_30.position_ticket = pos_ticket;
     }
  }

//==========================================================================
// FindEntryByPositionTicket — helper para OnTradeTransaction (cierre)
// Busca qué tranche tiene el position_ticket indicado.
// Retorna índice 0/1/2 o -1 si no encontrado.
//==========================================================================
int FindEntryByPositionTicket(ulong pos_ticket)
  {
   if(g_context.has_entry_first_30 && g_context.entry_first_30.position_ticket == pos_ticket) return 0;
   if(g_context.has_entry_40       && g_context.entry_40.position_ticket       == pos_ticket) return 1;
   if(g_context.has_entry_last_30  && g_context.entry_last_30.position_ticket  == pos_ticket) return 2;
   return -1;
  }

//==========================================================================
// OnTradeTransaction — réplica de on_order_status_change(msg)
//
// DEAL_ENTRY_IN  → orden LIMIT ejecutada (entrada abierta)
//   - Busca la entrada por DEAL_ORDER (= order ticket)
//   - Actualiza status = FILLED, guarda position_ticket
//
// DEAL_ENTRY_OUT → posición cerrada por TP o SL
//   - Busca la entrada por DEAL_POSITION_ID (= position_ticket)
//   - DEAL_REASON_TP → status = TAKED → reset
//   - DEAL_REASON_SL → status = STOP_LOSS_BROKEN → reset si todas cerradas
//==========================================================================
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest     &request,
                        const MqlTradeResult      &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if((ulong)HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic) return;

   ENUM_DEAL_ENTRY  deal_entry  = (ENUM_DEAL_ENTRY) HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   ENUM_DEAL_REASON deal_reason = (ENUM_DEAL_REASON)HistoryDealGetInteger(trans.deal, DEAL_REASON);
   ulong            deal_order  = (ulong)HistoryDealGetInteger(trans.deal, DEAL_ORDER);
   ulong            deal_pos_id = (ulong)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
   double           deal_price  = HistoryDealGetDouble(trans.deal, DEAL_PRICE);

   if(deal_entry == DEAL_ENTRY_IN)
     {
      // Orden LIMIT ejecutada — réplica del bloque else en on_order_status_change
      // Buscar por order ticket
      int idx = g_context.get_entry_index_by_ticket(deal_order);
      if(idx < 0) return;

      // status = FILLED, guardar position_ticket para matching en el cierre
      MarkEntryStatus(idx, FILLED, deal_pos_id);
      PrintFormat("Entrada FILLED tranche=%d price=%.5f pos_ticket=%d",
                  idx + 1, deal_price, deal_pos_id);
     }
   else if(deal_entry == DEAL_ENTRY_OUT)
     {
      // Posición cerrada por TP o SL
      // Réplica de: if msg["i"] == entry.oco_tp_order_id / oco_sl_order_id
      int idx = FindEntryByPositionTicket(deal_pos_id);
      if(idx < 0) return;

      if(deal_reason == DEAL_REASON_TP)
        {
         // Réplica de: entry.status = EntryStatus.TAKED
         MarkEntryStatus(idx, TAKED, 0);
         PrintFormat("TP ejecutado tranche=%d price=%.5f", idx + 1, deal_price);
        }
      else if(deal_reason == DEAL_REASON_SL || deal_reason == DEAL_REASON_SO)
        {
         // Réplica de: entry.status = EntryStatus.STOP_lOSS_BROKEN
         MarkEntryStatus(idx, STOP_LOSS_BROKEN, 0);
         PrintFormat("SL ejecutado tranche=%d price=%.5f", idx + 1, deal_price);
        }
      else
         return; // cierre manual u otro motivo — ignorar

      // Reset si TP tomado O si todas las entradas están cerradas
      // Réplica de: if context.amount_taked_entries == 1 or all_closed: reset()
      bool any_taked  = (g_context.entry_first_30.status == TAKED ||
                         g_context.entry_40.status       == TAKED ||
                         g_context.entry_last_30.status  == TAKED);
      bool all_closed = g_context.all_entries_closed();

      if(any_taked || all_closed)
        {
         g_context.cancel_pending();
         g_context.reset();
         Print("Contexto reseteado. Buscando nueva oportunidad...");
        }
     }
  }
