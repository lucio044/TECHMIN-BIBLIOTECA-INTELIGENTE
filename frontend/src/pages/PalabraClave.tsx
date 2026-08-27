/** Búsqueda por palabras clave — otro de los recursos del enunciado.
 *
 *  No es lo mismo que la búsqueda semántica y conviene que se note, porque
 *  usar la equivocada da resultados malos sin avisar. Medido contra la API:
 *
 *    «docker»                              aca: Jenkins Docker, Docker
 *                                     semantica: Docker run, Container Overview
 *                                     --cero documentos en comun--
 *
 *    «la aplicacion se cierra sola»        aca: Oracle Virtual Machine,
 *                                              Cliente-servidor, Leetcode
 *                                     semantica: Aplicacion movil, Telefono
 *
 *  Con una palabra esta pantalla es precisa: encuentra donde aparece ese
 *  termino. Con una frase se rompe, porque empieza a casar palabras sueltas.
 *  Por eso la entrada avisa cuando se escriben varias. */

import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { ErrorApi } from "../lib/api";
import { Cargando, Error as Aviso, colorDe } from "../components/Comunes";
import type { RespuestaBusqueda } from "../types";
import type { Vista } from "../App";

const MAX_PALABRAS = 3;

export default function PalabraClave({ irA }: { irA: (v: Vista) => void }) {
  const [termino, setTermino] = useState("");
  const [chips, setChips] = useState<string[]>([]);
  const [datos, setDatos] = useState<RespuestaBusqueda | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    api.sugerencias()
      .then((s) => { if (vivo) setChips(s.sugerencias.slice(0, 14)); })
      .catch(() => { /* sin sugerencias la pantalla funciona igual */ });
    return () => { vivo = false; };
  }, []);

  const palabras = termino.trim().split(/\s+/).filter(Boolean).length;
  const demasiadas = palabras > MAX_PALABRAS;

  async function explorar(t = termino) {
    if (t.trim().length < 2) {
      setError("El término necesita al menos dos caracteres.");
      return;
    }
    setCargando(true);
    setError(null);
    try {
      setDatos(await api.buscarTermino(t.trim(), 10));
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo buscar.");
      setDatos(null);
    } finally {
      setCargando(false);
    }
  }

  return (
    <section>
      <div className="hero">
        <h1>Por <span className="gr">palabra clave</span></h1>
        <div className="sub">
          Encuentra los documentos donde <b>aparece literalmente</b> el término que escribas.
          Si querés describir un problema con tus palabras, eso es{" "}
          <a
            href="#semantica"
            onClick={(e) => { e.preventDefault(); irA("semantica"); }}
            style={{ color: "var(--grad2)" }}
          >
            Búsqueda semántica
          </a>.
        </div>
      </div>

      <div className="card">
        <div className="card-b">
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <input
              className="tin" value={termino} style={{ flex: "1 1 240px" }}
              onChange={(e) => setTermino(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void explorar(); }}
              placeholder="Una palabra: docker, jwt, postgres…"
            />
            <button className="btn" onClick={() => void explorar()} disabled={cargando}>
              {cargando ? "Buscando…" : "Explorar"}
            </button>
          </div>

          {/* Escribir una frase aca da resultados malos sin avisar --se
              comprobo con «la aplicacion se cierra sola en el celular», que
              devuelve Oracle Virtual Machine y Leetcode--. Mejor decirlo
              antes que devolver ruido. */}
          {demasiadas && (
            <div className="rel-nota" style={{ marginTop: 10 }}>
              Escribiste {palabras} palabras. Esta búsqueda funciona con{" "}
              <b>un término</b>; con una frase va a casar palabras sueltas y traer cosas que no
              tienen que ver.{" "}
              <button
                className="btn-sm"
                onClick={() => irA("semantica")}
                style={{ marginLeft: 6 }}
              >
                Llevame a Búsqueda semántica
              </button>
            </div>
          )}

          {chips.length > 0 && (
            <div className="ejemplos">
              Términos frecuentes en el histórico:
              <div>
                {chips.map((c) => (
                  <span key={c} className="ej" onClick={() => { setTermino(c); void explorar(c); }}>
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        {cargando && <Cargando />}
        {!cargando && error && <Aviso mensaje="No se pudo buscar" detalle={error} />}

        {!cargando && datos && datos.resultados.length === 0 && (
          <div className="chat-vacio">
            Ningún documento contiene «{datos.termino}».<br />
            Probá con un término más común, o describí lo que buscás en Búsqueda semántica.
          </div>
        )}

        {!cargando && datos?.resultados.map((r) => (
          <div className="rel" key={r.id}>
            <div className="rt">{r.titulo}</div>
            {r.extracto && <div className="rx">{r.extracto}</div>}
            <div className="rc">
              <span className="rdot" style={{ background: colorDe(r.categoria) }} />
              {r.categoria}
            </div>
          </div>
        ))}

        {!cargando && datos && datos.resultados.length > 0 && (
          <div className="rel-nota">
            {datos.total} documentos contienen «{datos.termino}»
          </div>
        )}
      </div>
    </section>
  );
}
