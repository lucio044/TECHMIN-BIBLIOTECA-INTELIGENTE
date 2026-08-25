from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_contenido_responde_200_con_entrada_valida():
    respuesta = client.post("/contenido", json={
        "titulo": "Introduccion a Spring Boot",
        "texto": "Como crear controladores REST con Java"
    })
    assert respuesta.status_code == 200


def test_contenido_devuelve_los_tres_campos_del_contrato():
    respuesta = client.post("/contenido", json={
        "titulo": "Introduccion a Spring Boot",
        "texto": "Como crear controladores REST con Java"
    })
    cuerpo = respuesta.json()
    assert "categoria" in cuerpo
    assert "probabilidad" in cuerpo
    assert "informacion_adicional" in cuerpo


def test_categoria_es_una_de_las_8_oficiales():
    categorias_validas = {
        "Backend", "Bases de Datos", "Ciencia de Datos", "DevOps / Cloud",
        "Frontend", "Mobile", "Programación General", "Seguridad",
    }
    respuesta = client.post("/contenido", json={
        "titulo": "Tutorial de React",
        "texto": "Como manejar el estado con hooks en una aplicacion web"
    })
    categoria = respuesta.json()["categoria"]
    assert categoria in categorias_validas


def test_probabilidad_esta_entre_0_y_1():
    respuesta = client.post("/contenido", json={
        "titulo": "Guia de Docker",
        "texto": "Como desplegar contenedores con Kubernetes"
    })
    probabilidad = respuesta.json()["probabilidad"]
    assert 0 <= probabilidad <= 1


def test_informacion_adicional_es_una_lista_no_vacia():
    respuesta = client.post("/contenido", json={
        "titulo": "Seguridad informatica",
        "texto": "Proteccion de redes contra malware y ataques"
    })
    palabras = respuesta.json()["informacion_adicional"]
    assert isinstance(palabras, list)
    assert len(palabras) > 0


def test_titulo_vacio_devuelve_error_422():
    respuesta = client.post("/contenido", json={
        "titulo": "",
        "texto": "Algun texto valido"
    })
    assert respuesta.status_code == 422


def test_texto_solo_con_espacios_devuelve_error_422():
    respuesta = client.post("/contenido", json={
        "titulo": "Titulo valido",
        "texto": "     "
    })
    assert respuesta.status_code == 422


def test_falta_el_campo_texto_devuelve_error_422():
    respuesta = client.post("/contenido", json={
        "titulo": "Solo titulo, sin texto"
    })
    assert respuesta.status_code == 422