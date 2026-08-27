import { useCallback, useEffect, useState } from "react";
import Navegacion from "./components/Navegacion";
import Clasificar from "./pages/Clasificar";
import Biblioteca from "./pages/Biblioteca";
import Buscar from "./pages/Buscar";
import Asistente from "./pages/Asistente";
import Propios from "./pages/Propios";
import Dashboard from "./pages/Dashboard";
import * as api from "./lib/api";
import * as almacen from "./lib/almacen";
import type { EntradaBiblioteca } from "./types";

export type Vista =
  | "clasificar" | "biblioteca" | "semantica" | "chat" | "propios" | "modelo";

const VISTAS: Vista[] = [
  "clasificar", "biblioteca", "semantica", "chat", "propios", "modelo",
];

const esVista = (v: string): v is Vista => (VISTAS as string[]).includes(v);

export default function App() {
  const [vista, setVista] = useState<Vista>(() => {
    const h = location.hash.slice(1);
    return esVista(h) ? h : "clasificar";
  });

  const [entradas, setEntradas] = useState<EntradaBiblioteca[]>(() => almacen.cargar());

  // Lo responde /v1/traducir/estado al arrancar. Empieza en false para no
  // ofrecer el botón mientras llega: si el modelo no está instalado, ofrecer
  // un botón que va a fallar es peor que no ofrecerlo.
  const [hayTraductor, setHayTraductor] = useState(false);

  useEffect(() => {
    let vivo = true;
    api.estadoTraductor()
      .then((e) => { if (vivo) setHayTraductor(!!e.en_es); })
      .catch(() => { if (vivo) setHayTraductor(false); });
    return () => { vivo = false; };
  }, []);

  // El botón atrás del navegador vuelve a la vista anterior en vez de sacar
  // al visitante del sitio.
  useEffect(() => {
    const alVolver = () => {
      const h = location.hash.slice(1);
      setVista(esVista(h) ? h : "clasificar");
    };
    addEventListener("popstate", alVolver);
    return () => removeEventListener("popstate", alVolver);
  }, []);

  const navegar = useCallback((v: Vista) => {
    setVista(v);
    history.pushState({ vista: v }, "", `#${v}`);
  }, []);

  const archivar = useCallback(
    (nueva: Omit<EntradaBiblioteca, "id" | "fecha">) => {
      const siguientes = almacen.agregar(entradas, nueva);
      const ok = almacen.guardar(siguientes);
      // Se actualiza igual aunque no se haya podido persistir: lo que se
      // acaba de clasificar tiene que verse en la sesión, y quien llama se
      // encarga de avisar que no quedó guardado.
      setEntradas(siguientes);
      return ok;
    },
    [entradas],
  );

  const quitar = useCallback((id: string) => {
    const siguientes = almacen.quitar(entradas, id);
    almacen.guardar(siguientes);
    setEntradas(siguientes);
  }, [entradas]);

  return (
    <>
      <Navegacion activa={vista} alCambiar={navegar} guardados={entradas.length} />

      <main className="wrap">
        {vista === "clasificar" && <Clasificar alArchivar={archivar} />}
        {vista === "biblioteca" && <Biblioteca entradas={entradas} alQuitar={quitar} />}
        {vista === "semantica" && <Buscar hayTraductor={hayTraductor} />}
        {vista === "chat" && <Asistente hayTraductor={hayTraductor} />}
        {vista === "propios" && <Propios />}
        {vista === "modelo" && <Dashboard />}
      </main>

      <footer className="cierre">
        TechMind AI · Hackathon ONE — Alura Latam + Oracle · Equipo 46 G9 LATAM
      </footer>
    </>
  );
}
