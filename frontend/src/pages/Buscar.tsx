/** Búsqueda semántica: encuentra documentos que hablan de lo mismo aunque
 *  no compartan ni un término con lo que se escribió. */

import { useState } from "react";
import * as api from "../lib/api";
import { ErrorApi } from "../lib/api";
import { pareceIngles, preguntoEnIngles } from "../lib/idioma";
import { BotonTraducir, Cargando, Error as Aviso, colorDe } from "../components/Comunes";
import type { RespuestaSemantica, ResultadoSemantico } from "../types";

// Los cuatro se probaron contra la API en vivo. Se descartaron dos que
// devolvian ruido: «para que sirve Docker» daba 0,52 con un documento
// titulado «Bagel Bot Reimaging Donut», y «que el servidor se levante solo
// al reiniciar» daba 0,51 con un error de conexion de go-redis. La forma
// interrogativa perjudica al embedding: la misma idea enunciada como tema
// --«como desplegar contenedores»-- sube a 0,60 y acierta.
// Etiqueta corta y consulta larga, como en el prototipo: poner la consulta
// entera en el chip hace una fila de botones enormes.
//
// El ultimo es a proposito una consulta ajena al corpus. Que el sistema
// conteste «no hay nada que se parezca» es tan demostrable como que
// encuentre, y es lo que lo separa de uno que siempre responde algo.
const EJEMPLOS: { etiqueta: string; consulta: string }[] = [
  { etiqueta: "contraseñas", consulta: "cómo protejo las contraseñas de los usuarios" },
  { etiqueta: "app que se cierra", consulta: "la aplicación se cierra sola en el celular" },
  { etiqueta: "contenedores", consulta: "cómo desplegar contenedores" },
  { etiqueta: "guardar datos", consulta: "guardar millones de registros y buscarlos por fecha" },
  { etiqueta: "algo ajeno al corpus", consulta: "receta de sopa de tomate con albahaca" },
];

const LARGO_MINIMO = 3;

export default function Buscar({ hayTraductor }: { hayTraductor: boolean }) {
  const [consulta, setConsulta] = useState("");
  const [datos, setDatos] = useState<RespuestaSemantica | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // La traducción se guarda aparte del original, para poder volver.
  const [traducciones, setTraducciones] = useState<Map<number, ResultadoSemantico>>(new Map());
  const [traduciendo, setTraduciendo] = useState(false);
  const [errorTrad, setErrorTrad] = useState<string | null>(null);

  async function buscar(texto = consulta) {
    if (texto.trim().length < LARGO_MINIMO) {
      setError("Escribí algo un poco más largo para buscar.");
      return;
    }
    setCargando(true);
    setError(null);
    setTraducciones(new Map());
    setErrorTrad(null);
    try {
      setDatos(await api.buscarSemantica(texto.trim(), 6));
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo buscar.");
      setDatos(null);
    } finally {
      setCargando(false);
    }
  }

  async function alternarTraduccion() {
    if (!datos) return;
    if (traducciones.size > 0) { setTraducciones(new Map()); return; }

    setTraduciendo(true);
    setErrorTrad(null);
    try {
      // Una sola petición con todos los textos: gasta uno del límite por
      // minuto y no seis.
      const piezas = datos.resultados.flatMap((r) => [r.titulo, r.extracto]);
      const { traducciones: t } = await api.traducir(piezas, "es");
      const mapa = new Map<number, ResultadoSemantico>();
      datos.resultados.forEach((r, i) => {
        mapa.set(r.id, { ...r, titulo: t[i * 2] ?? r.titulo, extracto: t[i * 2 + 1] ?? r.extracto });
      });
      setTraducciones(mapa);
    } catch (e) {
      setErrorTrad(e instanceof ErrorApi ? e.message : "No se pudo traducir.");
    } finally {
      setTraduciendo(false);
    }
  }

  // El botón se ofrece a quien buscó en castellano y recibió material en
  // inglés. A quien preguntó en inglés no: pidió en el idioma que recibió.
  const ofrecerTraduccion =
    hayTraductor &&
    !!datos?.resultados.length &&
    !preguntoEnIngles(consulta) &&
    datos.resultados.some((r) => pareceIngles(`${r.titulo} ${r.extracto}`));

  const mostrados = datos?.resultados.map((r) => traducciones.get(r.id) ?? r) ?? [];

  return (
    <section>
      <div className="hero">
        <h1>Búsqueda <span className="gr">semántica</span></h1>
        <div className="sub">
          Describí lo que necesitás con tus palabras. Encuentra documentos que hablan de eso
          aunque no compartan ni un término con lo que escribiste — y aunque estén en otro idioma.
        </div>
      </div>

      <div className="card">
        <div className="card-h">🔍 Consulta en lenguaje corriente</div>
        <div className="card-b">
          <div className="chat-envio">
            <input
              className="tin" value={consulta}
              onChange={(e) => setConsulta(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void buscar(); }}
              placeholder="Ej.: cómo protejo las contraseñas de los usuarios"
            />
            <button className="btn" onClick={() => void buscar()} disabled={cargando}>
              {cargando ? "Buscando…" : "🔍 Buscar"}
            </button>
          </div>

          <div className="ejemplos">
            Probá con una consulta:
            <div>
              {EJEMPLOS.map((e) => (
                <span
                  key={e.etiqueta}
                  className="ej"
                  title={e.consulta}
                  onClick={() => { setConsulta(e.consulta); void buscar(e.consulta); }}
                >
                  {e.etiqueta}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        {cargando && <Cargando />}
        {!cargando && error && <Aviso mensaje="No se pudo buscar" detalle={error} />}

        {!cargando && datos && datos.resultados.length === 0 && (
          <div className="rel">
            <div className="rt">Nada del histórico se parece a eso</div>
            <div className="rx">
              Ningún documento superó el umbral de parecido. Con una consulta ajena al
              contenido técnico, eso es la respuesta correcta.
            </div>
          </div>
        )}

        {!cargando && mostrados.map((r) => (
          <div className="rel" key={r.id}>
            <div className="rel-h">
              <div className="rt">{r.titulo}</div>
              <span className="sim" title="parecido de significado, coseno de -1 a 1">
                {r.parecido.toFixed(2)}
              </span>
            </div>
            {r.extracto && <div className="rx">{r.extracto}</div>}
            <div className="rc">
              <span className="rdot" style={{ background: colorDe(r.categoria) }} />
              {r.categoria}
            </div>
          </div>
        ))}

        {!cargando && datos && datos.resultados.length > 0 && (
          <div className="rel-nota">
            {datos.total} de {datos.documentos_comparados.toLocaleString("es")} documentos
            superaron el umbral
            {ofrecerTraduccion && (
              <BotonTraducir
                traducido={traducciones.size > 0}
                ocupado={traduciendo}
                alPulsar={() => void alternarTraduccion()}
              />
            )}
            {errorTrad && (
              <span style={{ color: "var(--muted)", marginLeft: 8, fontSize: 12 }}>
                {errorTrad}
              </span>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
