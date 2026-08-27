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

export interface ContenidoRelacionado {
  id?: number;
  titulo: string;
  categoria: Categoria;
  parecido?: number;
  extracto?: string;
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

export interface ModeloPropio {
  id: string;
  nombre: string;
  categorias: string[];
  ejemplos: number;
  exactitud?: number;
  creado?: string;
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
