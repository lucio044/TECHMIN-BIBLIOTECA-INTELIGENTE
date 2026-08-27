import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// La pagina se publica en dos sitios y cada uno la sirve desde una ruta
// distinta: Vercel desde la raiz del dominio y GitHub Pages desde
// /TECHMIND-BIBLIOTECA-INTELIGENTE/. Un `base` fijo rompe uno de los dos --
// los assets se piden donde no estan y la pagina carga en blanco sin decir
// por que.
//
// Asi que lo pone quien construye: el flujo de Actions pasa BASE_PATH, y
// Vercel no pasa nada, con lo que vale «/».
export default defineConfig({
  base: process.env.BASE_PATH ?? "/",
  plugins: [react()],
  build: { outDir: "dist", sourcemap: false },
  server: { port: 5173 },
});
