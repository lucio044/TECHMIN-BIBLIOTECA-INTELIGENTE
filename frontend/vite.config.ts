import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// La pagina se publica en Vercel, que la sirve desde la raiz del dominio.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", sourcemap: false },
  server: { port: 5173 },
});
