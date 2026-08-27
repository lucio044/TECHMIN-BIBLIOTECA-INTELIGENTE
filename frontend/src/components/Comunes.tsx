/** Piezas que usan varias vistas. */

import type { Categoria } from "../types";

/** La paleta del prototipo, copiada tal cual.
 *
 *  No es decorativa: esta construida alrededor del violeta y el turquesa de
 *  la pagina. Invente una version propia al portar --naranjas, rosas, un
 *  amarillo chillon para Bases de Datos-- y desentonaba con el fondo. */
export const COLORES: Record<string, [string, string]> = {
  "Backend": ["#6d5efc", "#8b7dff"],
  "Frontend": ["#23d5c8", "#3ee6d8"],
  "Mobile": ["#2ecc71", "#4fe08a"],
  "Ciencia de Datos": ["#a855f7", "#c07bff"],
  "Bases de Datos": ["#f59e0b", "#ffbb3c"],
  "DevOps / Cloud": ["#38bdf8", "#5fd0ff"],
  "Seguridad": ["#f43f6e", "#ff6d90"],
  "Programación General": ["#94a3b8", "#b3c0d4"],
};

export const colorDe = (c: string) => COLORES[c]?.[0] ?? "#6d5efc";

export const Cargando = () => <div className="spinner" role="status" aria-label="Cargando" />;

export function Error({ mensaje, detalle }: { mensaje: string; detalle?: string }) {
  return (
    <div className="err">
      {mensaje}
      {detalle && (
        <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>{detalle}</div>
      )}
    </div>
  );
}

/** El anillo de confianza.
 *
 *  Las medidas son las del prototipo y no se pueden cambiar sueltas: la
 *  clase `.ring` mide 100 px, asi que un SVG de 120 se desborda y el trazo
 *  se ve como un aro gordo mal recortado. 100 de lado, radio 45, grosor 9.
 *
 *  El perimetro --2·pi·45-- es lo que consume el dasharray: se pinta la
 *  fraccion que corresponde a la confianza y el resto queda transparente.
 *  La rotacion de -90 grados la pone el CSS, que ya trae `.ring svg`. */
export function Anillo({ valor, categoria }: { valor: number; categoria: Categoria }) {
  const PERIMETRO = 2 * Math.PI * 45;
  const [color] = COLORES[categoria] ?? ["#6d5efc"];
  const pintado = valor * PERIMETRO;

  return (
    <div className="ring">
      <svg width="100" height="100" aria-hidden="true">
        <circle cx="50" cy="50" r="45" fill="none"
                stroke="rgba(255,255,255,.08)" strokeWidth="9" />
        <circle
          cx="50" cy="50" r="45" fill="none" stroke={color} strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${pintado.toFixed(1)} ${PERIMETRO.toFixed(1)}`}
          style={{ filter: `drop-shadow(0 0 6px ${color}88)` }}
        />
      </svg>
      <div className="val">
        <b>{Math.round(valor * 100)}%</b>
        <span>confianza</span>
      </div>
    </div>
  );
}

/** La categoria como insignia con degradado, que es como la muestra el
 *  prototipo. En texto plano se pierde el color, que es lo que hace que se
 *  reconozca la categoria de un vistazo. */
export function Insignia({ categoria }: { categoria: Categoria }) {
  const [a, b] = COLORES[categoria] ?? ["#6d5efc", "#8b7dff"];
  return (
    <span
      className="cat-badge"
      style={{ background: `linear-gradient(135deg,${a},${b})`, boxShadow: `0 10px 30px ${a}55` }}
    >
      <span className="dot" /> {categoria}
    </span>
  );
}

/** Botón «Ver en español». Solo se muestra donde hace falta; quien decide
 *  eso es la vista, que sabe en qué idioma se preguntó. */
export function BotonTraducir({
  traducido, ocupado, alPulsar,
}: {
  traducido: boolean;
  ocupado: boolean;
  alPulsar: () => void;
}) {
  return (
    <button className="btn-trad" onClick={alPulsar} disabled={ocupado}>
      {ocupado ? "traduciendo…" : traducido ? "Ver el original" : "Ver en español"}
    </button>
  );
}
