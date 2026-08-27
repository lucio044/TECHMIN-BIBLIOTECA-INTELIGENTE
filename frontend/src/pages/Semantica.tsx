/** Búsqueda semántica — el recurso que pide el enunciado.
 *
 *  Antes esto eran dos pestañas con el mismo campo de texto: una devolvía
 *  la lista de documentos parecidos y otra una respuesta redactada. Nadie
 *  entendía cuál usar, asi que se preguntaban lo mismo dos veces.
 *
 *  Ahora es una sola: se escribe una vez, y se muestran las dos cosas —
 *  primero la respuesta, y debajo los documentos de donde sale. Los dos
 *  endpoints siguen existiendo por separado en la API.
 *
 *  Se consultan en paralelo, no en cadena: el sintetizador tarda unos
 *  190 ms y la búsqueda unos 510, así que en serie serían 700 y en
 *  paralelo el tiempo del más lento. */

import { useState } from "react";
import * as api from "../lib/api";
import { ErrorApi } from "../lib/api";
import { pareceIngles, preguntoEnIngles } from "../lib/idioma";
import { BotonTraducir, Cargando, Error as Aviso, colorDe } from "../components/Comunes";
import type {
  MensajeChat, RespuestaChat, RespuestaSemantica, ResultadoSemantico,
} from "../types";

// Los cuatro se probaron contra la API en vivo y devuelven material del
// tema. Se descarto «para que sirve Docker», que daba 0,52 con un documento
// llamado «Bagel Bot Reimaging Donut»: la forma interrogativa arruina el
// embedding, y «como desplegar contenedores» --que es la misma idea-- da
// 0,60 con «Containers and Introduction to Docker».
const EJEMPLOS = [
  "qué es un índice en una base de datos",
  "cómo protejo las contraseñas de los usuarios",
  "cómo desplegar contenedores",
  "la aplicación se cierra sola en el celular",
];

const LARGO_MINIMO = 3;

interface Consulta {
  pregunta: string;
  respuesta?: RespuestaChat;
  documentos?: RespuestaSemantica;
  error?: string;
  traduccionCita?: string[];
  traduccionDocs?: Map<number, ResultadoSemantico>;
}

