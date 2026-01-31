# Ender - Deployment

Puedes desplegar el proyecto usando Docker Compose en un servidor remoto.

## Preparación

* Tener un servidor remoto disponible.
* Configurar los registros DNS de tu dominio para apuntar a la IP del servidor.
* Instalar y configurar [Docker](https://docs.docker.com/engine/install/) en el servidor remoto (Docker Engine, no Docker Desktop).

## Variables de Entorno

Necesitas configurar algunas variables de entorno.

Configura el `ENVIRONMENT`, por defecto `local` (para desarrollo), pero al desplegar en un servidor pondrías algo como `staging` o `production`:

```bash
export ENVIRONMENT=production
```

Puedes configurar varias variables, como:

* `PROJECT_NAME`: El nombre del proyecto, usado en la API para la documentación y emails.
* `BACKEND_CORS_ORIGINS`: Lista de orígenes CORS permitidos separados por comas.
* `SECRET_KEY`: La clave secreta para el proyecto FastAPI, usada para firmar tokens.
* `FIRST_SUPERUSER`: El email del primer superusuario.
* `FIRST_SUPERUSER_PASSWORD`: La contraseña del primer superusuario.
* `SMTP_HOST`: El host del servidor SMTP para enviar emails.
* `SMTP_USER`: El usuario del servidor SMTP.
* `SMTP_PASSWORD`: La contraseña del servidor SMTP.
* `EMAILS_FROM_EMAIL`: La cuenta de email desde la cual se envían los correos.
* `POSTGRES_SERVER`: El hostname del servidor PostgreSQL. Puedes dejar el valor por defecto `db`.
* `POSTGRES_PORT`: El puerto de PostgreSQL. Puedes dejar el valor por defecto.
* `POSTGRES_PASSWORD`: La contraseña de Postgres.
* `POSTGRES_USER`: El usuario de Postgres.
* `POSTGRES_DB`: El nombre de la base de datos.
* `SENTRY_DSN`: El DSN para Sentry, si lo estás usando.
* `VITE_API_URL`: La URL del backend para el frontend.

### Generar Claves Secretas

Algunas variables de entorno en el archivo `.env` tienen un valor por defecto de `changethis`.

Debes cambiarlas con una clave secreta. Para generar claves secretas puedes ejecutar:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copia el contenido y úsalo como contraseña / clave secreta. Ejecuta el comando nuevamente para generar otra clave.

## Desplegar con Docker Compose

Con las variables de entorno configuradas, puedes desplegar con Docker Compose:

```bash
docker compose -f docker-compose.yml up -d
```

Para producción no querrías tener los overrides en `docker-compose.override.yml`, por eso especificamos explícitamente `docker-compose.yml` como el archivo a usar.

## Despliegue Continuo (CD)

Puedes usar GitHub Actions para desplegar tu proyecto automáticamente.

Puedes tener múltiples entornos de despliegue.

Ya hay dos entornos configurados, `staging` y `production`.

### Instalar GitHub Actions Runner

* En tu servidor remoto, crea un usuario para GitHub Actions:

```bash
sudo adduser github
```

* Agrega permisos de Docker al usuario `github`:

```bash
sudo usermod -aG docker github
```

* Cambia temporalmente al usuario `github`:

```bash
sudo su - github
```

* Ve al directorio home del usuario `github`:

```bash
cd
```

* [Instala un GitHub Action self-hosted runner siguiendo la guía oficial](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners#adding-a-self-hosted-runner-to-a-repository).

* Cuando te pregunte por labels, agrega un label para el entorno, ej. `production`.

Después de instalar, la guía te dirá que ejecutes un comando para iniciar el runner. Sin embargo, se detendrá una vez que termines ese proceso.

Para asegurarte de que corra al inicio y continúe ejecutándose, puedes instalarlo como servicio:

```bash
exit
```

* Como usuario `root`, ve al directorio `actions-runner`:

```bash
sudo su
cd /home/github/actions-runner
```

* Instala el self-hosted runner como servicio:

```bash
./svc.sh install github
```

* Inicia el servicio:

```bash
./svc.sh start
```

* Verifica el estado:

```bash
./svc.sh status
```

### Configurar Secrets

En tu repositorio, configura secrets para las variables de entorno que necesitas. Sigue la [guía oficial de GitHub](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions#creating-secrets-for-a-repository).

Los workflows actuales de GitHub Actions esperan estos secrets:

* `EMAILS_FROM_EMAIL`
* `FIRST_SUPERUSER`
* `FIRST_SUPERUSER_PASSWORD`
* `POSTGRES_PASSWORD`
* `SECRET_KEY`

## URLs

Reemplaza `example.com` con tu dominio.

### Producción

Frontend: `https://example.com`

Backend API docs: `https://api.example.com/docs`

Backend API base URL: `https://api.example.com`

### Staging

Frontend: `https://staging.example.com`

Backend API docs: `https://api.staging.example.com/docs`

Backend API base URL: `https://api.staging.example.com`
