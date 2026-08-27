/// <reference types="vite/client" />

/** La URL de la API se puede fijar por entorno al construir, para poder
 *  apuntar el mismo build a otra instancia sin tocar el codigo. */
interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
