from fastapi import HTTPException, status
from app.schemas.contenido import ContenidoEntrada, ContenidoSalida, CategoriaRanking, ContenidoRelacionado
from app.ml.loader import cargar_modelo
from app.ml.preprocesamiento import preparar_entrada_modelo
# El extractor vive en el paquete techmind-nlp y no aca: era el mismo
# archivo copiado en dos sitios, con el riesgo de que un arreglo en uno
# no llegara al otro. Se instala con `pip install -e ./nlp`.
from techmind_nlp.keywords import ExtractorPalabrasClaveTfidf
from app.ml.recomendador import cargar_recomendador
from app.ml import traductor

modelo = cargar_modelo()
_extractor_palabras_clave = None

TOP_K_PALABRAS_CLAVE = 4
UMBRAL_OTRAS_CATEGORIAS = 0.05
TOPE_OTRAS_CATEGORIAS = 4
UMBRAL_CONFIANZA_RELACIONADOS = 0.5


def _obtener_extractor(pipeline):
    global _extractor_palabras_clave
    if _extractor_palabras_clave is None:
        vectorizador = pipeline.named_steps["tfidf"]
        clasificador = pipeline.named_steps.get("clf")
        _extractor_palabras_clave = ExtractorPalabrasClaveTfidf(vectorizador, clasificador)
    return _extractor_palabras_clave


def clasificar_contenido(entrada: ContenidoEntrada) -> ContenidoSalida:
    if modelo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El modelo de clasificación aún no está disponible. Intenta más tarde.",
        )

    # Con `traducir`, el texto pasa al ingles antes de clasificar. El
    # modelo aprendio de un corpus 95,9% en ese idioma, asi que un texto en
    # castellano le llega en desventaja: medido sobre veinte textos
    # coloquiales nuevos, el acierto sube de 6 a 11 de 20.
    #
    # Los relacionados se buscan igual con el texto ORIGINAL: la matriz
    # tiene documentos en los dos idiomas y traducir ahi no aporta, mientras
    # que perder el texto original si haria que un usuario en español no
    # encuentre nunca material en español.
    texto_original = preparar_entrada_modelo(entrada.titulo, entrada.texto)
    texto_preparado = texto_original

    if getattr(entrada, "traducir", False):
        traducido = traductor.traducir(f"{entrada.titulo}. {entrada.texto}", "en")
        if traducido:
            texto_preparado = preparar_entrada_modelo("", traducido)

    proba = modelo.predict_proba([texto_preparado])[0]
    idx = proba.argmax()
    categoria_ganadora = modelo.classes_[idx]
    probabilidad_ganadora = float(proba[idx])

    palabras_clave = _obtener_extractor(modelo).extraer(
        texto_preparado, TOP_K_PALABRAS_CLAVE, categoria_ganadora
    )

    orden_ranking = proba.argsort()[::-1]
    ranking_categorias = [
        CategoriaRanking(
            categoria=modelo.classes_[i],
            probabilidad=round(float(proba[i]), 2),
        )
        for i in orden_ranking[1:]
        if proba[i] >= UMBRAL_OTRAS_CATEGORIAS
    ][:TOPE_OTRAS_CATEGORIAS]

     # Filtro de confianza: evita relacionados falsos con texto ambiguo o no tecnico.
    contenidos_relacionados = []
    if probabilidad_ganadora >= UMBRAL_CONFIANZA_RELACIONADOS:
        recomendador = cargar_recomendador()
        if recomendador is not None:
            # Se piden mas candidatos de los que se van a mostrar y despues
            # se reordenan poniendo primero los de la categoria predicha.
            #
            # El clasificador y el recomendador miran el texto en dos espacios
            # vectoriales distintos --60.000 terminos contra 20.000-- asi que
            # no siempre coinciden: un texto de Jetpack Compose se clasifica
            # como Mobile con total seguridad y el vecino mas cercano cae en
            # DevOps / Cloud. Ya sabemos la categoria, conviene usarla.
            #
            # No se filtra, se reordena: si la categoria tiene pocos documentos
            # parecidos, los del resto siguen estando y la seccion no queda
            # vacia. Dentro de cada grupo se respeta el orden por similitud.
            relacionados_raw = recomendador.recomendar(texto_original, top_n=12)
            del_tema = [r for r in relacionados_raw if r["categoria"] == categoria_ganadora]
            del_resto = [r for r in relacionados_raw if r["categoria"] != categoria_ganadora]
            contenidos_relacionados = [
                ContenidoRelacionado(**r) for r in (del_tema + del_resto)[:3]
            ]

    return ContenidoSalida(
        categoria=categoria_ganadora,
        probabilidad=round(probabilidad_ganadora, 2),
        informacion_adicional=palabras_clave,
        ranking_categorias=ranking_categorias,
        contenidos_relacionados=contenidos_relacionados,
    )