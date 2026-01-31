# Ender - Plataforma SMS Gateway

[Read in English](./README.md)

Ender es una plataforma full-stack para gestión y envío de SMS a través de dispositivos conectados. Permite enviar mensajes SMS usando dispositivos registrados (teléfonos Android o módems) como gateways, con gestión de cuotas, webhooks y soporte para múltiples usuarios.

## Stack Tecnológico

### Backend
- **Framework**: FastAPI (Python 3.13+)
- **Base de datos**: PostgreSQL 17 con SQLModel ORM
- **Autenticación**: JWT (JSON Web Tokens)
- **Migraciones**: Alembic
- **Push Notifications**: Firebase Cloud Messaging (FCM)
- **Cola de mensajes**: QStash (Upstash)
- **Email**: Agnóstico de proveedor (Maileroo, SMTP) con Mailcatcher para dev local
- **Tests**: Pytest con coverage
- **Calidad de código**: Ruff, MyPy, pre-commit hooks

### Frontend
- **Framework**: React 19 con TypeScript
- **Build**: Vite
- **Estado**: TanStack Query + TanStack Router
- **Estilos**: Tailwind CSS + shadcn/ui
- **Formularios**: React Hook Form + Zod
- **Cliente API**: Auto-generado desde OpenAPI
- **Tests E2E**: Playwright

### Infraestructura
- **Contenedores**: Docker & Docker Compose
- **CI/CD**: GitHub Actions

## Funcionalidades Principales

### SMS
- Envío de SMS individuales y masivos
- Distribución round-robin entre dispositivos
- Cola de mensajes cuando no hay dispositivos online
- Tracking de estado (pending, queued, processing, sent, delivered, failed)
- Historial y reportes de SMS
- Soporte para SMS entrantes

### Dispositivos
- Registro de dispositivos con API keys únicas
- Gestión de tokens FCM para push notifications
- Monitoreo de estado de dispositivos

### Cuotas y Planes
- Múltiples planes de suscripción
- Tracking de cuota mensual de SMS
- Límites de dispositivos por plan
- Reset automático de cuota configurable

### Webhooks
- Configuración de webhooks para actualizaciones de estado
- Entrega automática en eventos de SMS

### Integraciones
- API keys múltiples por usuario
- Códigos QR para onboarding de dispositivos
- API pública para sistemas externos

## Estructura del Proyecto

```
ender/
├── backend/                    # API FastAPI
│   ├── app/
│   │   ├── api/routes/         # Endpoints (login, users, sms, webhooks, etc.)
│   │   ├── services/           # Lógica de negocio (SMS, FCM, Queue, Quota)
│   │   ├── core/               # Config, DB, Security
│   │   ├── models.py           # Modelos SQLModel
│   │   └── crud.py             # Operaciones de base de datos
│   ├── tests/
│   └── scripts/
├── frontend/                   # App React
│   ├── src/
│   │   ├── routes/             # Páginas (TanStack Router)
│   │   ├── components/         # Componentes React
│   │   ├── client/             # Cliente API auto-generado
│   │   └── hooks/
│   └── tests/                  # Tests Playwright
├── docker-compose.yml
├── docker-compose.override.yml # Overrides para desarrollo
└── .env                        # Variables de entorno
```

## Inicio Rápido

### Requisitos Previos
- Docker y Docker Compose
- Node.js (ver `.nvmrc`)
- Python 3.13+
- uv (gestor de paquetes Python)

### Desarrollo con Docker Compose (Recomendado)

```bash
# Iniciar stack completo con hot reload
docker compose watch

# O sin watching
docker compose up -d --wait
```

**Servicios disponibles:**
| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Adminer (DB UI) | http://localhost:8080 |
| Mailcatcher | http://localhost:1080 |

### Desarrollo Manual

#### Backend
```bash
cd backend

# Instalar dependencias
uv sync

# Activar entorno virtual
source .venv/bin/activate

# Ejecutar servidor de desarrollo
fastapi dev app/main.py

# Ejecutar tests
pytest
# o
bash ./scripts/test.sh
```

#### Frontend
```bash
cd frontend

# Instalar versión de Node
fnm use  # o nvm use

# Instalar dependencias
npm install

# Servidor de desarrollo
npm run dev

# Generar cliente API desde OpenAPI
npm run generate-client

# Tests E2E
npx playwright test
```

## Configuración

### Variables de Entorno Requeridas

Crea un archivo `.env` en la raíz del proyecto:

```env
# Base de datos
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<tu-password>
POSTGRES_DB=ender
POSTGRES_PORT=5432

# Aplicación
PROJECT_NAME=ender
ENVIRONMENT=local
SECRET_KEY=<generar-con-comando-abajo>
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=<tu-password>

# Frontend
FRONTEND_HOST=http://localhost:5173
BACKEND_CORS_ORIGINS=http://localhost,http://localhost:5173

# Planes
DEFAULT_PLAN=free
QUOTA_RESET_DAY=1

# Firebase (para push notifications)
FIREBASE_SERVICE_ACCOUNT_JSON=<json-de-firebase>

# QStash (cola de mensajes)
QSTASH_TOKEN=<tu-token>
QSTASH_URL=http://localhost:8080
QSTASH_CURRENT_SIGNING_KEY=<signing-key>
QSTASH_NEXT_SIGNING_KEY=<next-signing-key>
SERVER_BASE_URL=http://localhost:8000

# Proveedor de Email (smtp o maileroo)
EMAIL_PROVIDER=smtp
EMAILS_FROM_EMAIL=noreply@tudominio.com
EMAILS_FROM_NAME=Ender

# Para SMTP (desarrollo local con Mailcatcher)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_TLS=false

# Para Maileroo (producción)
# EMAIL_PROVIDER=maileroo
# MAILEROO_API_KEY=<tu-api-key-de-maileroo>
```

### Generar Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Testing

### Backend
```bash
# Ejecutar todos los tests
docker compose exec backend pytest

# Con coverage
docker compose exec backend bash scripts/tests-start.sh
```

### Frontend
```bash
# Tests E2E
npx playwright test

# Modo UI
npx playwright test --ui
```

## Migraciones de Base de Datos

```bash
# Crear nueva migración
docker compose exec backend alembic revision --autogenerate -m "Descripción"

# Aplicar migraciones
docker compose exec backend alembic upgrade head
```

## Despliegue

Ver [deployment.md](./deployment.md) para instrucciones detalladas de despliegue en producción.

## Documentación Adicional

- [Desarrollo](./development.md) - Guía de desarrollo local
- [Despliegue](./deployment.md) - Instrucciones de producción
- [Backend](./backend/README.md) - Documentación del backend
- [Frontend](./frontend/README.md) - Documentación del frontend
- [Release Notes](./release-notes.md) - Historial de versiones

## Licencia

MIT License
