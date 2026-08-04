# Refactor: adoptar patrón de clases de rendering (RenderObject)

## Context

El usuario ha introducido en `structure_renderer.py` un nuevo patrón: cada elemento visual es un dataclass autocontenido con `render(chart)` / `delete(chart)` / `update(chart)`, que llama directamente a la API de lightweight-charts sin pasar por un wrapper intermedio (`BaseRenderer`). El notebook `notebooks/lightweight-charts.ipynb` muestra el uso esperado.

Esto reemplaza el patrón viejo de `BaseRenderer` con sus `draw_segment`, `draw_ray`, etc. El `StructureRenderer` actual todavía hereda de `BaseRenderer` y usa los métodos viejos. Hay que completar la migración.

---

## Ficheros a eliminar

| Fichero | Razón |
|---------|-------|
| `backtesting/renders/base_renderer.py` | Reemplazado por el patrón de clases |
| `backtesting/renders/level_renderer.py` | Comentado en chart_manager, usa viejo patrón |

`trade_renderer.py` y `stas_renderer.py` no usan `BaseRenderer` → no se tocan.

---

## Cambios en `backtesting/renders/structure_renderer.py`

### 1. Añadir `_Point` (adaptador mínimo de timestamp)

```python
class _Point:
    __slots__ = ("time",)
    def __init__(self, t):
        self.time = t
```

Necesario porque las clases de render esperan objetos con `.time` pero los datos del contexto tienen `first_time` / `second_time` como `pd.Timestamp`.

### 2. Corregir `EqualLevel`

**Problemas actuales**:
- Usa `c1.high` / `c2.high` → debería ser `self.price` (línea horizontal fija)
- El label es un `chart.marker()` en `c1.time` → queda en el histórico, invisible al ver datos actuales
- Sin extensión a la derecha → la línea no llega al tiempo actual

**Fix**: reemplazar `_marker` por `_ray` usando `chart.ray_line()` que soporta `text=` nativo y extiende a la derecha:

```python
_line = None    # TrendLine c1→c2 (span histórico entre los dos pivots)
_ray  = None    # RayLine c2→∞ con text label (nivel activo visible en tiempo actual)

def render(self, chart):
    self._line = chart.trend_line(
        start_time=self.c1.time,
        start_value=self.price,      # ← precio fijo, no c1.high
        end_time=self.c2.time,
        end_value=self.price,        # ← mismo precio
        line_color=self.color,
        width=self.width,
        style=self.style,
    )
    self._ray = chart.ray_line(
        self.c2.time,
        self.price,
        color=self.color,
        width=self.width,
        style=self.style,
        text=self.text,              # ← "EQL" / "EQH" visible en el chart
    )

def delete(self, chart):
    if self._line:
        self._line.delete(); self._line = None
    if self._ray:
        self._ray.delete(); self._ray = None
```

### 3. Corregir `OrderBlock` y `FVG`

`chart.rectangle()` no existe en la librería → usar `chart.box()`.

API confirmada en `abstract.py:332`:
```python
chart.box(start_time, start_value, end_time, end_value,
          color=border, fill_color=fill, width=1)
```

`OrderBlock.render()`:
```python
self._box = chart.box(
    start_time=self.start.time,
    start_value=self.low,
    end_time=self.end.time,
    end_value=self.high,
    color=self.color,
    fill_color=fill_color,
)
```

`FVG.render()`: igual usando `c1.time` / `c2.time` y los precios high/low.

### 4. Reescribir `StructureRenderer`

Eliminar herencia de `BaseRenderer`. Nuevo esquema mínimo:

```python
class StructureRenderer:
    def __init__(self, manager, chart, is_daily: bool):
        self.manager   = manager
        self.chart     = chart
        self.is_daily  = is_daily
        self._objects: list[RenderObject] = []

    def clear(self):
        for obj in self._objects:
            obj.delete(self.chart)
        self._objects.clear()

    def draw(self, context):
        self.clear()
        flags = self.manager.render_flags
        if flags.get("EQL", True):
            self._draw_eql(context)
        if flags.get("EQH", True):
            self._draw_eqh(context)
        # OB, FVG, BOS, CHoCH, TZ: comentados (pendientes de prueba)

    def _draw_eql(self, context):
        for data in context.equal_lows:
            if not data.first_time or not data.second_time:
                continue
            obj = EqualLevel(
                c1=_Point(data.first_time),
                c2=_Point(data.second_time),
                price=data.price,
                text="EQL",
                color=Colors.EQL_LOW,
            )
            obj.render(self.chart)
            self._objects.append(obj)

    def _draw_eqh(self, context):
        # igual con context.equal_highs, text="EQH", Colors.EQL_HIGH
```

**Eliminar de StructureRenderer**: `_ts()`, `_is_bull()`, todos los métodos `draw_*` viejos, imports de `BaseRenderer`, `Direction`, `pandas`.

---

## Cambios en `backtesting/chart_manager.py`

Eliminar todo lo referente a `LevelRenderer`:

```python
# ELIMINAR:
from backtesting.renders.level_renderer import LevelRenderer
self._level_1d: LevelRenderer | None = None
self._level_4h: LevelRenderer | None = None
self._level_1d = LevelRenderer(self, self._chart_1d)
self._level_4h = LevelRenderer(self, self._chart_4h)
# En _redraw_all():
self._level_1d.draw(self._last_context)
self._level_4h.draw(self._last_context)
```

`StructureRenderer` mantiene la misma firma de constructor — sin cambios en el resto de chart_manager.

---

## Primer paso al implementar

Guardar este plan en `docs/plans/refactor-render-clases.md`.

---

## Verificación

1. `pipeline_backtest_v3.py` carga sin ImportError (base_renderer eliminado)
2. EQL = líneas rojas punteadas con "EQL" visible en el chart desde segundo pivot
3. EQH = líneas teal punteadas con "EQH" visible en el chart
4. Toggle EQL/EQH: limpia y redibuja sin duplicados
5. El resto de renders (OB, FVG, etc.) permanece comentado hasta próxima fase
