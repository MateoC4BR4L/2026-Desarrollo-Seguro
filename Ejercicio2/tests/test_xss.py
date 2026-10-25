# Pruebas unitarias del Ejercicio 2 (XSS almacenado).
# El XSS estaba en edit.html, que mostraba la descripcion con "| safe" y asi
# desactivaba el escape de Jinja2. Guardo una descripcion con codigo y reviso
# que al mostrarla quede escapada.
#
#   pip install -r requirements-test.txt
#   pytest Ejercicio2/tests -v

import os
import sys
import sqlite3
import tempfile
import importlib.util

import pytest

# Mismo tema que en el Ejercicio 1: app.py se llama igual en los dos ejercicios,
# lo cargo con nombre propio para que no choquen dentro de pytest.
EJ2_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, EJ2_DIR)
_spec = importlib.util.spec_from_file_location("ej2_app_mod", os.path.join(EJ2_DIR, "app.py"))
ej2_app = importlib.util.module_from_spec(_spec)
sys.modules["ej2_app_mod"] = ej2_app
_spec.loader.exec_module(ej2_app)


def _seed(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE peliculas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            genero TEXT NOT NULL,
            director TEXT NOT NULL,
            descripcion TEXT
        );
        CREATE TABLE funciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pelicula_id INTEGER NOT NULL,
            fecha_hora TEXT NOT NULL,
            asientos_totales INTEGER NOT NULL DEFAULT 100,
            asientos_ocupados INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    cur.execute(
        "INSERT INTO peliculas (nombre, genero, director, descripcion) VALUES (?, ?, ?, ?)",
        ("Dune: Parte Dos", "Ciencia Ficcion", "Denis Villeneuve", "Descripcion inicial"),
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _seed(db_path)
    ej2_app.app.config["DATABASE"] = db_path
    ej2_app.app.config["TESTING"] = True
    with ej2_app.app.test_client() as c:
        yield c
    os.remove(db_path)


def _guardar_descripcion(client, descripcion):
    # Guarda la descripcion en la pelicula 1 y devuelve el HTML del form de edicion.
    client.post(
        "/edit/1",
        data={
            "nombre": "Dune: Parte Dos",
            "genero": "Ciencia Ficcion",
            "director": "Denis Villeneuve",
            "descripcion": descripcion,
        },
    )
    return client.get("/edit/1").get_data(as_text=True)


def test_script_tag_se_escapa(client):
    payload = "<script>alert('xss')</script>"
    html = _guardar_descripcion(client, payload)

    assert payload not in html, "El <script> se mostro sin escapar."
    assert "&lt;script&gt;" in html


def test_img_onerror_se_escapa(client):
    payload = "<img src=x onerror=alert(1)>"
    html = _guardar_descripcion(client, payload)

    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;img" in html
