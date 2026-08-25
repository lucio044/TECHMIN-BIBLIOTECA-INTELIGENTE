# Poner el proyecto en línea

Dos servicios, los dos gratuitos y sin tarjeta:

| | Dónde | Queda en |
|---|---|---|
| La API | Render | `https://techmind-api-24gg.onrender.com` |
| La página | GitHub Pages | `https://lucio044.github.io/TECHMIN-BIBLIOTECA-INTELIGENTE/frontend/` |

---

## 1 · La API en Render

**Entrar** a [render.com](https://render.com) con la cuenta de GitHub.

**New → Blueprint**, elegir este repositorio. Render lee `render.yaml` y arma
el servicio solo: no hay que tocar nada del panel.

> Los subdominios de Render son únicos en todo el mundo, y `techmind-api`
> ya estaba tomado por otro proyecto. Render le agregó un sufijo y el
> servicio quedó en **`techmind-api-24gg.onrender.com`**.
>
> Esa es la URL que usa `frontend/index.html`. Si algún día se renombra el
> servicio, hay que cambiarla ahí también.

La primera construcción tarda unos minutos. Cuando termine, comprobar:

```
https://techmind-api-24gg.onrender.com/health    ->  {"status":"ok"}
https://techmind-api-24gg.onrender.com/docs      ->  Swagger
```

### El arranque en frío

Medido contra el servicio real: **72 segundos** cuando estaba dormido, y
**menos de un segundo** despierto.

Los artefactos se copian durante la construcción, no al arrancar, así la
descarga de 33 MB queda fuera del camino crítico. El resto del tiempo es
Render levantando el contenedor, y eso no se puede acortar en el plan
gratuito — por eso importa el ping del punto siguiente.

---

## 2 · Mantenerlo despierto

El plan gratuito **apaga el servicio a los 15 minutos sin uso**. La visita
siguiente espera **unos 72 segundos** mientras vuelve a arrancar — medido,
no estimado.

Se evita con un ping periódico:

**En [cron-job.org](https://cron-job.org)** — gratis, sin tarjeta:

```
URL       https://techmind-api-24gg.onrender.com/health
Cada      10 minutos
```

Diez minutos alcanza porque el corte es a los quince.

> Render da **750 horas al mes** en el plan gratuito y mantenerlo despierto
> todo el mes consume unas 720. Entra, pero sin margen para un segundo
> servicio: si algún día agregás otro, el ping hay que espaciarlo o apagarlo.

---

## 3 · La página en GitHub Pages

En este repositorio: **Settings → Pages**

```
Source    Deploy from a branch
Branch    main    /  (root)
```

Guardar. En un par de minutos queda en:

```
https://lucio044.github.io/TECHMIN-BIBLIOTECA-INTELIGENTE/frontend/
```

La página elige sola a qué API hablarle: desde GitHub Pages usa la de
Render, y abierta en local usa `127.0.0.1:8000`. No hay que cambiar nada
para desarrollar.

---

## Cómo comprobar que quedó bien

| | Esperado |
|---|---|
| `https://techmind-api-24gg.onrender.com/health` | `{"status":"ok"}` |
| `https://techmind-api-24gg.onrender.com/docs` | Swagger carga |
| La página en GitHub Pages | clasifica y muestra relacionados |

Si la página carga pero al clasificar da error, es CORS: revisar que el
origen esté en `backend/app/main.py`. Hoy están permitidos
`https://lucio044.github.io`, `localhost` y cualquier `*.onrender.com`.

---

## Si cambia el modelo

Se reemplazan los archivos de `modelos/` en este repositorio y se reinicia
el servicio en Render (**Manual Deploy → Restart**). No hace falta volver a
construir: los artefactos se descargan al arrancar.
