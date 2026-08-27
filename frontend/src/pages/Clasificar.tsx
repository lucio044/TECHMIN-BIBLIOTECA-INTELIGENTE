/** La vista del MVP que pide el enunciado: se entrega un contenido y se
 *  devuelve categoría, probabilidad y palabras clave. Lo demás --el
 *  ranking y los relacionados-- va por encima de lo pedido. */

import { useState } from "react";
import * as api from "../lib/api";
import { ErrorApi } from "../lib/api";
import { Anillo, Cargando, Error as Aviso, colorDe } from "../components/Comunes";
import type { ContenidoSalida, EntradaBiblioteca } from "../types";

const EJEMPLOS: { icono: string; etiqueta: string; titulo: string; texto: string }[] = [
  { icono: "☁️", etiqueta: "DevOps", titulo: "Desplegar con Docker y Kubernetes",
    texto: "Cómo empaquetar aplicaciones en contenedores Docker y desplegarlas en un clúster de Kubernetes en la nube con CI/CD." },
  { icono: "🎨", etiqueta: "Frontend", titulo: "Manejo de estado en React",
    texto: "Cómo administrar el estado de una aplicación web con componentes y hooks de React y Tailwind." },
  { icono: "🗄️", etiqueta: "Bases de Datos", titulo: "Optimizar consultas SQL",
    texto: "Uso de índices, JOIN y GROUP BY para acelerar consultas en PostgreSQL sobre tablas muy grandes." },
  { icono: "🔒", etiqueta: "Seguridad", titulo: "Autenticación con JWT",
    texto: "Cómo proteger una API con tokens JWT, OAuth y buenas prácticas de cifrado y seguridad." },
  { icono: "📈", etiqueta: "Ciencia de Datos", titulo: "Modelo de clasificación con scikit-learn",
    texto: "Entrenamiento de un modelo de machine learning con pandas y regresión logística sobre un dataset de textos." },
];

const LARGO_MINIMO = 20;

export default function Clasificar({
  alArchivar,
}: {
  alArchivar: (e: Omit<EntradaBiblioteca, "id" | "fecha">) => boolean;
}) {
  const [titulo, setTitulo] = useState("Introducción a Spring Boot");
  const [texto, setTexto] = useState(
    "En este contenido se presentan los conceptos básicos para la creación de APIs REST utilizando Java y Spring Boot, incluyendo controladores y servicios.",
  );
  const [resultado, setResultado] = useState<ContenidoSalida | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [archivado, setArchivado] = useState(false);

  async function enviar() {
    if (texto.trim().length < LARGO_MINIMO) {
      setError(`El texto debe tener al menos ${LARGO_MINIMO} caracteres.`);
      return;
    }
    if (!titulo.trim()) {
      setError("Hace falta un título.");
      return;
    }

    setCargando(true);
    setError(null);
    setArchivado(false);
    try {
      const r = await api.clasificar({ titulo: titulo.trim(), texto: texto.trim() });
      setResultado(r);
      const ok = alArchivar({
        titulo: titulo.trim(), texto: texto.trim(),
        categoria: r.categoria, probabilidad: r.probabilidad,
        palabras: r.informacion_adicional,
      });
      setArchivado(ok);
      if (!ok) setError("Se clasificó, pero no se pudo guardar en la biblioteca: el navegador no tiene espacio.");
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo conectar con la API.");
      setResultado(null);
    } finally {
      setCargando(false);
    }
  }

  function cargarEjemplo(e: (typeof EJEMPLOS)[number]) {
    setTitulo(e.titulo);
    setTexto(e.texto);
    setResultado(null);
    setError(null);
  }

  return (
    <section>
      <div className="hero">
        <h1>Clasificar contenido</h1>
        <div className="sub">
          El motor lee el contenido, decide su categoría y lo archiva en tu biblioteca — automáticamente.
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <div className="card-h">✍️ Contenido a clasificar</div>
          <div className="card-b">
            <label className="lab" htmlFor="titulo">Título</label>
            <input
              className="tin" id="titulo" value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              placeholder="Ej.: Introducción a Spring Boot"
            />

            <label className="lab" htmlFor="texto">Texto</label>
            <textarea
              className="tin" id="texto" value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder="Pegá aquí el contenido técnico…"
            />

            <button className="btn" onClick={enviar} disabled={cargando}>
              {cargando ? "Clasificando…" : "✨ Clasificar y archivar"}
            </button>

            <div className="ejemplos">
              Probá con un ejemplo:
              <div>
                {EJEMPLOS.map((e) => (
                  <span key={e.etiqueta} className="ej" onClick={() => cargarEjemplo(e)}>
                    {e.icono} {e.etiqueta}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-h">📊 Resultado del modelo</div>
          <div className="card-b">
            {cargando && <Cargando />}
            {!cargando && error && <Aviso mensaje={error} />}
            {!cargando && !error && !resultado && (
              <div className="chat-vacio">
                Pegá un contenido técnico y el modelo te dice<br />a qué categoría pertenece.
              </div>
            )}
            {!cargando && resultado && (
              <Resultado datos={resultado} archivado={archivado} />
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function Resultado({ datos, archivado }: { datos: ContenidoSalida; archivado: boolean }) {
  return (
    <>
      <div style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
        <Anillo valor={datos.probabilidad} categoria={datos.categoria} />
        <div>
          <div className="rc" style={{ fontSize: 18, fontWeight: 700 }}>
            <span className="rdot" style={{ background: colorDe(datos.categoria) }} />
            {datos.categoria}
          </div>
          {archivado && (
            <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 6 }}>
              Archivado en tu biblioteca
            </div>
          )}
        </div>
      </div>

      {datos.informacion_adicional.length > 0 && (
        <>
          <div className="lab" style={{ marginTop: 18 }}>Palabras clave</div>
          <div className="kwcloud">
            {datos.informacion_adicional.map((p) => (
              <span key={p} className="peso">{p}</span>
            ))}
          </div>
        </>
      )}

      {datos.ranking_categorias.length > 0 && (
        <>
          <div className="lab" style={{ marginTop: 18 }}>Otras categorías consideradas</div>
          {datos.ranking_categorias.map((r) => (
            <div key={r.categoria} className="rank-row">
              <span className="name">{r.categoria}</span>
              <span className="rank-bar">
                <i style={{ width: `${r.probabilidad * 100}%`, background: colorDe(r.categoria) }} />
              </span>
              <span className="pc">{Math.round(r.probabilidad * 100)}%</span>
            </div>
          ))}
        </>
      )}

      {datos.contenidos_relacionados.length > 0 && (
        <>
          <div className="lab" style={{ marginTop: 18 }}>Contenido relacionado del histórico</div>
          {datos.contenidos_relacionados.map((c, i) => (
            <div className="rel" key={c.id ?? i}>
              <div className="rel-h">
                <div className="rt">{c.titulo}</div>
                {c.parecido !== undefined && (
                  <span className="sim" title="parecido de significado">
                    {c.parecido.toFixed(2)}
                  </span>
                )}
              </div>
              <div className="rc">
                <span className="rdot" style={{ background: colorDe(c.categoria) }} />
                {c.categoria}
              </div>
            </div>
          ))}
        </>
      )}
    </>
  );
}
