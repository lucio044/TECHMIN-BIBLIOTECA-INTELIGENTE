import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El sitio se sirve desde la raiz del dominio, no desde un subdirectorio.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", sourcemap: false },
  server: { port: 5173 },
});
