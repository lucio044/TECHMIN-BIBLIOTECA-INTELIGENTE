/** Búsqueda semántica: encuentra documentos que hablan de lo mismo aunque
 *  no compartan ni un término con lo que se escribió. */

import { useState } from "react";
import * as api from "../lib/api";
import { ErrorApi } from "../lib/api";
import { pareceIngles, preguntoEnIngles } from "../lib/idioma";
import { BotonTraducir, Cargando, Error as Aviso, colorDe } from "../components/Comunes";
import type { RespuestaSemantica, ResultadoSemantico } from "../types";

const EJEMPLOS = [
  "cómo protejo las contraseñas de los usuarios",
  "la aplicación se cierra sola en el celular",
  "guardar millones de registros y buscarlos rápido",
  "que el servidor se levante solo al reiniciar",
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
        <h1>Buscar por significado</h1>
        <div className="sub">
          Describí lo que necesitás con tus palabras. Encuentra documentos que hablan de eso
          aunque no compartan ni un término con lo que escribiste — y aunque estén en otro idioma.
        </div>
      </div>

      <div className="card">
        <div className="card-b">
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <input
              className="tin" value={consulta} style={{ flex: "1 1 260px" }}
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
                <span key={e} className="ej" onClick={() => { setConsulta(e); void buscar(e); }}>
                  {e}
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
