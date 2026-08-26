# Poner el proyecto en línea

| | Dónde | Queda en |
|---|---|---|
| La API | AWS Lightsail, São Paulo | `https://15-229-103-244.sslip.io` |
| La página | Vercel | `https://techmind-equipo46.vercel.app` |
| La página (respaldo) | GitHub Pages | `https://lucio044.github.io/TECHMIND-BIBLIOTECA-INTELIGENTE/` |
| La base | Neon (PostgreSQL) | correcciones y modelos entrenados |

Los dos despliegues de la página salen del mismo repositorio y se
actualizan solos en cada push, así que nunca quedan desincronizados.

---

## 1 · La API en una instancia propia

Todo el procedimiento está en [`despliegue/instalar.sh`](despliegue/instalar.sh),
que se ejecuta una vez sobre una instancia Ubuntu recién creada:

```bash
curl -fsSL https://raw.githubusercontent.com/lucio044/TECHMIND-BIBLIOTECA-INTELIGENTE/main/despliegue/instalar.sh | bash -s <IP-ESTÁTICA>
```

El script instala los paquetes, Caddy, el código, el entorno virtual, los
artefactos, la unidad de systemd y el certificado. Tarda unos diez minutos,
casi todo esperando a que `pip` baje scipy y scikit-learn.

**La instancia:** Ubuntu 24.04, 2 GB de RAM. No alcanza con menos: la API
ocupa unos 270 MB con el modelo y la matriz cargados, y la búsqueda
semántica agrega otros 190 entre la sesión de ONNX y los vectores. Con dos
workers son unos 920 MB.

**El puerto 80 tiene que estar abierto**, además del 443. Let's Encrypt
valida por ahí antes de emitir el certificado.

### El dominio

Let's Encrypt no emite certificados para direcciones IP, y sin HTTPS la
página —que está en Vercel, que es HTTPS— no puede llamar a la API: el
navegador bloquea las llamadas a `http://` desde una página segura.

Se resuelve con [sslip.io](https://sslip.io), que resuelve cualquier IP
escrita en el nombre: `15.229.103.244` se vuelve `15-229-103-244.sslip.io`.
Es gratis y no hay que registrar nada. Para un dominio propio se cambia una
línea del `Caddyfile`.

### La base de datos

La cadena de Neon va en `/etc/techmind.env`, legible sólo por root, y nunca
en el repositorio:

```bash
sudo nano /etc/techmind.env      # pegar en DATABASE_URL=
sudo systemctl restart techmind
```

Sin ella el servicio arranca igual, pero las correcciones y los modelos
entrenados se pierden en cada reinicio.

---

## 2 · Qué pasa si algo se cae

**El proceso.** La unidad de systemd tiene `Restart=always`, así que si el
servicio muere vuelve solo a los 3 segundos. Y está habilitada con
`systemctl enable`, así que también arranca sola si se reinicia la máquina.

Para comprobarlo:

```bash
systemctl is-enabled techmind     # enabled
systemctl show techmind -p Restart  # Restart=always
```

**La API entera.** La página no se rompe: clasifica con un respaldo local en
JavaScript y lo dice. Lo que sí deja de funcionar es todo lo que necesita el
histórico —búsqueda, relacionados, asistente, modelos propios— y cada
pestaña muestra un error explicando qué pasó, en lugar de fingir un
resultado.

Eso es deliberado. No hay forma honesta de simular en el navegador una
búsqueda sobre 38.257 documentos, así que la alternativa a decir «no se
pudo» sería inventar.

**Por qué no hay una segunda API de respaldo.** La hubo, en Render, y se
apagó: su plan gratuito son 512 MB y la búsqueda semántica ya no entra ahí.
Un respaldo que corre una versión distinta de la que se está usando es peor
que no tener respaldo, porque nadie se entera de lo que falta hasta que lo
necesita.

---

## 3 · La página

**Vercel** — importar el repositorio. `vercel.json` tiene la configuración;
no hay que compilar nada, es un archivo HTML.

**GitHub Pages** — `Settings → Pages → Deploy from a branch → main / (root)`.

La página elige sola a qué API hablarle: publicada usa la de AWS, abierta en
local usa `127.0.0.1:8000`. No hay que cambiar nada para desarrollar.

---

## Cómo comprobar que quedó bien

| | Esperado |
|---|---|
| `https://15-229-103-244.sslip.io/v1/health` | `{"status":"ok"}` |
| `https://15-229-103-244.sslip.io/docs` | Swagger carga |
| La página | clasifica y muestra relacionados con su extracto |
| La pestaña Buscar | «cómo protejo las contraseñas» devuelve documentos en inglés |

Si la página carga pero al clasificar da error, es CORS: revisar que el
origen esté en `backend/app/main.py`.

---

## Actualizar

```bash
cd /opt/techmind
git pull
.venv/bin/pip install -q -r backend/requirements.txt   # sólo si cambiaron
sudo systemctl restart techmind
```

Si cambió el modelo o la matriz, hay que regenerar los vectores de la
búsqueda semántica, porque tienen que corresponderse fila a fila:

```bash
python semantica/generar_embeddings.py
```

El servicio lo comprueba al arrancar y se niega a usar unos vectores que no
coincidan con la matriz, en lugar de devolver resultados equivocados.
