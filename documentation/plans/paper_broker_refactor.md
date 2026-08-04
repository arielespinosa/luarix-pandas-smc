# Plan: Refactorizar PaperBroker para implementar la interfaz Broker

## Contexto

El `PaperBroker` actual en `app/brokers/paper.py` tiene la infraestructura interna de simulación (PaperOrder, EngineState, OCO) pero **no implementa la interfaz abstracta `Broker`**. Sus métodos públicos usan tipos propios (`PaperOrder`) en lugar de los del framework (`OrderRequest`, `OrderAck`, `Fill`), por lo que no puede usarse desde `BrokerFactory` como sustituto de `BinanceBroker`.

El objetivo es que `PaperBroker` exponga exactamente la misma API que `BinanceBroker` para poder hacer backtesting con él desde la factory sin cambiar el código de la estrategia.

---

## Qué cambiar en `app/brokers/paper.py`

### 1. Corregir el header (bug actual)
Hay un doble `from __future__ import annotations` (líneas 3 y 9). Limpiar el archivo para que solo haya uno.

### 2. Reescribir la clase `PaperBroker`

Mantener toda la infraestructura interna (`PaperOrder`, `PaperOCO`, `PaperPosition`, `EngineState`, `ExecutionReportFactory`) — es útil y correcta.

Reescribir solo la clase `PaperBroker` para que:
- Herede de `Broker` e implemente todos sus métodos abstractos
- Acepte `OrderRequest` en `place_order` (traduciendo internamente a `PaperOrder`)
- Devuelva `(OrderAck, list[Fill])` desde `place_order`
- Tenga la misma firma que `BinanceBroker` en todos los métodos

**Implementación de cada método:**

```python
class PaperBroker(Broker):
    def __init__(self, initial_balance: float = 10_000.0, commission: float = 0.001):
        self.state = EngineState()
        self._balance = initial_balance   # USDT simulado
        self._commission = commission     # 0.1% por defecto
        self._current_price: dict[str, float] = {}  # precio actual por símbolo

    # Métodos de conexión/mercado — stubs simples
    def connect(self) -> None: pass
    def get_ticker(self, symbol: str) -> float: return self._current_price.get(symbol, 0.0)
    def get_order_book(self, symbol: str, limit: int = 20) -> dict: return {}

    # Balance/posiciones — simuladas
    def get_balance(self) -> dict[str, float]: return {"USDT": self._balance}
    def get_positions(self) -> dict: return {p.symbol: float(p.quantity) for p in self.state.positions if not p.closed}

    # Órdenes
    def place_order(self, order: OrderRequest) -> tuple[OrderAck, list[Fill]]: ...
    def cancel_order(self, symbol: str, order_id: str) -> OrderAck: ...
    def update_order(self, symbol: str, order_id: str) -> OrderAck: ...  # cancel + replace

    # OCO
    def place_oco_order(self, symbol, side, quantity, take_profit_price, stop_price, stop_limit_price) -> tuple[str, OrderAck, OrderAck]: ...
    def cancel_oco(self, symbol: str, oco_list_id: int) -> OrderAck: ...
    def update_oco(self, entry, new_tp, new_sl, new_sl_limit) -> tuple[str, OrderAck, OrderAck]: ...  # cancel + replace

    # Backtesting — método extra (no está en Broker ABC)
    def on_candle(self, candle): ...
```

**Detalles clave:**

- `place_order(OrderRequest)`: 
  - MARKET → fill inmediato al `_current_price[symbol]`; devuelve `OrderAck(status=FILLED)` y un `Fill`
  - LIMIT → encola como `PaperOrder` pendiente; devuelve `OrderAck(status=NEW)` y `[]`

- `cancel_order(symbol, order_id: str)`: busca en `pending_orders` por `str(order.order_id) == order_id`, cancela, devuelve `OrderAck(status=CANCELED)`

- `place_oco_order(...)`: crea dos `PaperOrder` internos (TP como LIMIT, SL como STOP_LOSS_LIMIT) y los registra en el `EngineState`; devuelve `(str(list_id), tp_ack, sl_ack)` con `status=NEW`

- `cancel_oco(...)`: cancela el `PaperOCO` por `list_id`; devuelve `OrderAck(status=CANCELED)`

- `update_oco(entry, ...)`: llama `cancel_oco` + `place_oco_order`; devuelve lo mismo que `place_oco_order`

- `update_order(symbol, order_id)`: cancel + re-encolar — suficiente para backtesting

### 3. Actualizar `_filled` para manejar STOP_LOSS_LIMIT

El método actual solo maneja LIMIT. Hay que añadir la lógica de stop:

```python
def _filled(self, order: PaperOrder, candle) -> bool:
    if order.type == OrderType.STOP_LOSS_LIMIT and order.stop_price:
        trigger = float(order.stop_price)
        if order.side == OrderSide.SELL:
            return candle.low <= trigger   # SL de posición long
        else:
            return candle.high >= trigger  # SL de posición short
    # LIMIT normal
    if order.side == OrderSide.BUY:
        return candle.low <= float(order.price)
    return candle.high >= float(order.price)
```

Para el fill price del SL, usar `order.stop_price` (o `order.price` como límite).

### 4. No cambiar factory.py

Ya tiene `AvailableBrokers.PAPER` y `__create_paper__()` que devuelve `PaperBroker()`. Funciona tal cual.

---

## Archivos a modificar

- `app/brokers/paper.py` — única modificación: reescribir la clase `PaperBroker`

---

## Verificación

1. Desde un script de backtesting:
```python
broker = BrokerFactory.get_broker(AvailableBrokers.PAPER)
order = OrderRequest(symbol="BTCUSDT", side=Side.BUY, quantity=0.01, order_type=OrderType.LIMIT, price=50000.0)
ack, fills = broker.place_order(order)
assert ack.status == OrderStatus.NEW
assert fills == []

broker.on_candle(candle_with_low_below_50000)
# La orden debería haberse llenado → ack.status == FILLED en el callback
```

2. Verificar que el OCO se comporta como Binance: al llenarse el TP, el SL se cancela automáticamente.
