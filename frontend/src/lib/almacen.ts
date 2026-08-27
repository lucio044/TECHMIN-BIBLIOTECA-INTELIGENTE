/** La biblioteca personal, guardada en el navegador.
 *
 *  No va a la base: son las clasificaciones que hizo esta persona en este
 *  equipo. La API tiene su propio endpoint de biblioteca para lo que si se
 *  persiste del lado del servidor. */

import type { EntradaBiblioteca } from "../types";

const CLAVE = "techmind.biblioteca.v1";
const TOPE = 300;

export function cargar(): EntradaBiblioteca[] {
  try {
    const crudo = localStorage.getItem(CLAVE);
    if (!crudo) return [];
    const datos: unknown = JSON.parse(crudo);
    return Array.isArray(datos) ? (datos as EntradaBiblioteca[]) : [];
  } catch {
    // Un JSON corrupto no puede dejar la pagina en blanco: se empieza de cero.
    return [];
  }
}

/** Devuelve si se pudo guardar. El prototipo se tragaba el fallo de cuota
 *  en silencio y la persona creia tener guardado algo que no estaba. */
export function guardar(entradas: EntradaBiblioteca[]): boolean {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(entradas.slice(0, TOPE)));
    return true;
  } catch {
    return false;
  }
}

export function agregar(
  entradas: EntradaBiblioteca[],
  nueva: Omit<EntradaBiblioteca, "id" | "fecha">,
): EntradaBiblioteca[] {
  const entrada: EntradaBiblioteca = {
    ...nueva,
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    fecha: new Date().toISOString(),
  };
  return [entrada, ...entradas].slice(0, TOPE);
}

export const quitar = (entradas: EntradaBiblioteca[], id: string) =>
  entradas.filter((e) => e.id !== id);
