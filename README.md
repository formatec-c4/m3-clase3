# Modulo 3 - Clase 3: Docker y Docker Compose

En esta clase vamos a trabajar con Docker desde una aplicacion chica en Python. La idea no es memorizar comandos, sino entender el recorrido completo: escribir una app, construir una imagen, correr un contenedor y levantar una base de datos con Docker Compose.

Durante la practica vamos a ver:

- que problema resuelve Docker;
- diferencia entre imagen y contenedor;
- uso de Dockerfile;
- construccion y ejecucion de imagenes;
- variables de entorno;
- logs y diagnostico basico;
- Docker Compose;
- PostgreSQL como servicio;
- persistencia con volumenes;
- buenas practicas iniciales para imagenes.

## Prerrequisitos

Tener instalado:

- Docker;
- Docker Compose;
- un editor de texto;
- `curl` opcional para probar endpoints desde la terminal.

Antes de empezar, verificar:

```bash
docker --version
docker compose version
docker ps
```

Deberias ver las versiones instaladas y una tabla de contenedores. La tabla puede estar vacia.

Si `docker ps` falla, revisar que Docker este iniciado.

## 1. El problema que Docker resuelve

Una aplicacion puede funcionar en una computadora y fallar en otra por diferencias de entorno:

- distinta version de Python;
- dependencias faltantes;
- variables de entorno no configuradas;
- PostgreSQL no instalado;
- puertos ocupados;
- diferencias de sistema operativo.

Docker ayuda a empaquetar la aplicacion y sus dependencias en una imagen. Despues esa imagen se ejecuta como contenedor.

Algunas ideas base:

- Dockerfile: receta para construir una imagen.
- Imagen: paquete construido con sistema base, dependencias y codigo.
- Contenedor: instancia en ejecucion de una imagen.
- Docker Hub: repositorio de imagenes.
- Docker Engine: motor que construye imagenes y ejecuta contenedores.

Pregunta: que diferencia hay entre una imagen y un contenedor?

## 2. La aplicacion que vamos a usar

La aplicacion esta en `app.py` y expone estos endpoints:

- `GET /`: devuelve un mensaje simple.
- `GET /health`: devuelve `{"status":"ok"}`.
- `GET /db`: valida conexion a PostgreSQL.
- `GET /visits`: crea una tabla, inserta una visita y devuelve el total acumulado.

La configuracion se lee desde variables de entorno:

- `PORT`;
- `DATABASE_URL`.

Las dependencias estan en `requirements.txt`:

```text
flask
psycopg[binary]
```

La app escucha en `0.0.0.0` para poder recibir conexiones desde fuera del contenedor.

## 3. Elegir imagen base

Para Python se puede buscar la imagen oficial `python` en Docker Hub.

Tags comunes:

- `latest`: cambia con el tiempo. No conviene para practicas reproducibles.
- `3.12`: fija la version principal de Python.
- `3.12-slim`: version mas liviana basada en Debian.
- `3.12-alpine`: mas chica, pero puede traer complicaciones con dependencias nativas por musl/libc.

En esta practica se usa:

```text
python:3.12-slim
```

Es un buen equilibrio entre tamano, compatibilidad y simplicidad.

## 4. Primer Dockerfile: que funcione

Archivo: `Dockerfile.v1`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 3000
CMD ["python", "app.py"]
```

Construir la imagen:

```bash
docker build -f Dockerfile.v1 -t python-docker-app:v1 .
```

Notas:

- `docker build`: construye una imagen.
- `-f Dockerfile.v1`: indica que archivo usar.
- `-t python-docker-app:v1`: asigna nombre y tag.
- `.`: indica el build context, es decir, los archivos disponibles para copiar.

Deberias ver: Docker ejecuta las instrucciones del Dockerfile y crea una imagen local.

Pregunta: que representa el punto final del comando?

## 5. Ejecutar un contenedor

Ejecutar:

```bash
docker run --name python-app -p 3000:3000 python-docker-app:v1
```

Notas:

- `--name python-app`: nombre del contenedor.
- `-p 3000:3000`: publica `puerto_host:puerto_contenedor`.
- El primer `3000` es el puerto de la computadora.
- El segundo `3000` es el puerto dentro del contenedor.

Probar en otra terminal:

```bash
curl http://localhost:3000
curl http://localhost:3000/health
```

Deberias ver:

```json
{"message":"Hola desde Docker con Python"}
```

```json
{"status":"ok"}
```

Detener y borrar:

```bash
docker stop python-app
docker rm python-app
```

Pregunta: que cambiaria si se usara `-p 8080:3000`?

## 6. Inspeccionar contenedores

Comandos para mirar que esta pasando:

```bash
docker ps
docker logs python-app
docker exec -it python-app sh
```

Dentro del contenedor:

```bash
tr '\000' ' ' < /proc/1/cmdline; echo
exit
```

Notas:

- `docker ps`: muestra contenedores activos.
- `docker logs`: muestra stdout/stderr del contenedor.
- `docker exec`: ejecuta un comando dentro de un contenedor activo.
- `/proc/1/cmdline`: muestra el comando del proceso principal del contenedor.

Pregunta: por que los logs deben salir por stdout/stderr?

## 7. Mejorar el Dockerfile: que construya mejor

Archivo: `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=3000

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 3000

