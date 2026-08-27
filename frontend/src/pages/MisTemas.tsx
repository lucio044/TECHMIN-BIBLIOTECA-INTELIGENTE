/** Mis temas — cómo se reparte lo que esta persona fue guardando.
 *
 *  No busca nada: mira la biblioteca del navegador y la resume. En el
 *  prototipo era asi, y convertirla en un buscador la volvio indistinguible
 *  de la busqueda semantica, que es de donde salio la confusion.
 *
 *  La busqueda por termino contra el historico vive donde estaba: en la
 *  pestaña Clasificar, bajo «O explora el historico por termino». */

import { useMemo } from "react";
import { COLORES, colorDe } from "../components/Comunes";
import type { EntradaBiblioteca } from "../types";

const CATEGORIAS = Object.keys(COLORES);

export default function MisTemas({ entradas }: { entradas: EntradaBiblioteca[] }) {
  const cuentas = useMemo(() => {
    const m: Record<string, number> = {};
    for (const e of entradas) m[e.categoria] = (m[e.categoria] ?? 0) + 1;
    return m;
  }, [entradas]);

  // Los temas mas frecuentes salen de las palabras clave que devolvio el
  // modelo en cada clasificacion, no de una lista escrita a mano.
  const temas = useMemo(() => {
    const f: Record<string, number> = {};
    for (const e of entradas) {
      for (const p of e.palabras ?? []) {
        const k = p.trim();
        if (k) f[k] = (f[k] ?? 0) + 1;
      }
    }
    return Object.entries(f).sort((a, b) => b[1] - a[1]).slice(0, 14);
  }, [entradas]);

  const usadas = Object.keys(cuentas).length;
  const confianza = entradas.length
    ? Math.round((entradas.reduce((s, e) => s + e.probabilidad, 0) / entradas.length) * 100)
    : 0;

  if (entradas.length === 0) {
    return (
      <section>
        <div className="hero">
          <h1>Mis <span className="gr">temas</span></h1>
          <div className="sub">
            Cómo se distribuye y de qué habla el conocimiento que fuiste guardando.
          </div>
        </div>
        <div className="chat-vacio">
          Todavía no clasificaste nada.<br />
          Cuando lo hagas, acá vas a ver de qué temas se trata tu biblioteca.
        </div>
      </section>
    );
  }

  const maximo = Math.max(1, ...Object.values(cuentas));
  const maxFrec = Math.max(1, ...temas.map(([, f]) => f));

  return (
    <section>
      <div className="hero">
        <h1>Mis <span className="gr">temas</span></h1>
        <div className="sub">
          Cómo se distribuye y de qué habla el conocimiento que fuiste guardando.
        </div>
      </div>

      <div className="stats">
        <div className="stat">
          <div className="k">Contenidos organizados</div>
          <div className="v grad">{entradas.length}</div>
        </div>
        <div className="stat">
          <div className="k">Categorías activas</div>
          <div className="v">
            {usadas}<span style={{ fontSize: 16, color: "var(--muted)" }}> / 8</span>
          </div>
        </div>
        <div className="stat">
          <div className="k">Confianza promedio</div>
          <div className="v">{confianza}%</div>
        </div>
        <div className="stat">
          <div className="k">Temas únicos</div>
          <div className="v">{temas.length}</div>
        </div>
      </div>

      <div className="panel-cols">
        <div className="card">
          <div className="card-h">📚 Distribución por categoría</div>
          <div className="card-b">
            {CATEGORIAS.filter((c) => cuentas[c] > 0)
              .sort((a, b) => cuentas[b] - cuentas[a])
              .map((c) => (
                <div className="dist-row" key={c}>
                  <span className="dn">
                    <span className="dd" style={{ background: colorDe(c) }} />
                    {c}
                  </span>
                  <span className="dist-bar">
                    <i style={{
                      width: `${(cuentas[c] / maximo) * 100}%`,
                      background: `linear-gradient(90deg,${COLORES[c][0]},${COLORES[c][1]})`,
                    }} />
                  </span>
                  <span className="dv">{cuentas[c]}</span>
                </div>
              ))}
          </div>
        </div>

        <div className="card">
          <div className="card-h">🏷️ Temas más frecuentes</div>
          <div className="card-b kwcloud">
            {temas.length === 0 && <span style={{ color: "#5c6885" }}>Sin datos aún.</span>}
            {/* El tamaño de cada término es proporcional a cuántas veces
                aparece, que es lo que convierte la lista en una nube. */}
            {temas.map(([k, f]) => (
              <span
                key={k}
                className="chip"
                style={{ fontSize: `${(12 + (f / maxFrec) * 9).toFixed(0)}px` }}
              >
                {k} <b style={{ opacity: 0.5 }}>{f}</b>
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
