"""
Script de prueba manual (no es parte de la suite de pytest).
Envia una tanda de textos en español e ingles a POST /contenido,
compara la categoria predicha contra la esperada y guarda los
resultados en un CSV, junto con un resumen de aciertos y confusiones.

Requiere que el servidor este corriendo en http://localhost:8000
(ej: uvicorn app.main:app --port 8000).
"""
import csv
import json
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

URL_ENDPOINT = "http://localhost:8000/contenido"
CSV_SALIDA = Path(__file__).resolve().parent / "resultados_prueba_manual.csv"

CASOS = [
    {"idioma": "es", "categoria_esperada": "Backend",
     "titulo": "Diseño de APIs REST con Node.js",
     "texto": "Como construir endpoints, middlewares y manejo de errores en un servidor Express para exponer servicios backend."},
    {"idioma": "en", "categoria_esperada": "Backend",
     "titulo": "Building REST APIs with Spring Boot",
     "texto": "How to design controllers, service layers and dependency injection for a scalable backend application in Java."},

    {"idioma": "es", "categoria_esperada": "Bases de Datos",
     "titulo": "Optimizacion de consultas SQL",
     "texto": "Uso de indices, normalizacion y claves foraneas para mejorar el rendimiento de bases de datos relacionales en PostgreSQL."},
    {"idioma": "en", "categoria_esperada": "Bases de Datos",
     "titulo": "Introduction to NoSQL Databases",
     "texto": "Comparing document stores like MongoDB with relational databases, covering schema design and indexing strategies."},

    {"idioma": "es", "categoria_esperada": "Ciencia de Datos",
     "titulo": "Analisis exploratorio de datos con pandas",
     "texto": "Como limpiar, transformar y visualizar conjuntos de datos usando Python para encontrar patrones estadisticos."},
    {"idioma": "en", "categoria_esperada": "Ciencia de Datos",
     "titulo": "Machine Learning Model Evaluation",
     "texto": "Understanding precision, recall, cross validation and feature engineering techniques for predictive data science models."},

    {"idioma": "es", "categoria_esperada": "DevOps / Cloud",
     "titulo": "Automatizacion de despliegues con Docker y Kubernetes",
     "texto": "Como configurar pipelines de integracion continua para desplegar contenedores en la nube de forma automatica."},
    {"idioma": "en", "categoria_esperada": "DevOps / Cloud",
     "titulo": "AWS Infrastructure as Code with Terraform",
     "texto": "Managing cloud resources, auto scaling groups and CI/CD pipelines for reliable DevOps automation."},

    {"idioma": "es", "categoria_esperada": "Frontend",
     "titulo": "Manejo de estado en React con hooks",
     "texto": "Como usar useState y useEffect para construir interfaces de usuario interactivas y componentes reutilizables."},
    {"idioma": "en", "categoria_esperada": "Frontend",
     "titulo": "CSS Grid and Flexbox Layouts",
     "texto": "Building responsive user interfaces with modern styling techniques for web pages and JavaScript frameworks."},

    {"idioma": "es", "categoria_esperada": "Mobile",
     "titulo": "Desarrollo de aplicaciones moviles con Flutter",
     "texto": "Como crear interfaces nativas para Android e iOS usando widgets y gestion de estado en una sola base de codigo."},
    {"idioma": "en", "categoria_esperada": "Mobile",
     "titulo": "Building Native iOS Apps with Swift",
     "texto": "An introduction to UIKit, view controllers and mobile app lifecycle management for iPhone applications."},

    {"idioma": "es", "categoria_esperada": "Programación General",
     "titulo": "Fundamentos de algoritmos y estructuras de datos",
     "texto": "Conceptos basicos de programacion como recursividad, complejidad algoritmica y buenas practicas de codigo limpio."},
    {"idioma": "en", "categoria_esperada": "Programación General",
     "titulo": "Introduction to Object Oriented Programming",
     "texto": "Understanding classes, inheritance, polymorphism and design patterns as fundamental programming concepts."},

    {"idioma": "es", "categoria_esperada": "Seguridad",
     "titulo": "Prevencion de ataques de inyeccion SQL",
     "texto": "Como proteger aplicaciones web contra vulnerabilidades comunes como XSS, CSRF y fugas de informacion sensible."},
    {"idioma": "en", "categoria_esperada": "Seguridad",
     "titulo": "Network Security and Penetration Testing",
     "texto": "Best practices for firewalls, encryption, vulnerability scanning and ethical hacking to secure systems."},
]


def clasificar(titulo: str, texto: str) -> dict:
    payload = json.dumps({"titulo": titulo, "texto": texto}).encode("utf-8")
    peticion = urllib.request.Request(
        URL_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(peticion, timeout=10) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def ejecutar_pruebas() -> list[dict]:
    resultados = []
    for caso in CASOS:
        cuerpo = clasificar(caso["titulo"], caso["texto"])
        categoria_predicha = cuerpo["categoria"]
        acierto = categoria_predicha == caso["categoria_esperada"]
        resultados.append({
            "idioma": caso["idioma"],
            "categoria_esperada": caso["categoria_esperada"],
            "categoria_predicha": categoria_predicha,
            "probabilidad": cuerpo["probabilidad"],
            "acierto": acierto,
        })
    return resultados


def guardar_csv(resultados: list[dict]) -> None:
    with open(CSV_SALIDA, "w", newline="", encoding="utf-8") as archivo:
        columnas = ["idioma", "categoria_esperada", "categoria_predicha", "probabilidad", "acierto"]
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(resultados)


def imprimir_resumen(resultados: list[dict]) -> None:
    total = len(resultados)
    aciertos = [r for r in resultados if r["acierto"]]
    print(f"\nAciertos totales: {len(aciertos)}/{total} ({len(aciertos) / total:.1%})")

    for idioma in sorted({r["idioma"] for r in resultados}):
        del_idioma = [r for r in resultados if r["idioma"] == idioma]
        aciertos_idioma = [r for r in del_idioma if r["acierto"]]
        print(f"  {idioma}: {len(aciertos_idioma)}/{len(del_idioma)} ({len(aciertos_idioma) / len(del_idioma):.1%})")

    confusiones = Counter(
        (r["categoria_esperada"], r["categoria_predicha"])
        for r in resultados if not r["acierto"]
    )
    print("\nPares de categorias que mas se confunden:")
    if not confusiones:
        print("  Ninguno — todas las predicciones acertaron.")
    else:
        for (esperada, predicha), veces in confusiones.most_common():
            print(f"  {esperada} -> {predicha}: {veces} vez/veces")


if __name__ == "__main__":
    try:
        resultados = ejecutar_pruebas()
    except urllib.error.URLError as error:
        raise SystemExit(
            f"No se pudo conectar a {URL_ENDPOINT}. "
            f"Asegurate de tener el servidor corriendo (uvicorn app.main:app --port 8000). Detalle: {error}"
        )

    guardar_csv(resultados)
    print(f"Resultados guardados en {CSV_SALIDA}")
    imprimir_resumen(resultados)
