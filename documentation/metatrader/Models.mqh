//+------------------------------------------------------------------+
//| Models.mqh                                                       |
//| Réplica de models.py — estructuras de datos del pipeline         |
//| Entry, StrategyContext, EntryStatus                              |
//+------------------------------------------------------------------+
#ifndef MODELS_MQH
#define MODELS_MQH

//--- EntryStatus — réplica de class EntryStatus(Enum) en models.py
enum EntryStatus
  {
   WAITING,
   STARTED,
   FILLED,
   STOP_LOSS_BROKEN,
   TAKED
  };

//+------------------------------------------------------------------+
//| Entry — réplica de @dataclass Entry en models.py                 |
//+------------------------------------------------------------------+
struct Entry
  {
   string            symbol;
   ENUM_ORDER_TYPE   side;
   double            price;
   double            volume;         // quantity en Python
   datetime          start;
   datetime          end;

   ulong             ticket;          // order ticket (pending order)
   ulong             position_ticket; // position ticket una vez la orden se ejecuta
   EntryStatus       status;

   double            tp_price;
   double            sl_price;
   ulong             tp_ticket;
   ulong             sl_ticket;

   //--- Constructor
                     Entry() : ticket(0), position_ticket(0), tp_ticket(0), sl_ticket(0),
                               price(0), volume(0), tp_price(0), sl_price(0),
                               status(WAITING), start(0), end(0) {}

   //--- is_open() — réplica de Entry.is_open()
   bool              is_open() const
     { return status == WAITING || status == STARTED || status == FILLED; }
  };

//+------------------------------------------------------------------+
//| StrategyContext — réplica de @dataclass StrategyContext          |
//+------------------------------------------------------------------+
struct StrategyContext
  {
   //--- Contexto IPDA macro (≡ strategy() en pipeline.py)
   double            annual_high;
   double            annual_low;
   double            semester_high;
   double            semester_low;
   double            atr;

   //--- SMC — estado persistente entre barras (≡ trend_zones, order_blocks, equal_lows)
   double            eql_price;   // equal low activo barrido (0.0 = no activo)
   double            ob_top;      // techo del order block vigente
   double            ob_bot;      // suelo del order block vigente
   bool              ob_valid;    // OB no mitigado

   //--- Entradas 3 tranches (≡ entry_first_30, entry_40, entry_last_30)
   Entry             entry_first_30;
   Entry             entry_40;
   Entry             entry_last_30;
   bool              has_entry_first_30;
   bool              has_entry_40;
   bool              has_entry_last_30;

   //--- Constructor
                     StrategyContext() :
                        annual_high(0), annual_low(0),
                        semester_high(0), semester_low(0), atr(0),
                        eql_price(0), ob_top(0), ob_bot(0), ob_valid(false),
                        has_entry_first_30(false), has_entry_40(false), has_entry_last_30(false)
                        {}

   //--- amount_of_entries — réplica de context.amount_of_entries
   int               amount_of_entries() const
     {
      int n = 0;
      if(has_entry_first_30) n++;
      if(has_entry_40)       n++;
      if(has_entry_last_30)  n++;
      return n;
     }

   //--- amount_filled — réplica de context.amount_filled_entries
   int               amount_filled() const
     {
      int n = 0;
      if(has_entry_first_30 && entry_first_30.status == FILLED) n++;
      if(has_entry_40       && entry_40.status       == FILLED) n++;
      if(has_entry_last_30  && entry_last_30.status  == FILLED) n++;
      return n;
     }

   //--- all_entries_closed — réplica del check de reset tras SL en pipeline.py
   bool              all_entries_closed() const
     {
      if(amount_of_entries() == 0) return false;
      bool e1 = !has_entry_first_30 || entry_first_30.status == TAKED || entry_first_30.status == STOP_LOSS_BROKEN;
      bool e2 = !has_entry_40       || entry_40.status       == TAKED || entry_40.status       == STOP_LOSS_BROKEN;
      bool e3 = !has_entry_last_30  || entry_last_30.status  == TAKED || entry_last_30.status  == STOP_LOSS_BROKEN;
      return e1 && e2 && e3;
     }

   //--- get_entry_index_by_ticket — réplica de context.get_entry(exchange_order_id)
   //--- Retorna 0/1/2 según tranche, -1 si no encontrado
   int               get_entry_index_by_ticket(ulong ticket_in) const
     {
      if(has_entry_first_30 && entry_first_30.ticket == ticket_in) return 0;
      if(has_entry_40       && entry_40.ticket       == ticket_in) return 1;
      if(has_entry_last_30  && entry_last_30.ticket  == ticket_in) return 2;
      return -1;
     }

   //--- cancel_pending — réplica de context.cancel_pending_entries(broker)
   void              cancel_pending()
     {
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action = TRADE_ACTION_REMOVE;

      if(has_entry_first_30 && entry_first_30.status == WAITING && entry_first_30.ticket != 0)
        { req.order = entry_first_30.ticket; OrderSend(req, res); }

      if(has_entry_40 && entry_40.status == WAITING && entry_40.ticket != 0)
        { req.order = entry_40.ticket; OrderSend(req, res); }

      if(has_entry_last_30 && entry_last_30.status == WAITING && entry_last_30.ticket != 0)
        { req.order = entry_last_30.ticket; OrderSend(req, res); }
     }

   //--- reset — réplica de context.reset()
   //--- Preserva annual/semester (contexto macro). Limpia estructura y entradas.
   void              reset()
     {
      eql_price = 0;
      ob_top    = 0;
      ob_bot    = 0;
      ob_valid  = false;
      has_entry_first_30 = false;
      has_entry_40       = false;
      has_entry_last_30  = false;
     }
  };

#endif // MODELS_MQH
