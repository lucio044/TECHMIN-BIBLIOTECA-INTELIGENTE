import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// GitHub Pages sirve el sitio bajo /TECHMIND-BIBLIOTECA-INTELIGENTE/, no en
// la raiz del dominio. Sin este `base` los assets se piden a /assets/... y
// dan 404: la pagina carga en blanco sin decir por que.
export default defineConfig({
  base: "/TECHMIND-BIBLIOTECA-INTELIGENTE/",
  plugins: [react()],
  build: { outDir: "dist", sourcemap: false },
  server: { port: 5173 },
});
