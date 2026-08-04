# Desplegar `fastapi_server` en un VPS Linux con nginx + uvicorn

Runbook paso a paso para poner el servidor de indicadores en un VPS Linux limpio
(Ubuntu/Debian como referencia — en otras distros cambian `apt` por el gestor de
paquetes correspondiente). Acceso por IP, sin dominio ni HTTPS por ahora — se puede
agregar Let's Encrypt más adelante sin rehacer nada de esto (ver paso 10).

Arquitectura: **nginx** recibe las peticiones en el puerto 80 y las reenvía
(reverse proxy) a **uvicorn**, que corre en `127.0.0.1:8000` y nunca queda expuesto
directamente a internet. **systemd** mantiene uvicorn corriendo como servicio,
reiniciándolo solo si crashea o si el servidor se reinicia.

Los tres archivos de plantilla que se copian/pegan en este runbook viven en
`deploy/` en este repo:
- `deploy/nexora-fastapi.service`
- `deploy/nginx-nexora-api.conf`
- `deploy/.env.example`

---

## 1. Prerrequisitos

Acceso SSH con `sudo` al VPS. Instalar Python, venv y git:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git -y
```

## 2. Llevar el código al servidor

```bash
sudo mkdir -p /opt/nexora-trading-framework
sudo chown "$USER" /opt/nexora-trading-framework
git clone <url-del-repo> /opt/nexora-trading-framework
cd /opt/nexora-trading-framework
```

Para actualizaciones futuras, este mismo directorio se actualiza con `git pull`
(ver paso 9).

## 3. Entorno virtual e instalación de dependencias

El `env/` que trae el repo es un venv de **Windows** (está en `.gitignore`, no se
clona) — hay que crear uno nuevo, nativo de Linux:

```bash
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Nota**: `requirements.txt` está en UTF-16 (quedó así de un `pip freeze` hecho en
PowerShell en Windows). `pip` normalmente lo detecta bien por el BOM, pero conviene
confirmar que el `pip install` de arriba termina sin errores de parseo antes de
seguir. Si falla con un error de encoding, convertir el archivo a UTF-8
(`iconv -f UTF-16LE -t UTF-8 requirements.txt -o requirements.utf8.txt` y usar ese
archivo) es la salida rápida.

## 4. Variables de entorno

```bash
cp deploy/.env.example .env
nano .env   # ajustar CORS_ORIGINS al origen real del frontend
```

`CORS_ORIGINS` acepta varios orígenes separados por coma, por ejemplo:
```env
CORS_ORIGINS=http://<ip-del-frontend>:3000,https://midominio.com
```
Si el archivo `.env` no existe o queda vacío, el servidor arranca igual (todas las
variables de `config/settings.py` tienen default) — solo el CORS quedaría en su
default (`http://localhost:3000`), que probablemente haya que ajustar.

## 5. Servicio systemd

Crear el usuario de sistema que va a correr el proceso (nunca correr como `root`):

```bash
sudo adduser --system --group nexora
sudo chown -R nexora:nexora /opt/nexora-trading-framework
```

Copiar la plantilla y ajustarla si el usuario o las rutas difieren de los defaults
(`nexora` / `/opt/nexora-trading-framework`):

```bash
sudo cp deploy/nexora-fastapi.service /etc/systemd/system/nexora-fastapi.service
sudo nano /etc/systemd/system/nexora-fastapi.service   # ajustar User/Group/rutas si aplica
```

Activar y arrancar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nexora-fastapi
sudo systemctl status nexora-fastapi
```

Debe mostrar `active (running)`. Si no, ver la sección de logs (paso 8).

## 6. nginx

```bash
sudo apt install nginx -y
sudo cp deploy/nginx-nexora-api.conf /etc/nginx/sites-available/nexora-api
sudo ln -s /etc/nginx/sites-available/nexora-api /etc/nginx/sites-enabled/nexora-api
sudo nginx -t   # valida la sintaxis antes de aplicar
sudo systemctl reload nginx
```

Si el VPS trae un `sites-enabled/default` de ejemplo activo, conviene
deshabilitarlo para que no compita por el puerto 80:
```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl reload nginx
```

## 7. Firewall

Si `ufw` está activo:

```bash
sudo ufw allow OpenSSH     # confirmar ANTES de tocar nada más, para no perder el SSH
sudo ufw allow 'Nginx Full'
sudo ufw status
```

## 8. Verificación end-to-end

Desde **fuera** del VPS (tu máquina local, no una sesión SSH dentro del servidor):

```bash
curl -i http://<IP-del-VPS>/providers
curl -i -X POST http://<IP-del-VPS>/indicators/swings \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","interval":"4h","start_date":"2024-01-01","end_date":"2024-02-01","length":50}'
```

El primero debe devolver el catálogo mockeado de Binance (200 OK); el segundo, el
mismo JSON de `{"elements": [...]}` ya validado en local.

Si algo falla, revisar logs en el VPS:
```bash
journalctl -u nexora-fastapi -f      # logs de uvicorn/la aplicación
sudo tail -f /var/log/nginx/error.log # logs del proxy
```

## 9. Actualizar el despliegue

Cuando haya cambios de código en el repo:

```bash
cd /opt/nexora-trading-framework
git pull
source env/bin/activate
pip install -r requirements.txt   # solo si cambiaron las dependencias
sudo systemctl restart nexora-fastapi
```

No hace falta tocar nginx salvo que cambie el puerto o la configuración del proxy.

## 10. Cuando haya un dominio (HTTPS, opcional, no se hace ahora)

Con un dominio ya apuntando al VPS, agregar HTTPS es un solo comando —no hay que
reescribir el server block a mano—:

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d midominio.com
```

`certbot` edita `nginx-nexora-api` automáticamente para servir HTTPS y renovar el
certificado solo.