CMD ["python", "app.py"]
```

Construir:

```bash
docker build -t python-docker-app:v2 .
```

Que mejora:

- copia primero `requirements.txt` para aprovechar cache de layers;
- instala dependencias antes de copiar el codigo;
- evita cache de `pip` dentro de la imagen;
- configura Python para logs mas visibles;
- usa `CMD` en formato exec.

Importante: `EXPOSE 3000` documenta el puerto, pero no lo publica automaticamente. Para publicar se usa `-p` o `ports` en Compose.

Pregunta: por que conviene copiar `requirements.txt` antes que `app.py`?

## 8. .dockerignore

Archivo: `.dockerignore`

```text
__pycache__
*.pyc
.env
.git
.venv
venv
.pytest_cache
.coverage
htmlcov
```

El build context es el conjunto de archivos que Docker recibe para construir la imagen. No conviene enviar cache, entornos virtuales, `.git` o archivos `.env`.

Pregunta: que riesgo hay si `.env` entra en la imagen?

## 9. Variables de entorno

La configuracion no debe estar fija en el codigo.

Ejemplo:

```bash
docker run --name python-app -p 3000:3000 -e PORT=3000 python-docker-app:v2
```

En este punto `/` y `/health` funcionan. `/db` falla porque todavia no hay PostgreSQL ni `DATABASE_URL`.

Limpiar:

```bash
docker stop python-app
docker rm python-app
```

Pregunta: que configuracion falta para usar `/db`?

## 10. Docker Compose: app + PostgreSQL

Compose permite definir varios servicios en un archivo. En esta practica se usan:

- `app`: aplicacion Flask;
- `db`: base PostgreSQL.

Cuando Compose levanta estos servicios, tambien crea una red interna para el proyecto. Los contenedores conectados a esa red pueden hablar entre si usando el nombre del servicio como hostname.

En este caso:

- desde la computadora se entra a la app por `localhost:3000`;
- desde el contenedor `app`, PostgreSQL se alcanza como `db:5432`;
- `db` funciona porque es el nombre del servicio en `compose.yaml`;
- `localhost` dentro de `app` no es la computadora ni la base de datos: es el propio contenedor `app`.

Crear archivo `.env` desde el ejemplo:

```bash
cp .env.example .env
```

Contenido:

```env
APP_PORT=3000
POSTGRES_USER=usuario_dev
POSTGRES_PASSWORD=password123
POSTGRES_DB=mi_base
DATABASE_URL=postgres://usuario_dev:password123@db:5432/mi_base
```

Levantar servicios:

```bash
docker compose up -d
docker compose ps
```

Ver logs:

```bash
docker compose logs -f
```

Mirar la red creada por Compose:

```bash
docker network ls
docker compose exec app sh
```

Dentro del contenedor `app`:

```bash
python -c "import socket; print(socket.gethostbyname('db'))"
exit
```

Ese comando resuelve el hostname `db` a una IP interna de la red de Compose. La IP puede cambiar, por eso se usa el nombre del servicio y no una IP fija.

Probar:

```bash
curl http://localhost:3000
curl http://localhost:3000/health
curl http://localhost:3000/db
curl http://localhost:3000/visits
```

Deberias ver:

- `/db` devuelve hora de base de datos y nombre de base;
- `/visits` devuelve la visita insertada y el total acumulado.

Punto clave: `ports` publica un puerto hacia la computadora, pero no hace falta para que dos servicios se hablen dentro de la red de Compose. La app puede conectarse a `db:5432` aunque PostgreSQL no tenga un puerto publicado hacia el host.

Pregunta: por que `db` funciona como hostname?

## 11. Persistencia con volumenes

Probar varias visitas:

```bash
curl http://localhost:3000/visits
curl http://localhost:3000/visits
curl http://localhost:3000/visits
```

Detener sin borrar volumenes:

```bash
docker compose down
docker compose up -d
curl http://localhost:3000/visits
```

Deberias ver: el contador continua.

Borrar tambien los volumenes:

```bash
docker compose down -v
docker compose up -d
curl http://localhost:3000/visits
```

Deberias ver: el contador vuelve a empezar.

Pregunta: que diferencia hay entre `docker compose down` y `docker compose down -v`?

## 12. Cache de layers

Comparar:

```bash
docker build -f Dockerfile.bad -t python-app:bad .
docker build -f Dockerfile.cache -t python-app:cache .
```

`Dockerfile.bad`:

```dockerfile
FROM python:latest
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD python app.py
```

Problemas:

- `latest` no es reproducible;
- `COPY . .` copia demasiado;
- cualquier cambio puede invalidar `pip install`;
- usa shell form en `CMD`;
- puede copiar archivos innecesarios si no existe `.dockerignore`;
- corre como root.

`Dockerfile.cache` copia primero dependencias y luego codigo:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
CMD ["python", "app.py"]
```

