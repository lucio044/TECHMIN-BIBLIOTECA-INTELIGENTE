/** Lo que esta persona clasificó, guardado en su navegador. */

import { useMemo, useState } from "react";
import { colorDe } from "../components/Comunes";
import type { EntradaBiblioteca } from "../types";

export default function Biblioteca({
  entradas, alQuitar,
}: {
  entradas: EntradaBiblioteca[];
  alQuitar: (id: string) => void;
}) {
  const [filtro, setFiltro] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState("");

  const porCategoria = useMemo(() => {
    const m = new Map<string, number>();
    for (const e of entradas) m.set(e.categoria, (m.get(e.categoria) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [entradas]);

  const visibles = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    return entradas.filter((e) =>
      (!filtro || e.categoria === filtro) &&
      (!q || e.titulo.toLowerCase().includes(q) || e.texto.toLowerCase().includes(q)));
  }, [entradas, filtro, busqueda]);

  if (entradas.length === 0) {
    return (
      <section>
        <div className="hero">
          <h1>Tu biblioteca</h1>
          <div className="sub">Todavía no clasificaste nada.</div>
        </div>
        <div className="chat-vacio">
          Cada contenido que clasifiques se archiva acá,<br />con su categoría y sus palabras clave.
        </div>
      </section>
    );
  }

  return (
    <section>
      <div className="hero">
        <h1>Tu biblioteca</h1>
        <div className="sub">
          {entradas.length} contenido{entradas.length === 1 ? "" : "s"} archivado
          {entradas.length === 1 ? "" : "s"} en este navegador.
        </div>
      </div>

      <div className="card">
        <div className="card-b">
          <input
            className="tin" value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar en lo que guardaste…"
          />
          <div className="ejemplos" style={{ marginTop: 12 }}>
            <div>
              <span
                className={`ej${filtro === null ? " activo" : ""}`}
                onClick={() => setFiltro(null)}
              >
                Todas ({entradas.length})
              </span>
              {porCategoria.map(([cat, n]) => (
                <span
                  key={cat}
                  className={`ej${filtro === cat ? " activo" : ""}`}
                  onClick={() => setFiltro(filtro === cat ? null : cat)}
                >
                  {cat} ({n})
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        {visibles.length === 0 && (
          <div className="chat-vacio">Nada coincide con ese filtro.</div>
        )}
        {visibles.map((e) => (
          <div className="rel" key={e.id}>
            <div className="rel-h">
              <div className="rt">{e.titulo}</div>
              <span className="sim">{Math.round(e.probabilidad * 100)}%</span>
            </div>
            <div className="rx">{e.texto.slice(0, 220)}{e.texto.length > 220 ? "…" : ""}</div>
            <div className="rc">
              <span className="rdot" style={{ background: colorDe(e.categoria) }} />
              {e.categoria}
              <span style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}>
                <span style={{ color: "var(--muted)", fontSize: 11 }}>
                  {new Date(e.fecha).toLocaleDateString("es")}
                </span>
                <button className="btn-sm" onClick={() => alQuitar(e.id)}>Quitar</button>
              </span>
            </div>
            {e.palabras.length > 0 && (
              <div className="kwcloud" style={{ marginTop: 8 }}>
                {e.palabras.map((p) => <span className="peso" key={p}>{p}</span>)}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
