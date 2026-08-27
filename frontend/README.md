# Frontend — React + Vite + TypeScript

La interfaz de TechMind. Consume la API del proyecto y no tiene lógica de
modelo propia: todo lo que muestra sale de `/v1`.

```bash
npm install
npm run dev      # desarrollo, en el 5173
npm run build    # compila a dist/
npm run preview  # sirve lo compilado
```

## A qué API apunta

Por defecto, `https://15-229-103-244.sslip.io` en producción y
`http://127.0.0.1:8000` en local. Se puede fijar otra sin tocar el código:

```bash
VITE_API_URL=https://otra-instancia npm run build
```

## Cómo está organizado

```
src/
├── main.tsx              punto de entrada
├── App.tsx               navegación entre las siete vistas
├── types.ts              las formas que devuelve la API, en un solo sitio
├── index.css             estilos
├── lib/
│   ├── api.ts            todas las llamadas HTTP
│   ├── idioma.ts         detección es/en, para el botón de traducir
│   └── almacen.ts        la biblioteca personal, en localStorage
├── components/
│   ├── Navegacion.tsx    las pestañas
│   └── Comunes.tsx       anillo de confianza, colores, avisos
└── pages/
    ├── Clasificar.tsx    el MVP: contenido → categoría, confianza, claves
    ├── Biblioteca.tsx    lo clasificado, con filtro por categoría
    ├── MisTemas.tsx      explorar el histórico por término
    ├── Buscar.tsx        búsqueda semántica
    ├── Asistente.tsx     preguntas respondidas desde el histórico
    ├── Propios.tsx       entrenar con categorías propias
    └── Dashboard.tsx     métricas del modelo, leídas de /v1/metricas
```

## Por qué TypeScript y no JavaScript

Antes esto era un `index.html` de 1.599 líneas. Funcionaba, y tenía un fallo
que nadie podía ver: los `\b` de las dos expresiones que detectan el idioma
eran caracteres de retroceso literales en lugar de escapes, así que ninguna
matcheaba nada y el botón «Ver en español» no llegó a aparecer nunca. Una
expresión regular con un carácter de control adentro no da error de
sintaxis: se queda sin hacer nada, en silencio.

Acá eso no puede repetirse sin que se note: `src/lib/idioma.ts` tiene las
expresiones en un módulo aparte, y el build falla si un tipo no cierra.

## Lo que el enunciado pedía

React es el stack pedido por el hackathon. Antes esta versión no lo cumplía
—era un archivo suelto— y esa fila de la comparativa se perdía por defecto
aunque la funcionalidad estuviera.
