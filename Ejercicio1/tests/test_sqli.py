# Pruebas unitarias del Ejercicio 1 (SQL Injection).
# Prueban directamente buscar_funciones(). Como esperan el comportamiento ya
# arreglado, en main (vulnerable) fallan y en practico-2 pasan.
#
#   pip install -r requirements-test.txt
#   pytest Ejercicio1/tests -v

import os
import sys
import sqlite3
import tempfile
import importlib.util

import pytest

# Ejercicio1/app.py y Ejercicio2/app.py se llaman igual, asi que si dejo el
# import normal pytest se queda con el primero que cargo. Lo cargo a mano con
# otro nombre para que no se pisen.
EJ1_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, EJ1_DIR)  # lo necesita el "from config import Config" de app.py
_spec = importlib.util.spec_from_file_location("ej1_app_mod", os.path.join(EJ1_DIR, "app.py"))
ej1_app = importlib.util.module_from_spec(_spec)
sys.modules["ej1_app_mod"] = ej1_app  # Flask ubica templates/ con esto
_spec.loader.exec_module(ej1_app)


# Ninguna de estas peliculas contiene el texto de los payloads, asi que buscar
# un payload "tal cual" tiene que dar cero resultados.
PELICULAS = [
    ("Dune: Parte Dos", "Ciencia Ficcion", "Denis Villeneuve"),
    ("Oppenheimer", "Drama", "Christopher Nolan"),
    ("Wonka", "Fantasia", "Paul King"),
]


def _seed(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE peliculas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            genero TEXT NOT NULL,
            director TEXT NOT NULL
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
    cur.executemany(
        "INSERT INTO peliculas (nombre, genero, director) VALUES (?, ?, ?)",
        PELICULAS,
    )
    cur.executemany(
        "INSERT INTO funciones (pelicula_id, fecha_hora, asientos_totales, asientos_ocupados) "
        "VALUES (?, ?, ?, ?)",
        [(i + 1, "2026-07-13 14:30:00", 100, 10) for i in range(len(PELICULAS))],
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def contexto():
    # Base temporal para no tocar la cine.db real.
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _seed(db_path)
    ej1_app.app.config["DATABASE"] = db_path
    with ej1_app.app.app_context():
        yield
    os.remove(db_path)


def test_tautologia_no_expone_todas_las_filas(contexto):
    # El ' OR '1'='1 clasico. Si la consulta esta parametrizada se busca ese
    # texto y no coincide con nada; si se concatena, el OR devuelve todo.
    assert len(ej1_app.buscar_funciones("Dune")) >= 1  # hay datos cargados

    filas = ej1_app.buscar_funciones("' OR '1'='1")
    assert len(filas) == 0, "La tautologia devolvio filas: el valor se esta metiendo en el SQL."


def test_union_select_no_se_ejecuta(contexto):
    # Un UNION inyectado tiene que quedar como texto de busqueda, no ejecutarse.
    assert len(ej1_app.buscar_funciones("Dune")) >= 1

    filas = ej1_app.buscar_funciones("zzz' UNION SELECT name, sql, 1 FROM sqlite_master -- ")
    assert len(filas) == 0


def test_order_by_no_es_inyectable(contexto):
    # sort_by/sort_dir no deben concatenarse. Con un valor raro en sort_dir el
    # codigo vulnerable arma un SQL invalido y revienta; el mitigado lo ignora.
    try:
        filas = ej1_app.buscar_funciones("Dune", sort_by="nombre", sort_dir="ASC; DROP TABLE peliculas; --")
    except sqlite3.Error as e:
        pytest.fail(f"La direccion de orden se inyecto en el SQL: {e}")

    assert len(filas) >= 1
