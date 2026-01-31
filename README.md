# Ender - SMS Gateway Platform

[Leer en Español](./README.es.md)

Ender is a full-stack platform for SMS management and delivery through connected devices. It allows sending SMS messages using registered devices (Android phones or modems) as gateways, with quota management, webhooks, and multi-user support.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.13+)
- **Database**: PostgreSQL 17 with SQLModel ORM
- **Authentication**: JWT (JSON Web Tokens)
- **Migrations**: Alembic
- **Push Notifications**: Firebase Cloud Messaging (FCM)
- **Message Queue**: QStash (Upstash)
- **Email**: SMTP with Mailcatcher for local development
- **Tests**: Pytest with coverage
- **Code Quality**: Ruff, MyPy, pre-commit hooks

### Frontend
- **Framework**: React 19 with TypeScript
- **Build**: Vite
- **State**: TanStack Query + TanStack Router
- **Styling**: Tailwind CSS + shadcn/ui
- **Forms**: React Hook Form + Zod
- **API Client**: Auto-generated from OpenAPI
- **E2E Tests**: Playwright

### Infrastructure
- **Containers**: Docker & Docker Compose
- **CI/CD**: GitHub Actions

## Main Features

### SMS
- Single and bulk SMS sending
- Round-robin distribution across devices
- Message queuing when no devices are online
- Status tracking (pending, queued, processing, sent, delivered, failed)
- SMS history and reports
- Incoming SMS support

### Devices
- Device registration with unique API keys
- FCM token management for push notifications
- Device status monitoring

### Quotas and Plans
- Multiple subscription plans
- Monthly SMS quota tracking
- Device limits per plan
- Configurable automatic quota reset

### Webhooks
- Webhook configuration for status updates
- Automatic delivery on SMS events

### Integrations
- Multiple API keys per user
- QR codes for device onboarding
- Public API for external systems

## Project Structure

```
ender/
├── backend/                    # FastAPI API
│   ├── app/
│   │   ├── api/routes/         # Endpoints (login, users, sms, webhooks, etc.)
│   │   ├── services/           # Business logic (SMS, FCM, Queue, Quota)
│   │   ├── core/               # Config, DB, Security
│   │   ├── models.py           # SQLModel models
│   │   └── crud.py             # Database operations
│   ├── tests/
│   └── scripts/
├── frontend/                   # React App
│   ├── src/
│   │   ├── routes/             # Pages (TanStack Router)
│   │   ├── components/         # React components
│   │   ├── client/             # Auto-generated API client
│   │   └── hooks/
│   └── tests/                  # Playwright tests
├── docker-compose.yml
├── docker-compose.override.yml # Development overrides
└── .env                        # Environment variables
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js (see `.nvmrc`)
- Python 3.13+
- uv (Python package manager)

### Development with Docker Compose (Recommended)

```bash
# Start full stack with hot reload
docker compose watch

# Or without watching
docker compose up -d --wait
```

**Available services:**
| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Adminer (DB UI) | http://localhost:8080 |
| Mailcatcher | http://localhost:1080 |

### Manual Development

#### Backend
```bash
cd backend

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Run development server
fastapi dev app/main.py

# Run tests
pytest
# or
bash ./scripts/test.sh
```

#### Frontend
```bash
cd frontend

# Install Node version
fnm use  # or nvm use

# Install dependencies
npm install

# Development server
npm run dev

# Generate API client from OpenAPI
npm run generate-client

# E2E tests
npx playwright test
```

## Configuration

### Required Environment Variables

Create a `.env` file in the project root:

```env
# Database
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-password>
POSTGRES_DB=ender
POSTGRES_PORT=5432

# Application
PROJECT_NAME=ender
ENVIRONMENT=local
SECRET_KEY=<generate-with-command-below>
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=<your-password>

# Frontend
FRONTEND_HOST=http://localhost:5173
BACKEND_CORS_ORIGINS=http://localhost,http://localhost:5173

# Plans
DEFAULT_PLAN=free
QUOTA_RESET_DAY=1

# Firebase (for push notifications)
FIREBASE_SERVICE_ACCOUNT_JSON=<firebase-json>

# QStash (message queue)
QSTASH_TOKEN=<your-token>
QSTASH_URL=http://localhost:8080
QSTASH_CURRENT_SIGNING_KEY=<signing-key>
QSTASH_NEXT_SIGNING_KEY=<next-signing-key>
SERVER_BASE_URL=http://localhost:8000
```

### Generate Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Testing

### Backend
```bash
# Run all tests
docker compose exec backend pytest

# With coverage
docker compose exec backend bash scripts/tests-start.sh
```

### Frontend
```bash
# E2E tests
npx playwright test

# UI mode
npx playwright test --ui
```

## Database Migrations

```bash
# Create new migration
docker compose exec backend alembic revision --autogenerate -m "Description"

# Apply migrations
docker compose exec backend alembic upgrade head
```

## Deployment

See [deployment.md](./deployment.md) for detailed production deployment instructions.

## Additional Documentation

- [Development](./development.md) - Local development guide
- [Deployment](./deployment.md) - Production instructions
- [Backend](./backend/README.md) - Backend documentation
- [Frontend](./frontend/README.md) - Frontend documentation
- [Release Notes](./release-notes.md) - Version history

## License

MIT License
