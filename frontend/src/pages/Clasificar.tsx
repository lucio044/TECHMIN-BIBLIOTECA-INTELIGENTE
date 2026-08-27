/** La vista del MVP que pide el enunciado: se entrega un contenido y se
 *  devuelve categoría, probabilidad y palabras clave. Lo demás --el
 *  ranking y los relacionados-- va por encima de lo pedido. */

import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { ErrorApi } from "../lib/api";
import { Anillo, Cargando, Error as Aviso, Insignia, colorDe } from "../components/Comunes";
import type {
  ContenidoSalida, EntradaBiblioteca, RespuestaBusqueda, TerminoSugerido,
} from "../types";

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
  // Vacios: el placeholder ya dice que va, y un formulario relleno invita a
  // darle a Clasificar sin leer lo que dice.
  const [titulo, setTitulo] = useState("");
  const [texto, setTexto] = useState("");
  const [resultado, setResultado] = useState<ContenidoSalida | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [archivado, setArchivado] = useState(false);

  // Explorar el historico por termino vive aca, como en el prototipo: los
  // terminos no estan escritos a mano, los devuelve /v1/sugerencias.
  const [chips, setChips] = useState<TerminoSugerido[]>([]);
  const [exploracion, setExploracion] = useState<RespuestaBusqueda | null>(null);
  const [explorando, setExplorando] = useState(false);

  useEffect(() => {
    let vivo = true;
    api.sugerencias()
      .then((s) => { if (vivo) setChips(s.terminos.slice(0, 4)); })
      .catch(() => { /* sin sugerencias la pestaña funciona igual */ });
    return () => { vivo = false; };
  }, []);

  async function explorar(termino: string) {
    setExplorando(true);
    setResultado(null);
    setError(null);
    try {
      setExploracion(await api.buscarTermino(termino, 5));
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo explorar.");
      setExploracion(null);
    } finally {
      setExplorando(false);
    }
  }

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
    setExploracion(null);
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

  function limpiar() {
    setTitulo("");
    setTexto("");
    setResultado(null);
    setExploracion(null);
    setError(null);
    setArchivado(false);
  }

  const hayAlgo = !!(titulo || texto || resultado || exploracion);

  function cargarEjemplo(e: (typeof EJEMPLOS)[number]) {
    setTitulo(e.titulo);
    setTexto(e.texto);
    setResultado(null);
    setError(null);
  }

  return (
    <section>
      <div className="hero">
        <h1>Clasificá tu contenido técnico con <span className="gr">IA</span></h1>
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

            <div className="chat-envio" style={{ marginTop: 4 }}>
              <button className="btn" onClick={enviar} disabled={cargando}>
                {cargando ? "Clasificando…" : "✨ Clasificar y archivar"}
              </button>
              {hayAlgo && (
                <button className="btn-sm" onClick={limpiar} style={{ flex: "none" }}>
                  Limpiar
                </button>
              )}
            </div>

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

            {/* Las dos filas hacian cosas distintas y se veian iguales: los
                ejemplos rellenan este formulario, y esto busca en el
                historico y escribe en el panel de la derecha. Se separan por
                estilo --pastilla en vez de chip-- y por texto. */}
            {chips.length > 0 && (
              <div className="ejemplos">
                🔍 O buscá un término en los 38.257 documentos:
                <div>
                  {chips.map((c) => (
                    <span
                      key={c.termino}
                      className="chip"
                      style={{ cursor: "pointer" }}
                      title={`${c.documentos} documentos · ${c.categoria}`}
                      onClick={() => void explorar(c.termino)}
                    >
                      {c.termino}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-h">
            {exploracion ? "🏷️ Documentos del histórico" : "📊 Resultado del análisis"}
          </div>
          <div className="card-b">
            {(cargando || explorando) && <Cargando />}
            {!cargando && !explorando && error && <Aviso mensaje={error} />}

            {!cargando && !explorando && !error && !resultado && !exploracion && (
              <Vacio />
            )}

            {!cargando && !explorando && resultado && (
              <Resultado datos={resultado} archivado={archivado} />
            )}

            {!explorando && exploracion && (
              <>
                {exploracion.resultados.map((r) => (
                  <div className="rel" key={r.id}>
                    <div className="rt">{r.titulo}</div>
                    {r.extracto && <div className="rx">{r.extracto}</div>}
                    <div className="rc">
                      <span className="rdot" style={{ background: colorDe(r.categoria) }} />
                      {r.categoria}
                    </div>
                  </div>
                ))}
                <div className="rel-nota">
                  {exploracion.total} documentos contienen «{exploracion.termino}»
                </div>
              </>
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
      <div className="res-top">
        <Anillo valor={datos.probabilidad} categoria={datos.categoria} />
        <div>
          <div className="cat-mini">Categoría detectada</div>
          <Insignia categoria={datos.categoria} />
          {archivado && (
            <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
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
              <span key={p} className="chip">{p}</span>
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
            <div className="rel" key={i}>
              <div className="rel-h">
                <div className="rt">{c.titulo}</div>
                <span className="sim" title="similitud del coseno">
                  {c.similitud.toFixed(2)}
                </span>
              </div>
              {c.extracto && (
                <div className="rx" style={{ WebkitLineClamp: 1, lineClamp: 1 }}>
                  {c.extracto}
                </div>
              )}
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

/** El panel antes de clasificar: se ve la forma de lo que va a salir, con
 *  los lugares vacíos. Ni un cartel de texto --que no dice qué se obtiene--
 *  ni valores de ejemplo --que se leen como si el modelo ya hubiera
 *  respondido--. */
function Vacio() {
  return (
    <div style={{ opacity: 0.45 }}>
      <div className="res-top">
        <div className="ring">
          <svg width="100" height="100" aria-hidden="true">
            <circle cx="50" cy="50" r="45" fill="none"
                    stroke="rgba(255,255,255,.08)" strokeWidth="9" />
          </svg>
          <div className="val">
            <b>—</b>
            <span>confianza</span>
          </div>
        </div>
        <div>
          <div className="cat-mini">Categoría detectada</div>
          <span className="cat-badge" style={{ background: "rgba(255,255,255,.06)" }}>
            <span className="dot" /> —
          </span>
        </div>
      </div>

      <div className="lab">Palabras clave</div>
      <div className="kwcloud">
        <span className="chip">—</span>
        <span className="chip">—</span>
        <span className="chip">—</span>
        <span className="chip">—</span>
      </div>

      <div className="lab" style={{ marginTop: 18 }}>Otras categorías consideradas</div>
      {[0, 1, 2].map((i) => (
        <div className="rank-row" key={i}>
          <span className="name">—</span>
          <span className="rank-bar"><i style={{ width: 0 }} /></span>
          <span className="pc">—</span>
        </div>
      ))}

      <div className="lab" style={{ marginTop: 18 }}>Contenido relacionado del histórico</div>
      <div className="rel-nota" style={{ marginTop: 0 }}>
        Clasificá un contenido para ver los documentos que se le parecen.
      </div>
    </div>
  );
}