export default function Semantica({ hayTraductor }: { hayTraductor: boolean }) {
  const [consultas, setConsultas] = useState<Consulta[]>([]);
  const [entrada, setEntrada] = useState("");
  const [cargando, setCargando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [traduciendo, setTraduciendo] = useState<string | null>(null);

  async function preguntar(texto = entrada) {
    const limpio = texto.trim();
    if (limpio.length < LARGO_MINIMO) {
      setAviso("Escribí algo un poco más largo.");
      return;
    }
    setAviso(null);
    setEntrada("");
    setCargando(true);

    // El historial va porque el endpoint lo acepta y es lo correcto segun su
    // contrato. Medido: hoy no cambia la respuesta --«y para que sirve»
    // devuelve «sin_informacion» con historial y sin el--, asi que la
    // interfaz no promete preguntas de seguimiento. Si el sintetizador
    // empieza a usarlo, ya le llega.
    const historial: MensajeChat[] = consultas.flatMap((c) =>
      c.respuesta
        ? ([
            { rol: "user", contenido: c.pregunta },
            { rol: "assistant", contenido: c.respuesta.respuesta },
          ] as MensajeChat[])
        : [],
    );

    const [chat, semantica] = await Promise.allSettled([
      api.preguntar(limpio, historial),
      api.buscarSemantica(limpio, 5),
    ]);

    const nueva: Consulta = { pregunta: limpio };
    if (chat.status === "fulfilled") nueva.respuesta = chat.value;
    if (semantica.status === "fulfilled") nueva.documentos = semantica.value;
    if (chat.status === "rejected" && semantica.status === "rejected") {
      nueva.error =
        chat.reason instanceof ErrorApi ? chat.reason.message : "No se pudo consultar la API.";
    }

    setConsultas((c) => [...c, nueva]);
    setCargando(false);
  }

  async function traducirCita(i: number) {
    const c = consultas[i];
    const frags = c.respuesta?.del_historico?.fragmentos;
    if (!frags) return;
    if (c.traduccionCita) {
      setConsultas((cs) => cs.map((x, k) => (k === i ? { ...x, traduccionCita: undefined } : x)));
      return;
    }
    setTraduciendo(`cita-${i}`);
    try {
      const { traducciones } = await api.traducir(frags.map((f) => f.texto), "es");
      setConsultas((cs) => cs.map((x, k) => (k === i ? { ...x, traduccionCita: traducciones } : x)));
    } catch {
      setAviso("No se pudo traducir.");
    } finally {
      setTraduciendo(null);
    }
  }

  async function traducirDocs(i: number) {
    const c = consultas[i];
    const docs = c.documentos?.resultados;
    if (!docs) return;
    if (c.traduccionDocs) {
      setConsultas((cs) => cs.map((x, k) => (k === i ? { ...x, traduccionDocs: undefined } : x)));
      return;
    }
    setTraduciendo(`docs-${i}`);
    try {
      const piezas = docs.flatMap((d) => [d.titulo, d.extracto]);
      const { traducciones } = await api.traducir(piezas, "es");
      const mapa = new Map<number, ResultadoSemantico>();
      docs.forEach((d, k) => {
        mapa.set(d.id, {
          ...d,
          titulo: traducciones[k * 2] ?? d.titulo,
          extracto: traducciones[k * 2 + 1] ?? d.extracto,
        });
      });
      setConsultas((cs) => cs.map((x, k) => (k === i ? { ...x, traduccionDocs: mapa } : x)));
    } catch {
      setAviso("No se pudo traducir.");
    } finally {
      setTraduciendo(null);
    }
  }

  return (
    <section>
      <div className="hero">
        <h1>
          Búsqueda <span className="gr">semántica</span>
          {consultas.length > 0 && (
            <button className="btn-limpiar" onClick={() => { setConsultas([]); setAviso(null); }}>
              Empezar de nuevo
            </button>
          )}
        </h1>
        <div className="sub">
          Preguntá con tus palabras. El modelo redacta la respuesta desde los documentos del
          histórico y te muestra de cuáles la sacó — aunque no compartan ni un término con lo
          que escribiste.
        </div>
      </div>

      <div className="card">
        <div className="card-b">
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <input
              className="tin" value={entrada} style={{ flex: "1 1 260px" }}
              onChange={(e) => setEntrada(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void preguntar(); }}
              placeholder="Ej.: qué es un índice en una base de datos"
            />
            <button className="btn" onClick={() => void preguntar()} disabled={cargando}>
              {cargando ? "Buscando…" : "🔍 Buscar"}
            </button>
          </div>

          {aviso && (
            <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>{aviso}</div>
          )}

          {consultas.length === 0 && (
            <div className="ejemplos">
              Probá con:
              <div>
                {EJEMPLOS.map((e) => (
                  <span key={e} className="ej" onClick={() => void preguntar(e)}>{e}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {consultas.map((c, i) => {
        const h = c.respuesta?.del_historico;
        const enEspanol = !preguntoEnIngles(c.pregunta);

        const ofrecerCita =
          hayTraductor && enEspanol && !!h && h.fragmentos.some((f) => pareceIngles(f.texto));

        const docs = c.documentos?.resultados.map((d) => c.traduccionDocs?.get(d.id) ?? d) ?? [];
        const ofrecerDocs =
          hayTraductor && enEspanol && !!c.documentos?.resultados.length &&
          c.documentos.resultados.some((d) => pareceIngles(`${d.titulo} ${d.extracto}`));

        return (
          <div key={i} style={{ marginTop: 22 }}>
            <div className="sec-lbl">Preguntaste</div>
            <div className="burbuja mia" style={{ marginBottom: 14 }}>{c.pregunta}</div>

            {c.error && <Aviso mensaje="No se pudo consultar" detalle={c.error} />}

            {/* --- la respuesta --- */}
            {c.respuesta && (
              <>
                <div className="sec-lbl">Respuesta</div>
                <div className="card">
                  <div className="card-b">
                    <div>{c.respuesta.respuesta}</div>

                    {h && (
                      <>
                        <div className="cita">
                          {h.fragmentos.map((f, k) => (
                            <div className="frag" key={k}>
                              {f.parte !== undefined && <span className="np">[{f.parte}]</span>}
                              {c.traduccionCita?.[k] ?? f.texto}
                            </div>
                          ))}
                        </div>
                        <div className="cita-pie">
                          <span>fuente: <b>{h.fuente}</b></span>
                          <span>{h.categoria}</span>
                          <span>parecido {h.parecido.toFixed(2)}</span>
                          {ofrecerCita && (
                            <BotonTraducir
                              traducido={!!c.traduccionCita}
                              ocupado={traduciendo === `cita-${i}`}
                              alPulsar={() => void traducirCita(i)}
                            />
                          )}
                        </div>
                      </>
                    )}

                    {c.respuesta.terminos_decisivos && c.respuesta.terminos_decisivos.length > 0 && (
                      <div className="pesos">
                        {c.respuesta.terminos_decisivos.map((t) => (
                          <span className="peso" key={t.termino}>
                            {t.termino} <b>{t.aporte >= 0 ? "+" : ""}{t.aporte.toFixed(2)}</b>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}

            {/* --- los documentos de donde sale --- */}
            {docs.length > 0 && (
              <>
                <div className="sec-lbl" style={{ marginTop: 18 }}>
                  Documentos más parecidos
                </div>
                {docs.map((d) => (
                  <div className="rel" key={d.id}>
                    <div className="rel-h">
                      <div className="rt">{d.titulo}</div>
                      <span className="sim" title="parecido de significado, coseno de -1 a 1">
                        {d.parecido.toFixed(2)}
                      </span>
                    </div>
                    {d.extracto && <div className="rx">{d.extracto}</div>}
                    <div className="rc">
                      <span className="rdot" style={{ background: colorDe(d.categoria) }} />
                      {d.categoria}
                    </div>
                  </div>
                ))}
                <div className="rel-nota">
                  {c.documentos!.total} de{" "}
                  {c.documentos!.documentos_comparados.toLocaleString("es")} documentos superaron
                  el umbral de parecido
                  {ofrecerDocs && (
                    <BotonTraducir
                      traducido={!!c.traduccionDocs}
                      ocupado={traduciendo === `docs-${i}`}
                      alPulsar={() => void traducirDocs(i)}
                    />
                  )}
                </div>
              </>
            )}

            {/* Que el sintetizador no encuentre corroboracion no significa que
                no haya nada: exige dos fragmentos de la misma fuente, y la
                lista de abajo puede tener material igual. Antes eso obligaba
                a cambiar de pestaña para enterarse. */}
            {c.respuesta?.tipo === "sin_informacion" && docs.length > 0 && (
              <div className="rel-nota" style={{ marginTop: 10 }}>
                No hubo una fuente con respaldo suficiente para redactar una respuesta, pero
                estos documentos sí hablan del tema.
              </div>
            )}
          </div>
        );
      })}

      {cargando && <div style={{ marginTop: 20 }}><Cargando /></div>}
    </section>
  );
}
