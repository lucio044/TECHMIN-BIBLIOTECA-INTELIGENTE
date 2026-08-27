/** Explorar el histórico por término, que es la búsqueda léxica --distinta
 *  de la semántica: acá el término tiene que aparecer de verdad. */

import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { ErrorApi } from "../lib/api";
import { Cargando, Error as Aviso, colorDe } from "../components/Comunes";
import type { RespuestaBusqueda } from "../types";

export default function MisTemas() {
  const [termino, setTermino] = useState("");
  const [chips, setChips] = useState<string[]>([]);
  const [datos, setDatos] = useState<RespuestaBusqueda | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    api.sugerencias()
      .then((s) => { if (vivo) setChips(s.sugerencias.slice(0, 12)); })
      .catch(() => { /* sin sugerencias la vista funciona igual */ });
    return () => { vivo = false; };
  }, []);

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
      setError(e instanceof ErrorApi ? e.message : "No se pudo explorar.");
      setDatos(null);
    } finally {
      setCargando(false);
    }
  }

  return (
    <section>
      <div className="hero">
        <h1>Explorar por término</h1>
        <div className="sub">
          Busca documentos donde el término aparece literalmente. Para buscar por significado
          está la pestaña Buscar.
        </div>
      </div>

      <div className="card">
        <div className="card-b">
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <input
              className="tin" value={termino} style={{ flex: "1 1 240px" }}
              onChange={(e) => setTermino(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void explorar(); }}
              placeholder="Ej.: docker, jwt, postgres…"
            />
            <button className="btn" onClick={() => void explorar()} disabled={cargando}>
              {cargando ? "Buscando…" : "Explorar"}
            </button>
          </div>

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
        {!cargando && error && <Aviso mensaje="No se pudo explorar" detalle={error} />}
        {!cargando && datos?.resultados.length === 0 && (
          <div className="chat-vacio">Ningún documento contiene «{datos.termino}».</div>
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
          <div className="rel-nota">{datos.total} documentos contienen «{datos.termino}»</div>
        )}
      </div>
    </section>
  );
}
