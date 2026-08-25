"""
Pipeline de NLP para el clasificador de contenido técnico (TechMind) —
modelo v2, entrenado con dataset bilingüe (inglés + español).

Módulos:
    exceptions        — jerarquía de errores propios del dominio.
    config             — rutas y umbrales centralizados.
    cleaning           — limpieza de texto (réplica exacta de la usada
                          para entrenar el modelo).
    keywords           — extracción de palabras clave por pesos TF-IDF.
    model_repository   — carga y caché del Pipeline serializado (.joblib).
    schemas            — contrato de datos tipado del resultado.
    classifier         — orquesta limpieza + predicción + palabras clave.
    inference          — fachada simple para la API: procesar_contenido()
                          y precargar_modelo().
"""
