# ConfigHub

ConfigHub is a feature flag and remote configuration platform built as a small monorepo. It includes a FastAPI backend, a Next.js admin dashboard, and SDKs for JavaScript/TypeScript and Python.

The project is designed to cover the full workflow:
- manage organizations, products, configs, and environments
- create flags and remote config values
- define targeting rules and segments
- expose a public `config.json` endpoint for SDK consumers
- evaluate flags client-side with lightweight JS and Python SDKs
- track changes with audit logs and webhook integrations

## What's Inside

### Backend
- FastAPI application with async SQLAlchemy
- JWT-based auth
- APIs for organizations, products, configs, environments, settings, segments, tags, permissions, audit logs, and webhooks
- Public SDK endpoint at `/api/v1/sdk/{sdk_key}/config.json`

### Frontend
- Next.js 14 app router dashboard
- login and registration flows
- dashboard screens for orgs, products, configs, environments, flags, segments, tags, audit logs, SDK keys, and webhooks

### SDK
- package name: `@confighub/sdk-js`
- package name: `confighub-sdk`
- fetches config JSON from the backend
- caches config locally
- supports polling and ETag-based refreshes
- evaluates targeting rules, segments, and percentage rollouts in the client

## Tech Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL or SQLite, Pydantic Settings
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS
- SDKs: TypeScript, Python
- Local container setup: Docker Compose

## Repo Layout

```text
.
├── backend/          FastAPI API server
├── frontend/         Next.js dashboard
├── packages/sdk-js/  JavaScript/TypeScript SDK
├── packages/sdk-python/ Python SDK
└── docker-compose.yml
```

## Quick Start

### Option 1: Run with Docker Compose

This is the fastest way to bring up the full stack.

```bash
docker compose up --build
```

Services:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Health check: `http://localhost:8000/api/v1/health`
- PostgreSQL: `localhost:5432`

The Docker setup uses PostgreSQL and wires the frontend to the backend with:
- `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `DATABASE_URL=postgresql+asyncpg://confighub:confighub@db:5432/confighub`

### Option 2: Run Locally

#### Backend

The backend defaults to SQLite for local development if `DATABASE_URL` is not set.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

Backend will start on `http://localhost:8000`.

#### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Frontend will start on `http://localhost:3000`.

#### SDK Package

```bash
cd packages/sdk-js
npm install
npm run build
```

#### Python SDK Package

```bash
cd packages/sdk-python
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Environment Notes

### Backend

Important backend environment variables:

```env
DATABASE_URL=sqlite+aiosqlite:///./flagsmith.db
JWT_SECRET_KEY=change-me-in-production-use-a-real-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]
```

Notes:
- local development can run on SQLite
- Docker Compose uses PostgreSQL
- table creation currently happens automatically on startup for convenience

### Frontend

Important frontend environment variable:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

This value is baked into the browser bundle at build time, so it should point to a URL reachable from the user's machine.

## API Surface

The backend exposes routes for:
- auth
- organizations
- products
- configs
- environments
- settings and values
- segments
- tags
- permissions
- audit logs
- webhooks
- SDK config delivery

Health endpoint:

```text
GET /api/v1/health
```

Public SDK endpoint:

```text
GET /api/v1/sdk/{sdk_key}/config.json
```

## SDK Examples

```ts
import { ConfigHubClient } from "@confighub/sdk-js";

const client = await ConfigHubClient.create("YOUR_SDK_KEY", {
  baseUrl: "http://localhost:8000",
});

const showNewCheckout = client.getValue("new_checkout", false, {
  identifier: "user-123",
  country: "IN",
  plan: "pro",
});
```

```python
from confighub_sdk import ConfigHubClient

client = ConfigHubClient.create(
    "YOUR_SDK_KEY",
    base_url="http://localhost:8000",
)

show_new_checkout = client.get_value(
    "new_checkout",
    False,
    {"identifier": "user-123", "country": "IN", "plan": "pro"},
)
```

The SDK can also:
- refresh config on demand
- poll for config changes
- evaluate all flags for a user in one call

## Linting

Ruff is configured at the repo root for all Python code in `backend/` and `packages/sdk-python/`.

```bash
make lint
make format
ruff check backend packages/sdk-python
ruff format backend packages/sdk-python
```

## Development Notes

- The repo uses a root `.gitignore` plus package-level `.gitignore` files where framework-specific rules make sense.
- The frontend and SDK are now regular folders in the main repo, not nested Git repositories.
- The SDK package intentionally ignores local `dist/` and `node_modules/` output.

## Current Status

This repository already contains the main building blocks for a working feature flag platform:
- backend APIs and data models
- frontend dashboard flows
- public SDK config endpoint
- TypeScript SDK package

The next likely areas to improve are tests, production deployment hardening, migrations, and developer documentation for API/auth flows.
