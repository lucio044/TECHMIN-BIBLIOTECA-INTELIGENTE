/** Lo que el modelo declara de sí mismo: cómo está hecho y cuánto acierta,
 *  por categoría. Sale de /v1/metricas, que lee el JSON que produce el
 *  notebook de entrenamiento — no son números escritos a mano en la página. */

import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { Cargando, Error as Aviso, colorDe } from "../components/Comunes";
import type { Metricas } from "../types";

export default function Dashboard() {
  const [datos, setDatos] = useState<Metricas | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    api.metricas()
      .then((m) => { if (vivo) setDatos(m); })
      .catch((e: Error) => { if (vivo) setError(e.message); });
    return () => { vivo = false; };
  }, []);

  if (error) return <section><Aviso mensaje="No se pudieron leer las métricas" detalle={error} /></section>;
  if (!datos) return <section><Cargando /></section>;

  const { modelo, rendimiento } = datos;
  const porCategoria = Object.entries(rendimiento.por_categoria)
    .sort((a, b) => b[1].f1 - a[1].f1);
  const vecesMejor = rendimiento.f1_macro / rendimiento.linea_base_f1_macro;

  return (
    <section>
      <div className="hero">
        <h1>Cómo está hecho el modelo</h1>
        <div className="sub">
          Medido sobre {rendimiento.textos_de_prueba.toLocaleString("es")} textos que el modelo
          no vio al entrenar.
        </div>
      </div>

      <div className="stats">
        <div className="stat">
          <div className="v">{rendimiento.f1_macro.toFixed(4)}</div>
          <div className="k">F1 macro</div>
        </div>
        <div className="stat">
          <div className="v">{(rendimiento.accuracy * 100).toFixed(1)}%</div>
          <div className="k">exactitud</div>
        </div>
        <div className="stat">
          <div className="v">{vecesMejor.toFixed(0)}×</div>
          <div className="k">sobre la línea base</div>
        </div>
        <div className="stat">
          <div className="v">{rendimiento.validacion_cruzada.media.toFixed(4)}</div>
          <div className="k">validación cruzada (5)</div>
        </div>
      </div>

      <div className="grid" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="card-h">📊 Acierto por categoría</div>
          <div className="card-b">
            {porCategoria.map(([cat, m]) => (
              <div className="rank-row" key={cat}>
                <span className="name">{cat}</span>
                <span className="rank-bar">
                  <i style={{ width: `${m.f1 * 100}%`, background: colorDe(cat) }} />
                </span>
                <span className="pc">{m.f1.toFixed(2)}</span>
              </div>
            ))}
            <div className="rel-nota" style={{ marginTop: 12 }}>
              La línea base —responder siempre la categoría más común— da un F1 macro de{" "}
              {rendimiento.linea_base_f1_macro.toFixed(4)}.
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-h">⚙️ Configuración</div>
          <div className="card-b">
            <Fila k="Algoritmo" v={modelo.algoritmo} />
            <Fila k="Categorías" v={String(modelo.categorias)} />
            <Fila k="Vocabulario" v={modelo.vocabulario.toLocaleString("es")} />
            <Fila k="N-gramas" v={`${modelo.ngramas[0]} a ${modelo.ngramas[1]}`} />
            <Fila k="Regularización C" v={String(modelo.regularizacion_C)} />
            <Fila k="Pesos balanceados" v={modelo.pesos_balanceados ? "sí" : "no"} />
            <div className="rel-nota" style={{ marginTop: 12 }}>
              Los pesos balanceados compensan que Seguridad tenga la mitad de ejemplos que
              Frontend.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const Fila = ({ k, v }: { k: string; v: string }) => (
  <div className="dist-row">
    <span>{k}</span>
    <span className="dv">{v}</span>
  </div>
);
