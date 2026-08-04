# Despliegue de `fastapi_server` con nginx + uvicorn (Linux VPS)

## Contexto

El servidor FastAPI (`fastapi_server/`) ya funciona localmente en modo desarrollo
(`uvicorn --reload`). Ahora se necesita desplegarlo en un VPS Linux para que el
frontend Next.js lo consuma en un entorno real, no solo local. Se confirmó con el
usuario:
- **SO destino**: Linux (VPS/servidor dedicado).
- **Acceso**: por IP directa, sin dominio ni HTTPS por ahora (se puede agregar
  Let's Encrypt/certbot más adelante sin rehacer nada de esto).
- **nginx**: instalación nueva, dedicada solo a esta API (no hay que convivir con
  otros sitios existentes).

`uvicorn` sirve la app ASGI directamente; `nginx` actúa como reverse proxy delante
(termina la conexión del cliente, reenvía a uvicorn en `127.0.0.1:8000`) — el patrón
estándar en Linux, con `systemd` manteniendo uvicorn corriendo como servicio
(reinicio automático si crashea o si el servidor reinicia).

## Cambio de código necesario antes de desplegar

`fastapi_server/main.py` tiene el origen CORS **hardcodeado** a
`http://localhost:3000` (línea 11). En producción el frontend correrá en otro
origen (la IP del VPS de Next.js, o un dominio más adelante), así que esto debe
hacerse configurable vía variable de entorno en vez de estar fijo en código:

```python
import os
...
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_methods=["*"], allow_headers=["*"])
```

Así, en el `.env` de producción (o en el `EnvironmentFile` del servicio systemd) se
define `CORS_ORIGINS=http://<ip-del-frontend>,https://midominio.com` sin tocar código
cada vez que cambie el origen permitido. No se toca `fastapi_server/run.py` (es un
helper de desarrollo local en Windows, ya con su propio hack de `sys.path`
intencional — en producción no se usa en absoluto, systemd invoca `uvicorn`
directamente).

## Archivos nuevos (plantillas de despliegue)

Se crea una carpeta `deploy/` en el repo con las plantillas versionadas (así quedan
en git, no solo en el VPS):

- **`deploy/nexora-fastapi.service`** — unit de systemd que mantiene uvicorn corriendo.
- **`deploy/nginx-nexora-api.conf`** — server block de nginx (reverse proxy a uvicorn).
- **`deploy/.env.example`** — plantilla de variables opcionales (`CORS_ORIGINS`, y las
  que ya lee `config/settings.py` si en algún momento se necesitan credenciales reales
  de Binance/Bitunix — hoy no son necesarias, los endpoints de indicadores funcionan
  sin API key).

### `deploy/nexora-fastapi.service`

```ini
[Unit]
Description=Nexora FastAPI indicators server (uvicorn)
After=network.target

[Service]
Type=simple
User=nexora
Group=nexora
WorkingDirectory=/opt/nexora-trading-framework
Environment="PATH=/opt/nexora-trading-framework/env/bin"
EnvironmentFile=-/opt/nexora-trading-framework/.env
ExecStart=/opt/nexora-trading-framework/env/bin/uvicorn fastapi_server.main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Notas sobre esta plantilla:
- `User`/`Group=nexora` es un ejemplo — se reemplaza por un usuario real del sistema
  (no correr como `root`); el MD explica cómo crearlo si no existe.
- `WorkingDirectory`/rutas usan `/opt/nexora-trading-framework` como ejemplo — se
  ajusta a donde realmente se clone el repo en el VPS.
- `EnvironmentFile=-/opt/.../.env` — el `-` inicial lo hace **opcional**: si el
  archivo no existe, el servicio arranca igual (no falla), ya que
  `config/settings.py` usa `os.getenv(..., default)` en todos los casos, nunca
  variables obligatorias.
- `--workers 4` es un punto de partida razonable para un VPS pequeño/mediano;
  ajustable según CPU disponible.
- `--proxy-headers --forwarded-allow-ips=127.0.0.1` le dice a uvicorn que confíe en
  los headers `X-Forwarded-For`/`X-Forwarded-Proto` que pone nginx.

### `deploy/nginx-nexora-api.conf`

```nginx
server {
    listen 80;
    server_name _;  # reemplazar por la IP pública o un dominio cuando exista

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### `deploy/.env.example`

```env
# Opcional. Orígenes permitidos por CORS, separados por coma.
CORS_ORIGINS=http://localhost:3000

# Opcionales — solo si /brokers/candles se usará con broker=bitunix o con
# credenciales reales de Binance (no necesarias para /indicators, /smc, ni para
# /brokers/candles con broker=binance, que ya funciona sin API key).
# BINANCE_API_KEY=
# BINANCE_API_SECRET=
# BITUNIX_API_KEY=
# BITUNIX_API_SECRET=
```

## El documento MD (entregable principal)

**`docs/deploy_fastapi_server.md`** — runbook copiar/pegar, paso a paso, para un VPS
Linux limpio (Ubuntu/Debian como referencia — se nota dónde cambian los comandos si
es otra distro). Contenido:

1. **Prerrequisitos**: acceso SSH con sudo, Python 3.11+ y `python3-venv` instalados
   (`apt install python3 python3-venv python3-pip -y`), git.
2. **Llevar el código al servidor**: `git clone <url-del-repo> /opt/nexora-trading-framework`
   (o `git pull` si ya existe).
3. **Entorno virtual e instalación**: crear venv nuevo en el servidor (el `env/` del
   repo es de Windows, no sirve en Linux — está en `.gitignore`, así que no se
   clona), `pip install -r requirements.txt`. Nota: `requirements.txt` está en
   UTF-16 (arrastrado de un `pip freeze` en PowerShell) — pip normalmente lo
   detecta bien por el BOM, pero el paso incluye verificar que la instalación
   termine sin errores de parseo antes de seguir.
4. **Variables de entorno**: copiar `deploy/.env.example` a `/opt/.../. env`,
   ajustar `CORS_ORIGINS` al origen real del frontend.
5. **Servicio systemd**: copiar `deploy/nexora-fastapi.service` a
   `/etc/systemd/system/nexora-fastapi.service`, ajustar `User`/rutas si difieren,
   crear el usuario de sistema si no existe (`adduser --system --group nexora`),
   `systemctl daemon-reload`, `systemctl enable --now nexora-fastapi`,
   `systemctl status nexora-fastapi` para confirmar que quedó activo.
6. **nginx**: `apt install nginx -y`, copiar `deploy/nginx-nexora-api.conf` a
   `/etc/nginx/sites-available/nexora-api`, symlink en
   `/etc/nginx/sites-enabled/`, `nginx -t` (valida sintaxis),
   `systemctl reload nginx`.
7. **Firewall**: si `ufw` está activo, `ufw allow 'Nginx Full'` (o `ufw allow 80/tcp`)
   y confirmar que el puerto SSH sigue permitido antes de aplicar.
8. **Verificación end-to-end**: `curl http://<IP-del-VPS>/providers` desde una
   máquina externa (no localhost del VPS) debe devolver el JSON mockeado; probar
   también un `POST /indicators/swings` real. Si falla, cómo mirar logs:
   `journalctl -u nexora-fastapi -f` (uvicorn/aplicación) y
   `tail -f /var/log/nginx/error.log` (proxy).
9. **Actualizar el despliegue** cuando cambie el código: `git pull` +
   `systemctl restart nexora-fastapi` (no hace falta tocar nginx salvo que cambie
   el puerto/config).
10. **Próximo paso opcional (cuando haya dominio)**: nota breve de que agregar
    HTTPS es `certbot --nginx -d midominio.com` sin reescribir el server block a
    mano — se deja para cuando exista el dominio, no se implementa ahora.

## Verificación de este plan una vez ejecutado

- `systemctl status nexora-fastapi` → `active (running)`.
- `curl -I http://<IP>/providers` desde fuera del VPS → `200 OK` con CORS/headers de
  nginx visibles (`server: nginx`).
- `POST http://<IP>/indicators/swings` con un body real → mismo JSON de elementos
  que ya se validó en local.
- Reiniciar el VPS (o `systemctl stop` manualmente) y confirmar que
  `systemctl status` vuelve a `active` solo (systemd lo revive) sin intervención
  manual.
