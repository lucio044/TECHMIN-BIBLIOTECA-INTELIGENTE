/** El asistente responde desde el propio histórico, sin modelos externos.
 *
 *  Cuando no encuentra nada lo dice, en lugar de inventar: es la diferencia
 *  entre citar una fuente y sonar convincente. */

import { useEffect, useRef, useState } from "react";
import * as api from "../lib/api";
import { ErrorApi } from "../lib/api";
import { pareceIngles, preguntoEnIngles } from "../lib/idioma";
import { BotonTraducir, Cargando, colorDe } from "../components/Comunes";
import type { RespuestaChat } from "../types";

interface Turno {
  rol: "user" | "asistente";
  contenido: string;
  datos?: RespuestaChat;
  traduccion?: string[];
}

const EJEMPLOS = ["¿Qué es XSS?", "¿Qué es un índice?", "¿Para qué sirve Docker?"];
const LARGO_MINIMO = 3;

export default function Asistente({ hayTraductor }: { hayTraductor: boolean }) {
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [entrada, setEntrada] = useState("");
  const [cargando, setCargando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [traduciendo, setTraduciendo] = useState<number | null>(null);
  const finRef = useRef<HTMLDivElement>(null);

  useEffect(() => { finRef.current?.scrollIntoView({ behavior: "smooth" }); }, [turnos, cargando]);

  async function enviar(texto = entrada) {
    const limpio = texto.trim();
    // El prototipo descartaba en silencio lo que midiera menos de 15, y eso
    // se tragaba hasta sus propias sugerencias: «¿Qué es XSS?» son 12.
    if (limpio.length < LARGO_MINIMO) {
      setAviso("Escribí una pregunta un poco más larga.");
      return;
    }

    setAviso(null);
    setEntrada("");
    setTurnos((t) => [...t, { rol: "user", contenido: limpio }]);
    setCargando(true);
    try {
      const datos = await api.preguntar(limpio);
      setTurnos((t) => [...t, { rol: "asistente", contenido: datos.respuesta, datos }]);
    } catch (e) {
      setTurnos((t) => [...t, {
        rol: "asistente",
        contenido: e instanceof ErrorApi ? e.message : "No se pudo conectar con la API.",
      }]);
    } finally {
      setCargando(false);
    }
  }

  async function traducirFragmentos(indice: number) {
    const turno = turnos[indice];
    const fragmentos = turno.datos?.del_historico?.fragmentos;
    if (!fragmentos) return;

    if (turno.traduccion) {
      setTurnos((t) => t.map((x, i) => (i === indice ? { ...x, traduccion: undefined } : x)));
      return;
    }

    setTraduciendo(indice);
    try {
      const { traducciones } = await api.traducir(fragmentos.map((f) => f.texto), "es");
      setTurnos((t) => t.map((x, i) => (i === indice ? { ...x, traduccion: traducciones } : x)));
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
          Asistente
          {turnos.length > 0 && (
            <button className="btn-limpiar" onClick={() => { setTurnos([]); setAviso(null); }}>
              Nueva conversación
            </button>
          )}
        </h1>
        <div className="sub">
          Responde desde los documentos del histórico y cita de dónde lo sacó. Si no encuentra
          nada, lo dice.
        </div>
      </div>

      <div className="card">
        <div className="card-b">
          <div className="chat-hilo">
            {turnos.length === 0 && !cargando && (
              <div className="chat-vacio">
                Preguntá algo técnico y el asistente busca la respuesta<br />
                entre los documentos del histórico.
              </div>
            )}

            {turnos.map((t, i) => {
              if (t.rol === "user") {
                return <div className="burbuja mia" key={i}>{t.contenido}</div>;
              }

              const h = t.datos?.del_historico;
              const pregunta = turnos[i - 1]?.rol === "user" ? turnos[i - 1].contenido : "";
              const ofrecer =
                hayTraductor && !!h &&
                !preguntoEnIngles(pregunta) &&
                h.fragmentos.some((f) => pareceIngles(f.texto));

              return (
                <div className="burbuja" key={i}>
                  <div>{t.contenido}</div>

                  {h && (
                    <>
                      <div className="cita">
                        {h.fragmentos.map((f, k) => (
                          <div className="frag" key={k}>
                            {f.parte !== undefined && <span className="np">[{f.parte}]</span>}
                            {t.traduccion?.[k] ?? f.texto}
                          </div>
                        ))}
                      </div>
                      <div className="cita-pie">
                        <span>fuente: <b>{h.fuente}</b></span>
                        <span>{h.categoria}</span>
                        <span>parecido {h.parecido.toFixed(2)}</span>
                        <span>entre {h.documentos_consultados.toLocaleString("es")} documentos</span>
                        {ofrecer && (
                          <BotonTraducir
                            traducido={!!t.traduccion}
                            ocupado={traduciendo === i}
                            alPulsar={() => void traducirFragmentos(i)}
                          />
                        )}
                      </div>
                    </>
                  )}

                  {t.datos?.terminos_decisivos && t.datos.terminos_decisivos.length > 0 && (
                    <div className="pesos">
                      {t.datos.terminos_decisivos.map((x) => (
                        <span className="peso" key={x.termino}>
                          {x.termino} <b>{x.aporte >= 0 ? "+" : ""}{x.aporte.toFixed(2)}</b>
                        </span>
                      ))}
                    </div>
                  )}

                  {t.datos?.categoria && t.datos.tipo !== "sin_informacion" && (
                    <div className="chat-meta">
                      <span className="rdot" style={{ background: colorDe(t.datos.categoria) }} />
                      {t.datos.categoria}
                      {t.datos.probabilidad !== undefined &&
                        ` · ${Math.round(t.datos.probabilidad * 100)}% de confianza`}
                      {" · redactado por el propio modelo"}
                    </div>
                  )}
                </div>
              );
            })}

            {cargando && <Cargando />}
            <div ref={finRef} />
          </div>

          {aviso && (
            <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>{aviso}</div>
          )}

          <div className="chat-envio">
            <input
              className="tin" value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void enviar(); }}
              placeholder="Preguntá algo técnico…"
            />
            <button className="btn" onClick={() => void enviar()} disabled={cargando}>
              Enviar
            </button>
          </div>

          <div className="ejemplos">
            Probá con:
            <div>
              {EJEMPLOS.map((e) => (
                <span key={e} className="ej" onClick={() => void enviar(e)}>{e}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
