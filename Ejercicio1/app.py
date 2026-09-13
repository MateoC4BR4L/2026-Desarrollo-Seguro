from flask import Flask, render_template, request, g
import sqlite3
from config import Config

app = Flask(__name__)
app.config.from_object(Config)


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# --- MITIGACIÓN SQLi ---
# Whitelist de columnas y direcciones permitidas para ORDER BY
SORT_BY_ALLOWED  = {'nombre': 'peliculas.nombre', 'fecha': 'funciones.fecha_hora'}
SORT_DIR_ALLOWED = {'ASC', 'DESC'}


def buscar_funciones(query, sort_by='nombre', sort_dir='ASC'):
    db = get_db()

    # Whitelist para sort_by y sort_dir: evita inyección en ORDER BY
    col       = SORT_BY_ALLOWED.get(sort_by, 'peliculas.nombre')
    direction = sort_dir if sort_dir in SORT_DIR_ALLOWED else 'ASC'

    # Consulta parametrizada: el valor de query nunca forma parte del SQL
    sql = (
        f"SELECT peliculas.nombre as pelicula, funciones.fecha_hora, "
        f"(funciones.asientos_totales - funciones.asientos_ocupados) as disponibles "
        f"FROM funciones "
        f"JOIN peliculas ON funciones.pelicula_id = peliculas.id "
        f"WHERE peliculas.nombre LIKE ? "
        f"ORDER BY {col} {direction}"
    )
    return db.execute(sql, (f'%{query}%',)).fetchall()


@app.route('/')
def index():
    query = request.args.get('buscar', '')
    sort_by = request.args.get('ordenar_por', 'nombre')
    sort_dir = request.args.get('sentido', 'ASC')
    resultados = []
    if query:
        resultados = buscar_funciones(query, sort_by, sort_dir)
    return render_template('index.html',
                           resultados=resultados,
                           query=query,
                           sort_by=sort_by,
                           sort_dir=sort_dir)


if __name__ == '__main__':
    import os
    host  = os.environ.get('FLASK_HOST', '0.0.0.0')
    # Mitigación: debug desactivado por defecto (antes era 'true')
    debug = os.environ.get('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
    app.run(debug=debug, host=host)