Modificar `app.py` y volver a construir:

```bash
docker build -f Dockerfile.cache -t python-app:cache .
```

Deberias ver: si solo cambia `app.py`, la instalacion de dependencias puede reutilizar cache.

Pregunta: que pasa con el cache si cambia `requirements.txt`?

## 13. RUN, CMD y ENTRYPOINT

- `RUN`: se ejecuta durante el build.
- `CMD`: define el comando por defecto al iniciar el contenedor.
- `ENTRYPOINT`: define el ejecutable principal del contenedor.

Ejemplo para sobrescribir `CMD`:

```bash
docker run --rm python-app:cache python --version
```

Pregunta: cual de estas instrucciones se ejecuta durante `docker build`?

## 14. ARG y ENV

- `ARG`: existe durante el build.
- `ENV`: queda disponible en la imagen y en runtime.
- `env_file` y `environment` en Compose configuran el contenedor al ejecutarse.

No usar estas opciones para secretos reales dentro de imagenes.

Pregunta: donde deberia configurarse `DATABASE_URL`?

## 15. Multi-stage build y usuario no-root

Archivo: `Dockerfile.multistage`

```dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install \
    --prefix=/install \
    --no-cache-dir \
    -r requirements.txt


FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=3000
ENV PATH="/install/bin:${PATH}"
ENV PYTHONPATH="/install/lib/python3.12/site-packages"

RUN useradd --create-home appuser

COPY --from=builder /install /install
COPY app.py .

USER appuser

EXPOSE 3000

CMD ["python", "app.py"]
```

Construir:

```bash
docker build -f Dockerfile.multistage -t python-app:multistage .
```

Notas:

- `builder`: instala dependencias;
- `runtime`: contiene lo necesario para ejecutar;
- `COPY --from=builder`: copia archivos entre etapas;
- `USER appuser`: evita correr la app como root.

Ver usuario dentro del contenedor con Compose:

```bash
docker compose up -d
docker compose exec app id
```

Pregunta: por que conviene no correr la app como root?

## 16. Compose de desarrollo con bind mount

Levantar usando el archivo de desarrollo:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d
```

`compose.dev.yaml` monta el archivo local:

```yaml
volumes:
  - ./app.py:/app/app.py
```

Diferencia:

- named volume: Docker administra el almacenamiento, como `postgres_data`;
- bind mount: se monta un archivo o carpeta de la computadora dentro del contenedor.

Si se cambia `app.py`, reiniciar la app:

```bash
docker compose restart app
```

Pregunta: para que caso conviene un named volume y para que caso un bind mount?

## 17. Buenas practicas minimas

- No usar `latest` en imagenes importantes.
- No correr procesos como root si no hace falta.
- No copiar `.env` dentro de la imagen.
- No guardar secretos reales en el repositorio.
- Usar `.dockerignore`.
- Copiar dependencias antes que codigo para aprovechar cache.
- Enviar logs a stdout/stderr.
- Mantener un proceso principal por contenedor.
- Usar variables de entorno para configuracion.
- Persistir datos en volumenes, no dentro del contenedor de la app.

## 18. Problemas comunes

Docker no esta corriendo:

```bash
docker ps
```

Puerto ocupado:

```bash
lsof -i :3000
```

Cambiar `APP_PORT` en `.env`:

```env
APP_PORT=3001
```

La app no conecta a la DB:

```bash
docker compose ps
docker compose logs db
docker compose logs app
```

Variables no cargadas:

```bash
ls -la .env
docker compose config
```

El contenedor sale inmediatamente:

```bash
docker compose logs app
```

Se perdieron datos:

Revisar si se ejecuto:

```bash
docker compose down -v
```

Ese comando borra los volumenes.

## 19. Limpieza final

Detener y borrar contenedores, red y volumen:

```bash
docker compose down -v
```

Borrar imagenes creadas en la practica, si se desea:

```bash
docker rmi python-docker-app:v1 python-docker-app:v2 python-app:bad python-app:cache python-app:multistage
```

## Preguntas de cierre

- Que problema resuelve Docker?
- Que es un Dockerfile?
- Que es una imagen?
- Que es un contenedor?
- Que hace `RUN`?
- Que hace `CMD`?
- Que significa `-p 3000:3000`?
- Por que `db` funciona como hostname?
- Por que los datos sobreviven con volumen?
- Que diferencia hay entre named volume y bind mount?
- Que mejora aporta multi-stage build?
- Que significa que la app sea stateless?
