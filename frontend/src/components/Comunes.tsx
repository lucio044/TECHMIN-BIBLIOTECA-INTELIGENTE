/** Piezas que usan varias vistas. */

import type { Categoria } from "../types";

export const COLORES: Record<string, [string, string]> = {
  "Backend": ["#6d5efc", "#8b7dff"],
  "Frontend": ["#23d5c8", "#5ae5da"],
  "Mobile": ["#ff8f5e", "#ffab85"],
  "Ciencia de Datos": ["#f45d9c", "#ff85b8"],
  "Bases de Datos": ["#ffc857", "#ffd98a"],
  "DevOps / Cloud": ["#5eb0ff", "#8ac8ff"],
  "Seguridad": ["#ff6b6b", "#ff9a9a"],
  "Programación General": ["#a78bfa", "#c4b0ff"],
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

/** El anillo de confianza. El trazo se dibuja con dasharray sobre una
 *  circunferencia de radio 52, que son 326,7 de perimetro. */
export function Anillo({ valor, categoria }: { valor: number; categoria: Categoria }) {
  const PERIMETRO = 2 * Math.PI * 52;
  const [a, b] = COLORES[categoria] ?? ["#6d5efc", "#8b7dff"];
  const id = `grad-${categoria.replace(/[^a-z]/gi, "")}`;

  return (
    <div className="ring">
      <svg viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor={a} />
            <stop offset="1" stopColor={b} />
          </linearGradient>
        </defs>
        <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="9" />
        <circle
          cx="60" cy="60" r="52" fill="none" stroke={`url(#${id})`} strokeWidth="9"
          strokeLinecap="round" transform="rotate(-90 60 60)"
          strokeDasharray={`${(valor * PERIMETRO).toFixed(1)} ${PERIMETRO.toFixed(1)}`}
        />
      </svg>
      <div className="val">
        <b>{Math.round(valor * 100)}%</b>
        <span>confianza</span>
      </div>
    </div>
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
