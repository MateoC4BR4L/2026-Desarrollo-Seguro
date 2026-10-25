# Pruebas de integracion del Ejercicio 3 (carga insegura de archivos).
# Aclaracion: en este repo el Ejercicio 3 es el de file upload (CWE-434), no SSTI.
# Las pruebas corren contra la app levantada en Docker:
#
#   cd Ejercicio3
#   docker compose up -d --build        # queda en http://localhost:8080
#   pytest tests -v
#   docker compose down
#
# La idea: subir archivos que no son imagenes y verificar que la app no los deje
# accesibles. En main pasa cualquier cosa, asi que fallan.

import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080").rstrip("/")
PELICULA_ID = 1
TIMEOUT = 10


@pytest.fixture(scope="session", autouse=True)
def app_disponible():
    try:
        requests.get(BASE_URL + "/", timeout=TIMEOUT)
    except requests.RequestException as e:
        pytest.fail(f"No llego a {BASE_URL}. Levantar la app con docker compose up. Detalle: {e}")


def _subir(nombre, contenido, content_type):
    files = {"afiche": (nombre, contenido, content_type)}
    return requests.post(
        f"{BASE_URL}/upload/{PELICULA_ID}", files=files, timeout=TIMEOUT, allow_redirects=False
    )


def _servido_como_activo(nombre):
    # True si el archivo quedo accesible y ademas se sirve como contenido activo.
    r = requests.get(f"{BASE_URL}/uploads/{nombre}", timeout=TIMEOUT)
    if r.status_code != 200:
        return False
    ctype = r.headers.get("Content-Type", "")
    return "html" in ctype or "svg" in ctype or "javascript" in ctype


def test_rechaza_archivo_html():
    nombre = f"poc_{uuid.uuid4().hex[:8]}.html"
    _subir(nombre, b"<html><body><script>alert('xss-upload')</script></body></html>", "text/html")

    assert not _servido_como_activo(nombre), "El HTML subido quedo servible como pagina activa."


def test_rechaza_archivo_svg():
    # El SVG puede traer JavaScript adentro (onload), tampoco deberia aceptarse.
    nombre = f"poc_{uuid.uuid4().hex[:8]}.svg"
    contenido = b"<svg xmlns='http://www.w3.org/2000/svg' onload=\"alert('xss-svg')\"></svg>"
    _subir(nombre, contenido, "image/svg+xml")

    assert not _servido_como_activo(nombre), "El SVG subido quedo servible como contenido activo."


def test_rechaza_ejecutable_disfrazado():
    # Extension no permitida: no tendria que guardarse con su nombre original.
    nombre = f"shell_{uuid.uuid4().hex[:8]}.jsp"
    _subir(nombre, b"<% out.println(\"pwned\"); %>", "application/octet-stream")

    r = requests.get(f"{BASE_URL}/uploads/{nombre}", timeout=TIMEOUT)
    assert r.status_code == 404, "El .jsp quedo accesible: la app acepto una extension no permitida."
