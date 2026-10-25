# CineBuscador - Desarrollo de Software Seguro

Repositorio de los prácticos de la materia. Tiene dos ramas:

- **main**: las aplicaciones con las vulnerabilidades sin corregir.
- **practico-2**: las mismas aplicaciones con las vulnerabilidades mitigadas.

En el Práctico 4 se agregaron pruebas automatizadas para cada vulnerabilidad. Están
pensadas para correr igual en las dos ramas: **fallan en `main`** (porque la
vulnerabilidad está presente) y **pasan en `practico-2`** (porque ya está mitigada).

## Qué se prueba en cada ejercicio

| Ejercicio | Vulnerabilidad | Tipo de prueba | Herramienta |
|-----------|----------------|----------------|-------------|
| 1 | SQL Injection | Unitaria | Pytest |
| 2 | Cross-Site Scripting (almacenado) | Unitaria | Pytest |
| 3 | Carga insegura de archivos | Integración | Pytest + requests |
| 4 | SSTI / SpEL injection (RCE) | Integración | Pytest + requests |
| 5 | Almacenamiento inseguro de contraseñas | Unitaria | JUnit 5 + Mockito |

> Nota sobre la numeración: la consigna del Práctico 4 nombra "SSTI" para el
> ejercicio 3 y "RCE" para el 4. En este repositorio el ejercicio 3 es la
> vulnerabilidad de carga de archivos y el 4 es la de SpEL injection, que es
> justamente la que lleva a RCE. Las pruebas validan la vulnerabilidad real de
> cada ejercicio.

## Requisitos

- Python 3.11 o superior
- Docker Desktop (para las pruebas de integración de los ejercicios 3 y 4)
- Para las pruebas de JUnit: JDK 17 y Maven. Si no están instalados, se pueden
  correr dentro de un contenedor (ver más abajo).

Instalar las dependencias de Python de las pruebas:

```bash
pip install -r requirements-test.txt
```

## Pruebas unitarias (Ejercicios 1 y 2)

Se corren por línea de comando, sin levantar el servidor ni Docker. Arman una
base SQLite temporal, así que no tocan las bases reales.

```bash
pytest Ejercicio1/tests -v
pytest Ejercicio2/tests -v
```

## Pruebas de integración (Ejercicios 3 y 4)

Se corren contra la aplicación levantada en Docker. Los dos ejercicios usan el
puerto 8080, así que hay que correrlos de a uno.

Ejercicio 3:

```bash
cd Ejercicio3
docker compose up -d --build
cd ..
pytest Ejercicio3/tests -v
cd Ejercicio3 && docker compose down && cd ..
```

Ejercicio 4:

```bash
cd Ejercicio4
docker compose up -d --build
cd ..
pytest Ejercicio4/tests -v
cd Ejercicio4 && docker compose down && cd ..
```

Si la app quedó en otra URL, se puede cambiar con la variable `BASE_URL`, por
ejemplo `BASE_URL=http://localhost:9000 pytest Ejercicio4/tests -v`.

## Pruebas de JUnit (Ejercicio 5)

Con JDK 17 y Maven instalados:

```bash
cd Ejercicio5
mvn test
```

Si no hay Maven/JDK 17 en la máquina, se puede correr en un contenedor (desde la
carpeta `Ejercicio5`):

```bash
docker run --rm -v "$(pwd)":/app -w /app maven:3.9-eclipse-temurin-17 mvn test
```

## Para ver que fallan en main

Las pruebas están pensadas para pasar en `practico-2`. Si se ejecutan los mismos
comandos parados en la rama `main`, las pruebas de seguridad fallan, que es lo
esperado (demuestran que la vulnerabilidad sigue ahí).
