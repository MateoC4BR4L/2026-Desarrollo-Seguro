# Pruebas de integracion del Ejercicio 4 (SSTI / SpEL injection -> RCE).
# El buscador evaluaba el texto como expresion SpEL con un StandardEvaluationContext
# (que encima exponia System y Runtime), asi que se podia ejecutar codigo con algo
# como T(java.lang.Runtime).getRuntime().exec(...).
#
# Mando expresiones por el parametro "buscar" y chequeo que NO se evaluen: el
# resultado calculado no tiene que aparecer en la respuesta.
#
#   cd Ejercicio4
#   docker compose up -d --build        # http://localhost:8080
#   pytest tests -v
#   docker compose down

import os

import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080").rstrip("/")
TIMEOUT = 10


@pytest.fixture(scope="session", autouse=True)
def app_disponible():
    try:
        requests.get(BASE_URL + "/", timeout=TIMEOUT)
    except requests.RequestException as e:
        pytest.fail(f"No llego a {BASE_URL}. Levantar la app con docker compose up. Detalle: {e}")


def _buscar(expresion):
    r = requests.get(BASE_URL + "/", params={"buscar": expresion}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def test_expresion_aritmetica_no_se_evalua():
    # 1337*7331 = 9801547. Ese numero no esta en la entrada, asi que si aparece
    # en la respuesta es porque el servidor evaluo la cuenta.
    html = _buscar("1337*7331")
    assert "9801547" not in html, "Evaluo la expresion aritmetica (SpEL injection activa)."


def test_concatenacion_de_strings_no_se_evalua():
    # 'XYZ123'+'987ABC' daria 'XYZ123987ABC', que tampoco esta en la entrada.
    html = _buscar("'XYZ123'+'987ABC'")
    assert "XYZ123987ABC" not in html, "Evaluo la concatenacion: el motor SpEL sigue activo."


def test_acceso_a_tipos_java_no_se_evalua():
    # Mismo mecanismo que habilita T(java.lang.Runtime) para RCE, pero con una
    # operacion inofensiva. multiplyExact(1234,5678) = 7006652.
    html = _buscar("T(java.lang.Math).multiplyExact(1234,5678)")
    assert "7006652" not in html, "Evaluo una expresion con acceso a tipos Java (T(...))."
