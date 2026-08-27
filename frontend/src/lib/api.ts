/** Todas las llamadas a la API, en un solo sitio.
 *
 *  Se apunta a /v1 y no a las rutas sueltas: esas siguen respondiendo por
 *  compatibilidad pero vienen con la cabecera Deprecation, y el primero que
 *  tiene que respetar el versionado es el propio frontend. */

import type {
  ContenidoEntrada, ContenidoSalida, RespuestaSemantica, RespuestaBusqueda,
  RespuestaChat, EstadoTraductor, RespuestaTraduccion, InfoModelo, Metricas,
  ModeloPropio,
} from "../types";

const enLocal = ["localhost", "127.0.0.1", ""].includes(location.hostname);

export const BASE = import.meta.env.VITE_API_URL
  ?? (enLocal ? "http://127.0.0.1:8000" : "https://15-229-103-244.sslip.io");

export const API = `${BASE}/v1`;

/** Error con el cuerpo ya leido, para que quien lo atrape no tenga que
 *  volver a tocar la respuesta --que ya se consumio. */
export class ErrorApi extends Error {
  constructor(public estado: number, mensaje: string) {
    super(mensaje);
    this.name = "ErrorApi";
  }
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  const r = await fetch(API + ruta, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });

  // El cuerpo se lee una sola vez y sirve para los dos caminos: en el
  // prototipo esto estaba duplicado y un `r.ok` sin comprobar dejaba pasar
  // el detalle del error como si fuera un resultado.
  const texto = await r.text();
  let cuerpo: unknown = null;
  try { cuerpo = texto ? JSON.parse(texto) : null; } catch { /* no era JSON */ }

  if (!r.ok) {
    const detalle =
      (cuerpo as { detail?: unknown })?.detail;
    throw new ErrorApi(
      r.status,
      typeof detalle === "string" ? detalle : `La API respondio ${r.status}`,
    );
  }
  return cuerpo as T;
}

// --- lo que pide el enunciado ---------------------------------------------

export const clasificar = (entrada: ContenidoEntrada) =>
  pedir<ContenidoSalida>("/contenido", {
    method: "POST",
    body: JSON.stringify(entrada),
  });

export const categorias = () => pedir<{ categorias: string[] }>("/categorias");

// --- busqueda --------------------------------------------------------------

export const buscarSemantica = (consulta: string, cantidad = 6) =>
  pedir<RespuestaSemantica>(
    `/semantica?consulta=${encodeURIComponent(consulta)}&cantidad=${cantidad}`,
  );

export const buscarTermino = (termino: string, cantidad = 10) =>
  pedir<RespuestaBusqueda>(
    `/buscar?termino=${encodeURIComponent(termino)}&cantidad=${cantidad}`,
  );

export const sugerencias = () =>
  pedir<{ sugerencias: string[] }>("/sugerencias");

// --- asistente -------------------------------------------------------------

export const preguntar = (texto: string) =>
  pedir<RespuestaChat>("/chat", { method: "POST", body: JSON.stringify({ texto }) });

// --- traduccion ------------------------------------------------------------

export const estadoTraductor = () => pedir<EstadoTraductor>("/traducir/estado");

export const traducir = (textos: string[], destino: "es" | "en") =>
  pedir<RespuestaTraduccion>("/traducir", {
    method: "POST",
    body: JSON.stringify({ textos, destino }),
  });

// --- modelo ----------------------------------------------------------------

export const infoModelo = () => pedir<InfoModelo>("/modelo/info");
export const metricas = () => pedir<Metricas>("/metricas");

// --- modelos propios -------------------------------------------------------

export const listarModelos = () => pedir<ModeloPropio[]>("/modelos");

export const borrarModelo = (id: string) =>
  pedir<{ borrado: boolean }>(`/modelos/${encodeURIComponent(id)}`, { method: "DELETE" });

export const clasificarConModelo = (id: string, texto: string) =>
  pedir<{ categoria: string; probabilidad: number }>(
    `/modelos/${encodeURIComponent(id)}/clasificar`,
    { method: "POST", body: JSON.stringify({ texto }) },
  );

/** El entrenamiento manda un CSV, asi que no lleva Content-Type JSON:
 *  el navegador tiene que poner el suyo con el limite del multipart. */
export async function entrenarModelo(archivo: File, nombre: string) {
  const cuerpo = new FormData();
  cuerpo.append("archivo", archivo);
  cuerpo.append("nombre", nombre);

  const r = await fetch(`${API}/modelos`, { method: "POST", body: cuerpo });
  const texto = await r.text();
  let j: unknown = null;
  try { j = texto ? JSON.parse(texto) : null; } catch { /* no era JSON */ }
  if (!r.ok) {
    const d = (j as { detail?: unknown })?.detail;
    throw new ErrorApi(r.status, typeof d === "string" ? d : `La API respondio ${r.status}`);
  }
  return j as ModeloPropio;
}
