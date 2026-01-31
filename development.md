# Ender - Development

## Docker Compose

* Inicia el stack local con Docker Compose:

```bash
docker compose watch
```

* Ahora puedes abrir tu navegador e interactuar con estas URLs:

Frontend: <http://localhost:5173>

Backend, API web basada en JSON (OpenAPI): <http://localhost:8000>

Documentación interactiva automática con Swagger UI: <http://localhost:8000/docs>

Adminer, administración web de base de datos: <http://localhost:8080>

MailCatcher: <http://localhost:1080>

**Nota**: La primera vez que inicies tu stack, puede tomar un minuto para estar listo. Mientras el backend espera que la base de datos esté lista y configura todo. Puedes revisar los logs para monitorearlo.

Para revisar los logs, ejecuta (en otra terminal):

```bash
docker compose logs
```

Para revisar los logs de un servicio específico, agrega el nombre del servicio, ej.:

```bash
docker compose logs backend
```

## Mailcatcher

Mailcatcher es un servidor SMTP simple que captura todos los emails enviados por el backend durante el desarrollo local. En lugar de enviar emails reales, son capturados y mostrados en una interfaz web.

Esto es útil para:

* Probar funcionalidad de email durante el desarrollo
* Verificar contenido y formato de emails
* Debuggear funcionalidad relacionada con email sin enviar emails reales

El backend está configurado automáticamente para usar Mailcatcher cuando corre con Docker Compose localmente (SMTP en puerto 1025). Todos los emails capturados se pueden ver en <http://localhost:1080>.

## Desarrollo Local

Los archivos de Docker Compose están configurados para que cada servicio esté disponible en un puerto diferente en `localhost`.

Para el backend y frontend, usan el mismo puerto que usaría su servidor de desarrollo local, así que el backend está en `http://localhost:8000` y el frontend en `http://localhost:5173`.

De esta manera, podrías apagar un servicio de Docker Compose e iniciar su servidor de desarrollo local, y todo seguiría funcionando porque todo usa los mismos puertos.

Por ejemplo, puedes detener el servicio `frontend` en Docker Compose, en otra terminal, ejecuta:

```bash
docker compose stop frontend
```

Y luego inicia el servidor de desarrollo local del frontend:

```bash
cd frontend
npm run dev
```

O podrías detener el servicio `backend` de Docker Compose:

```bash
docker compose stop backend
```

Y luego puedes ejecutar el servidor de desarrollo local del backend:

```bash
cd backend
fastapi dev app/main.py
```

## Archivos de Docker Compose y variables de entorno

Hay un archivo principal `docker-compose.yml` con todas las configuraciones que aplican a todo el stack, es usado automáticamente por `docker compose`.

Y también hay un `docker-compose.override.yml` con overrides para desarrollo, por ejemplo para montar el código fuente como volumen. Es usado automáticamente por `docker compose` para aplicar overrides sobre `docker-compose.yml`.

Estos archivos de Docker Compose usan el archivo `.env` que contiene configuraciones para inyectar como variables de entorno en los contenedores.

Después de cambiar variables, asegúrate de reiniciar el stack:

```bash
docker compose watch
```

## El archivo .env

El archivo `.env` es el que contiene todas tus configuraciones, claves generadas y contraseñas, etc.

Dependiendo de tu flujo de trabajo, podrías querer excluirlo de Git, por ejemplo si tu proyecto es público. En ese caso, tendrías que asegurarte de configurar una manera para que tus herramientas de CI obtengan las variables mientras construyen o despliegan tu proyecto.

## Pre-commits y linting de código

Estamos usando una herramienta llamada [pre-commit](https://pre-commit.com/) para linting y formateo de código.

Cuando lo instalas, corre justo antes de hacer un commit en git. De esta manera asegura que el código sea consistente y formateado incluso antes de ser commiteado.

Puedes encontrar un archivo `.pre-commit-config.yaml` con configuraciones en la raíz del proyecto.

### Instalar pre-commit para que corra automáticamente

`pre-commit` ya es parte de las dependencias del proyecto, pero también podrías instalarlo globalmente si prefieres, siguiendo [la documentación oficial de pre-commit](https://pre-commit.com/).

Después de tener la herramienta `pre-commit` instalada y disponible, necesitas "instalarla" en el repositorio local, para que corra automáticamente antes de cada commit.

Usando `uv`, podrías hacerlo con:

```bash
❯ uv run pre-commit install
pre-commit installed at .git/hooks/pre-commit
```

Ahora cada vez que intentes hacer commit, pre-commit correrá y revisará y formateará el código que estás a punto de commitear, y te pedirá que agregues ese código (stage it) con git de nuevo antes de commitear.

### Correr pre-commit hooks manualmente

También puedes correr `pre-commit` manualmente en todos los archivos usando `uv`:

```bash
❯ uv run pre-commit run --all-files
check for added large files..............................................Passed
check toml...............................................................Passed
check yaml...............................................................Passed
ruff.....................................................................Passed
ruff-format..............................................................Passed
eslint...................................................................Passed
prettier.................................................................Passed
```

## URLs

### URLs de Desarrollo

URLs de desarrollo, para desarrollo local.

Frontend: <http://localhost:5173>

Backend: <http://localhost:8000>

Documentación Interactiva Automática (Swagger UI): <http://localhost:8000/docs>

Documentación Alternativa Automática (ReDoc): <http://localhost:8000/redoc>

Adminer: <http://localhost:8080>

MailCatcher: <http://localhost:1080>
