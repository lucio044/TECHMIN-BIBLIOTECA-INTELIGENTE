/** Entrenar un clasificador con las categorías de quien lo usa.
 *
 *  Es la respuesta a «mi empresa no usa esas ocho categorías»: se sube un
 *  CSV con las propias y el modelo se entrena en el momento. */

import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { ErrorApi } from "../lib/api";
import { Cargando, Error as Aviso } from "../components/Comunes";
import type { ModeloPropio } from "../types";

export default function Propios() {
  const [modelos, setModelos] = useState<ModeloPropio[]>([]);
  const [nombre, setNombre] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [entrenando, setEntrenando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  const [prueba, setPrueba] = useState("");
  const [resultados, setResultados] = useState<Record<string, string>>({});

  useEffect(() => { void refrescar(); }, []);

  async function refrescar() {
    setCargando(true);
    try {
      setModelos(await api.listarModelos());
      setError(null);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudieron listar los modelos.");
    } finally {
      setCargando(false);
    }
  }

  async function entrenar() {
    if (!archivo) { setError("Elegí un CSV con las columnas texto y categoria."); return; }
    if (!nombre.trim()) { setError("Poné un nombre para reconocerlo después."); return; }

    setEntrenando(true);
    setError(null);
    try {
      await api.entrenarModelo(archivo, nombre.trim());
      setNombre("");
      setArchivo(null);
      await refrescar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo entrenar.");
    } finally {
      setEntrenando(false);
    }
  }

  async function borrar(id: string) {
    try {
      await api.borrarModelo(id);
      await refrescar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo borrar.");
    }
  }

  async function probarTodos() {
    if (prueba.trim().length < 10) { setError("Escribí un texto un poco más largo."); return; }
    const salida: Record<string, string> = {};
    for (const m of modelos) {
      try {
        const r = await api.clasificarConModelo(m.id, prueba.trim());
        salida[m.id] = `${r.categoria} · ${Math.round(r.probabilidad * 100)}%`;
      } catch {
        salida[m.id] = "no respondió";
      }
    }
    setResultados(salida);
  }

  return (
    <section>
      <div className="hero">
        <h1>Categorías propias</h1>
        <div className="sub">
          Subí un CSV con columnas <code>texto</code> y <code>categoria</code> y entrená un
          clasificador con tus propias categorías, sin tocar el modelo principal.
        </div>
      </div>

      <div className="card">
        <div className="card-h">🧪 Entrenar uno nuevo</div>
        <div className="card-b">
          <label className="lab" htmlFor="nombre">Nombre</label>
          <input
            className="tin" id="nombre" value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder="Ej.: tickets de soporte"
          />

          <label className="lab" htmlFor="csv">Archivo CSV</label>
          <input
            className="tin" id="csv" type="file" accept=".csv,text/csv"
            onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
          />

          <button className="btn" onClick={() => void entrenar()} disabled={entrenando}>
            {entrenando ? "Entrenando…" : "Entrenar"}
          </button>

          {error && <div style={{ marginTop: 12 }}><Aviso mensaje={error} /></div>}
        </div>
      </div>

      {cargando && <Cargando />}

      {!cargando && modelos.length > 0 && (
        <>
          <div className="card" style={{ marginTop: 16 }}>
            <div className="card-h">⚖️ Probar el mismo texto en todos</div>
            <div className="card-b">
              <textarea
                className="tin" value={prueba}
                onChange={(e) => setPrueba(e.target.value)}
                placeholder="Pegá un texto y comparalo contra todos tus modelos…"
              />
              <button className="btn" onClick={() => void probarTodos()}>Comparar</button>
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            {modelos.map((m) => (
              <div className="rel" key={m.id}>
                <div className="rel-h">
                  <div className="rt">{m.nombre}</div>
                  <span className="sim" title="F1 macro sobre su propia partición retenida">
                    {m.f1_macro.toFixed(2)}
                  </span>
                </div>
                <div className="rx">
                  {m.ejemplos} ejemplos · {m.categorias.length} categorías:{" "}
                  {m.categorias.join(", ")}
                  {m.entrenado && ` · ${new Date(m.entrenado).toLocaleDateString("es")}`}
                </div>
                <div className="rc">
                  {resultados[m.id] && <span className="peso">{resultados[m.id]}</span>}
                  <span style={{ marginLeft: "auto" }}>
                    <button className="btn-sm" onClick={() => void borrar(m.id)}>Borrar</button>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {!cargando && modelos.length === 0 && !error && (
        <div className="chat-vacio">
          Todavía no entrenaste ninguno.<br />
          El CSV necesita una columna <code>texto</code> y una <code>categoria</code>.
        </div>
      )}
    </section>
  );
}
