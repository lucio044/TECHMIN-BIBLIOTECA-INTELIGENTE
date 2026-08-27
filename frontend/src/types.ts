/** Las formas que devuelve la API, escritas una sola vez.
 *
 *  Estan tomadas del esquema OpenAPI que publica el backend. Si la API
 *  cambia un campo, el compilador senala todos los sitios que lo usan, que
 *  es justamente lo que el prototipo de un solo archivo no podia hacer. */

export type Categoria =
  | "Backend"
  | "Frontend"
  | "Mobile"
  | "Ciencia de Datos"
  | "Bases de Datos"
  | "DevOps / Cloud"
  | "Seguridad"
  | "Programación General";

export interface CategoriaRanking {
  categoria: Categoria;
  probabilidad: number;
}

/** Tal como lo devuelve POST /v1/contenido. El campo se llama `similitud`,
 *  no `parecido` --ese es el de la busqueda semantica-- y no hay `id`. */
export interface ContenidoRelacionado {
  titulo: string;
  extracto: string;
  categoria: Categoria;
  similitud: number;
}

/** Lo que pide el enunciado: POST /contenido con titulo y texto. */
export interface ContenidoEntrada {
  titulo: string;
  texto: string;
}

export interface ContenidoSalida {
  categoria: Categoria;
  probabilidad: number;
  informacion_adicional: string[];
  ranking_categorias: CategoriaRanking[];
  contenidos_relacionados: ContenidoRelacionado[];
}

export interface ResultadoSemantico {
  id: number;
  titulo: string;
  extracto: string;
  categoria: Categoria;
  parecido: number;
}

export interface RespuestaSemantica {
  consulta: string;
  total: number;
  documentos_comparados: number;
  resultados: ResultadoSemantico[];
}

export interface ResultadoBusqueda {
  id: number;
  titulo: string;
  extracto: string;
  categoria: Categoria;
}

export interface RespuestaBusqueda {
  termino: string;
  total: number;
  resultados: ResultadoBusqueda[];
}

export interface Fragmento {
  texto: string;
  parte?: number;
}

export interface TerminoDecisivo {
  termino: string;
  aporte: number;
  sostiene?: boolean;
}

export interface Historico {
  fuente: string;
  categoria: Categoria;
  parecido: number;
  documentos_consultados: number;
  fragmentos: Fragmento[];
}

/** Un turno del historial, tal como lo espera POST /v1/chat. */
export interface MensajeChat {
  rol: "user" | "assistant";
  contenido: string;
}

export interface RespuestaChat {
  respuesta: string;
  tipo: "explicacion" | "historico" | "sin_informacion" | string;
  categoria?: Categoria;
  probabilidad?: number;
  fuente?: string;
  terminos_decisivos?: TerminoDecisivo[];
  del_historico?: Historico | null;
}

export interface EstadoTraductor {
  es_en: boolean;
  en_es: boolean;
  cargados: string[];
}

export interface RespuestaTraduccion {
  destino: "es" | "en";
  traducciones: string[];
  ya_estaban_en_destino: number;
}

export interface InfoModelo {
  algoritmo: string;
  cantidad_categorias: number;
  categorias: Categoria[];
  fecha_modificacion: string;
}

export interface MetricasPorCategoria {
  precision: number;
  recall: number;
  f1: number;
  soporte: number;
}

export interface Metricas {
  modelo: {
    algoritmo: string;
    categorias: number;
    vocabulario: number;
    ngramas: [number, number];
    regularizacion_C: number;
    pesos_balanceados: boolean;
  };
  rendimiento: {
    f1_macro: number;
    accuracy: number;
    validacion_cruzada: { media: number; desvio: number };
    linea_base_f1_macro: number;
    textos_de_prueba: number;
    por_categoria: Record<string, MetricasPorCategoria>;
  };
}

/** Tal como lo devuelve GET /v1/modelos. Los nombres salen del esquema
 *  OpenAPI, no de la memoria: escribir `exactitud` en lugar de `f1_macro`
 *  no rompe nada al compilar, simplemente deja el dato sin mostrar. */
export interface ModeloPropio {
  id: string;
  nombre: string;
  categorias: string[];
  ejemplos: number;
  distribucion: Record<string, number>;
  f1_macro: number;
  entrenado: string;
}

/** Un termino frecuente del historico, tal como lo devuelve
 *  GET /v1/sugerencias. La lista viene bajo la clave `terminos`. */
export interface TerminoSugerido {
  termino: string;
  categoria: Categoria;
  documentos: number;
}

export interface RespuestaSugerencias {
  generado_por: string;
  total: number;
  terminos: TerminoSugerido[];
}

/** Lo guardado en el navegador, que no viene de la API. */
export interface EntradaBiblioteca {
  id: string;
  titulo: string;
  texto: string;
  categoria: Categoria;
  probabilidad: number;
  palabras: string[];
  fecha: string;
}
