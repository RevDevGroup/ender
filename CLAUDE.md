# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ender is a full-stack SMS gateway platform that allows sending SMS messages using registered devices (Android phones or modems) as gateways. Features include quota management, webhooks, multi-user support, and API key authentication.

## Commands

### Development (Docker Compose - Recommended)
```bash
docker compose watch          # Start full stack with hot reload
docker compose up -d --wait   # Start without watching
docker compose down -v        # Clean up with volumes
```

### Backend
```bash
cd backend
uv sync                       # Install dependencies
source .venv/bin/activate     # Activate venv
fastapi dev app/main.py       # Run dev server

# Testing
pytest                        # Run all tests
pytest -x                     # Stop on first failure
pytest tests/path/test_file.py::test_name  # Run single test
bash ./scripts/test.sh        # Run with coverage report

# Code quality
ruff check --fix              # Lint and fix
ruff format                   # Format code
mypy                          # Type checking (strict mode)
```

### Frontend
```bash
cd frontend
fnm use                       # Switch to Node 24 (or nvm use)
npm install
npm run dev                   # Dev server at localhost:5173
npm run build                 # TypeScript + Vite build
npm run lint                  # Biome check with auto-fix
npm run generate-client       # Regenerate OpenAPI client

# E2E tests (requires backend running)
npx playwright test
npx playwright test --ui      # Interactive UI mode
```

### Pre-commit
```bash
uv run pre-commit install     # Setup git hooks
uv run pre-commit run --all-files  # Run manually
```

### Database Migrations
```bash
docker compose exec backend bash
alembic revision --autogenerate -m "Description"  # Create migration
alembic upgrade head          # Apply migrations
```

### Generate Frontend API Client
```bash
./scripts/generate-client.sh  # From project root (backend venv must be active)
```

## Architecture

### Backend (`backend/`)
- **Framework**: FastAPI with Python 3.13+
- **Database**: PostgreSQL 17 with SQLModel ORM
- **Key directories**:
  - `app/api/routes/` - API endpoints (login, users, sms, webhooks, api_keys, plans)
  - `app/services/` - Business logic (sms_service, fcm_service, qstash_service, quota_service, webhook_service)
  - `app/core/` - Config, DB setup, security, rate limiting
  - `app/models.py` - SQLModel data models
  - `app/crud.py` - Database CRUD operations
  - `app/alembic/` - Database migrations

### Frontend (`frontend/`)
- **Framework**: React 19 + TypeScript + Vite
- **Routing/State**: TanStack Router + TanStack Query
- **Styling**: Tailwind CSS + shadcn/ui components
- **Key directories**:
  - `src/routes/` - Pages using TanStack Router file-based routing
  - `src/components/` - React components
  - `src/client/` - Auto-generated OpenAPI client (do not edit manually)
  - `src/hooks/` - Custom React hooks

### Services Integration
- **FCM**: Firebase Cloud Messaging for push notifications to devices
- **QStash**: Upstash message queue for async SMS processing
- **Email**: Provider-agnostic (SMTP/Maileroo), Mailcatcher for local dev at localhost:1080

## Code Quality Standards

### Backend
- MyPy strict mode enabled
- Ruff for linting (pycodestyle, pyflakes, isort, flake8-bugbear, pyupgrade)
- Print statements not allowed (T201 rule)

### Frontend
- Biome for linting and formatting
- TypeScript strict mode
- API client auto-generated from OpenAPI - regenerate after backend API changes

## Development URLs
| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Adminer (DB) | http://localhost:8080 |
| Mailcatcher | http://localhost:1080 |

## Email Templates

Email templates use MJML. Source files are in `backend/app/email-templates/src/`. Use the VS Code MJML extension to export to HTML, then save to the `build/` directory.
