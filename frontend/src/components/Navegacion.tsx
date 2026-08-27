import type { Vista } from "../App";

const PESTANAS: { id: Vista; etiqueta: string; icono: string }[] = [
  { id: "clasificar", etiqueta: "Clasificar", icono: "✍️" },
  { id: "biblioteca", etiqueta: "Biblioteca", icono: "📚" },
  { id: "semantica", etiqueta: "Búsqueda semántica", icono: "🔍" },
  { id: "chat", etiqueta: "Chat", icono: "💬" },
  { id: "propios", etiqueta: "Categorías propias", icono: "🧪" },
  { id: "modelo", etiqueta: "Dashboard", icono: "📊" },
];

export default function Navegacion({
  activa, alCambiar, guardados,
}: {
  activa: Vista;
  alCambiar: (v: Vista) => void;
  guardados: number;
}) {
  return (
    <div className="topbar">
      <span className="logo">Tech<b>Mind</b></span>
      <span className="badge-top"><span className="g" />Biblioteca inteligente</span>
      <nav className="tabs">
        {PESTANAS.map((p) => (
          <button
            key={p.id}
            className={`tab${activa === p.id ? " active" : ""}`}
            onClick={() => alCambiar(p.id)}
            aria-current={activa === p.id ? "page" : undefined}
          >
            {p.icono} {p.etiqueta}
            {p.id === "biblioteca" && <span className="n">{guardados}</span>}
          </button>
        ))}
      </nav>
    </div>
  );
}
