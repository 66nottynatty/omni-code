# OmniCode

AI-powered code analysis and automation platform featuring a Next.js 14 frontend, FastAPI backend with LangGraph, and Dockerized infrastructure.

## Architecture

```
├── frontend/          # Next.js 14 with Tailwind + shadcn/ui + NextAuth
├── backend/          # FastAPI with LangGraph agentic workflows
└── docker-compose.yml
```

## Features

- **Frontend**: Next.js 14 App Router, Tailwind CSS, shadcn/ui components, GitHub OAuth via NextAuth
- **Backend**: FastAPI with LangGraph for agentic workflows, PostgreSQL persistence, Redis caching
- **Infrastructure**: Docker Compose with PostgreSQL 15, Redis 7, multi-stage builds

## Quick Start

### Prerequisites

- Docker & Docker Compose v2
- Node.js 20+ (for local development)
- Python 3.12+ (for local development)

### Setup

1. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

2. Update `.env` with your GitHub OAuth credentials:
   - Create a GitHub OAuth App at https://github.com/settings/developers
   - Set callback URL to `http://localhost:3000/api/auth/callback/github`

3. Start services:
   ```bash
   docker-compose up
   ```

4. Access the application:
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs

## Development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React 18, Tailwind CSS, shadcn/ui |
| Auth | NextAuth.js with GitHub OAuth |
| Backend | FastAPI, LangGraph, Pydantic |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Container | Docker Compose |

## License

MIT
