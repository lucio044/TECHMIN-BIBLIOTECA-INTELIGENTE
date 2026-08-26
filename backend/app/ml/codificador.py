# -*- coding: utf-8 -*-
"""Codificador de textos a vectores, sobre ONNX Runtime.

Se usa ONNX y no sentence-transformers para no arrastrar torch: son 800 MB
instalados y varios cientos de MB en memoria, que no entran junto al resto
en una instancia de 2 GB.

El modelo es paraphrase-multilingual-MiniLM-L12-v2 cuantizado a uint8: 113
MB en vez de 470, que es lo que permite que esto viva en el servidor.
"""
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

DIMENSIONES = 384
MAX_TOKENS = 128


class Codificador:
    def __init__(self, ruta_modelo: str, ruta_tokenizador: str, hebras: int = 1):
        # Una hebra por defecto, que es lo que corresponde en el servidor:
        # ahi varias peticiones compiten por los mismos nucleos y repartir
        # cada una en varias hebras las hace mas lentas, no mas rapidas.
        # El trabajo de vectorizar el historico si pide todas las que haya.
        opciones = ort.SessionOptions()
        opciones.intra_op_num_threads = hebras
        opciones.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sesion = ort.InferenceSession(ruta_modelo, opciones,
                                           providers=["CPUExecutionProvider"])
        self.entradas = {e.name for e in self.sesion.get_inputs()}

        self.tok = Tokenizer.from_file(ruta_tokenizador)
        self.tok.enable_truncation(max_length=MAX_TOKENS)
        self.tok.enable_padding(length=None)

    def __call__(self, textos, lote: int = 32) -> np.ndarray:
        salida = []
        for i in range(0, len(textos), lote):
            salida.append(self._codificar(textos[i:i + lote]))
        return np.vstack(salida) if salida else np.zeros((0, DIMENSIONES), dtype=np.float32)

    @staticmethod
    def normalizar(texto: str) -> str:
        """Todo a minusculas, de los dos lados.

        El modelo distingue mayusculas: «BASE DE DATOS» quedaba a 0,451 de
        su mejor documento y «base de datos» a 0,705. No es solo el grito,
        tambien la mayuscula normal: «Kubernetes» daba 0,409 y «kubernetes»
        0,677.

        Se normaliza aca adentro y no en quien llama, para que el indice y
        la consulta no puedan tratarse distinto. Si esto viviera en el
        buscador, el dia que alguien agregue otra ruta se olvidaria, y el
        sintoma seria una busqueda que no encuentra nada sin ningun error.
        """
        return str(texto).lower()

    def _codificar(self, textos) -> np.ndarray:
        cods = self.tok.encode_batch([self.normalizar(t) for t in textos])
        ids = np.array([c.ids for c in cods], dtype=np.int64)
        mascara = np.array([c.attention_mask for c in cods], dtype=np.int64)

        alimento = {"input_ids": ids, "attention_mask": mascara}
        if "token_type_ids" in self.entradas:
            alimento["token_type_ids"] = np.zeros_like(ids)

        estados = self.sesion.run(None, alimento)[0]

        # Promedio de los tokens reales, ignorando el relleno. Es la
        # operacion que sentence-transformers llama mean pooling y la que
        # este modelo espera: sin ella los vectores no son comparables.
        m = mascara[..., None].astype(np.float32)
        vect = (estados * m).sum(axis=1) / np.clip(m.sum(axis=1), 1e-9, None)

        # Normalizados, para que el producto punto sea el coseno.
        normas = np.linalg.norm(vect, axis=1, keepdims=True)
        return (vect / np.clip(normas, 1e-9, None)).astype(np.float32)
