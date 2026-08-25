#!/usr/bin/env bash
#
# Instala TechMind en una instancia Ubuntu de AWS, con HTTPS.
#
# Se ejecuta una sola vez, sobre una instancia recien creada:
#
#     curl -fsSL <url-de-este-archivo> -o instalar.sh
#     bash instalar.sh
#
# Al terminar imprime la URL publica de la API.

set -euo pipefail

REPO="https://github.com/lucio044/TECHMIN-BIBLIOTECA-INTELIGENTE.git"
DESTINO="/opt/techmind"
USUARIO="${SUDO_USER:-$USER}"

# La IP publica tiene que ser la IP ESTATICA ya asignada a la instancia.
# Por eso se pasa como argumento en vez de leerla de los metadatos: en
# Lightsail la estatica se adjunta despues de crear la instancia, y los
# metadatos pueden seguir devolviendo la dinamica original. Un certificado
# emitido para la IP equivocada no sirve.
IP="${1:-}"

if [[ -z "$IP" ]]; then
  echo "Uso: bash instalar.sh <IP-ESTATICA>"
  echo
  echo "La IP estatica esta en Lightsail > Networking, o en EC2 > Elastic IPs."
  exit 1
fi

if [[ ! "$IP" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
  echo "Eso no parece una IPv4: $IP"
  exit 1
fi

# sslip.io resuelve cualquier IP escrita en el nombre: 1.2.3.4.sslip.io -> 1.2.3.4
# Sirve para que Let's Encrypt emita un certificado, porque no emite para
# direcciones IP peladas. Evita tener que comprar un dominio hoy.
HOST="${IP//./-}.sslip.io"

echo "=============================================="
echo "  IP publica : $IP"
echo "  Dominio    : $HOST"
echo "=============================================="
echo

# ---------------------------------------------------------------- paquetes
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip git curl \
     debian-keyring debian-archive-keyring apt-transport-https

# Caddy se encarga del HTTPS solo: pide el certificado a Let's Encrypt en el
# primer arranque y lo renueva sin intervencion. Es lo que evita el paso
# manual de certbot.
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq caddy
fi

# ---------------------------------------------------------------- codigo
sudo mkdir -p "$DESTINO"
sudo chown "$USUARIO:$USUARIO" "$DESTINO"

if [[ -d "$DESTINO/.git" ]]; then
  git -C "$DESTINO" pull --ff-only
else
  git clone --depth 1 "$REPO" "$DESTINO"
fi

cd "$DESTINO"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r backend/requirements.txt

# Copia los artefactos del repositorio al lugar donde el backend los busca,
# para que no tenga que descargarlos al arrancar.
.venv/bin/python preparar.py

# ---------------------------------------------------------------- entorno
# La cadena de Neon va aca y no en el repositorio. El archivo queda legible
# solo por root, que es quien lanza el servicio.
if [[ ! -f /etc/techmind.env ]]; then
  sudo tee /etc/techmind.env >/dev/null <<'ENV'
# Pega la cadena de conexion de Neon en la linea de abajo, sin comillas.
# Sin ella el servicio arranca igual, pero las correcciones y los modelos
# propios se pierden en cada reinicio.
DATABASE_URL=

# Limita las hebras de BLAS. En una instancia chica, varias hebras pelean
# por los mismos nucleos y el resultado es mas lento, no mas rapido.
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
ENV
  sudo chmod 600 /etc/techmind.env
fi

# ---------------------------------------------------------------- servicio
sudo tee /etc/systemd/system/techmind.service >/dev/null <<UNIT
[Unit]
Description=TechMind API
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
User=$USUARIO
WorkingDirectory=$DESTINO/backend
EnvironmentFile=/etc/techmind.env
ExecStart=$DESTINO/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2

# Cada worker carga su propia copia del modelo, unos 270 MB. Con dos
# workers son 540 MB: entra en una instancia de 1 GB, no en una de 512 MB.

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

# ---------------------------------------------------------------- caddy
sudo tee /etc/caddy/Caddyfile >/dev/null <<CADDY
$HOST {
	reverse_proxy 127.0.0.1:8000
	encode gzip
}
CADDY

sudo systemctl daemon-reload
sudo systemctl enable --now techmind
sudo systemctl restart caddy

echo
echo "Esperando a que la API responda..."
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    echo "  la API responde."
    break
  fi
  sleep 2
done

echo
echo "=============================================="
echo "  API:   https://$HOST"
echo "  Docs:  https://$HOST/docs"
echo "=============================================="
echo
echo "Falta:"
echo "  1. Pegar la cadena de Neon:  sudo nano /etc/techmind.env"
echo "     y despues:                sudo systemctl restart techmind"
echo "  2. Apuntar el front a esta URL (linea 326 de index.html)."
echo
echo "Registro en vivo:   sudo journalctl -u techmind -f"
