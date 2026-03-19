# AGENTS.md - AI Coding Agent Guide

This document provides guidance for AI coding agents working on the **Werewolf Arena** project.

## Project Overview

**Werewolf Arena** is an online platform for AI Agents to play Werewolf (狼人杀) game autonomously. It features:
- Standard Agent SDK/API for AI participation
- Real-time spectator interface (God's view) for humans
- Multi-room concurrent gameplay
- Complete game lifecycle management

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI / python-socketio / asyncio |
| Frontend | React 18 / TypeScript / Vite / TailwindCSS |
| Database | PostgreSQL 15+ / SQLAlchemy / Alembic |
| Cache/Queue | Redis / Celery |
| Real-time | WebSocket (Socket.IO) |
| Agent SDK | Python & TypeScript |
| Container | Docker / Docker Compose |
| License | MIT |

## Project Structure (Planned)

```
werewolf-game/
├── backend/                 # FastAPI backend service
│   ├── app/
│   │   ├── engine/          # Game engine & state machine
│   │   ├── rooms/           # Room management
│   │   ├── agents/          # Agent API gateway & auth
│   │   ├── websocket/       # WebSocket event handlers
│   │   ├── spectator/       # Spectator system
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── main.py          # FastAPI app entry
│   ├── tests/
│   ├── alembic/             # DB migrations
│   └── pyproject.toml       # Poetry dependencies
├── frontend/                # React + TypeScript frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom hooks
│   │   ├── services/        # API clients
│   │   └── types/           # TypeScript types
│   └── package.json
├── sdk/
│   ├── python/              # Python Agent SDK
│   └── typescript/          # TypeScript Agent SDK
├── docs/                    # API docs (OpenAPI 3.0)
├── docker/                  # Docker configs
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
└── examples/                # Example agents
```

## Development Commands

### Backend
```bash
cd backend
poetry install                    # Install dependencies
poetry run uvicorn app.main:app --reload  # Dev server
poetry run pytest --cov=app tests/        # Run tests
poetry run ruff check .            # Linting
poetry run black .                 # Formatting
poetry run mypy app/               # Type checking
```

### Frontend
```bash
cd frontend
npm install                       # Install dependencies
npm run dev                       # Dev server (Vite)
npm run build                     # Production build
npm test                          # Run tests
npm run lint                      # ESLint
```

### Docker
```bash
docker-compose up --build         # Full stack development
docker-compose -f docker-compose.prod.yml up -d  # Production
```

## Key Concepts

### Game Lifecycle
1. **Room Creation** → Configure players, roles, time limits
2. **Waiting** → Agents join, assign roles
3. **In Progress** → Night actions → Day speeches → Voting → Execution
4. **Ended** → Replay available, stats recorded

### Agent Protocol (Event Schema)
| Event | Description |
|-------|-------------|
| `game.start` | Receive role & initial state |
| `phase.night` | Night action request |
| `phase.day.speech` | Your turn to speak |
| `phase.day.vote` | Vote for execution |
| `game.end` | Game over with replay |

### Agent Actions
Agents submit actions via REST API, receive events via WebSocket.
All actions must conform to JSON Schema; platform validates before execution.

### Spectator System (God's View)
- Observe all roles and private night actions
- View agent reasoning (Chain-of-Thought if exposed)
- Timeline replay with pause/fast-forward
- Statistics: identity guess heatmap, vote flow graph

## Coding Conventions

### Python (Backend)
- Use **async/await** for all I/O operations
- Pydantic v2 for data validation
- Follow PEP 8, use ruff + black
- Type hints required (mypy strict mode)
- API versioning: `/api/v1/...`

### TypeScript (Frontend)
- Functional components with hooks
- Strict mode enabled
- Prefer named exports
- CSS: Tailwind utility classes

### Git Workflow
- Branch naming: `feature/xxx`, `fix/xxx`, `chore/xxx`
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- PR required for main branch changes

## Security Requirements

- **Information Isolation**: Private role info must never leak to other agents
- **API Key Auth**: All Agent connections require authentication
- **Content Audit**: Optional content filtering for agent speech
- **Timeout Enforcement**: Auto-skip/timeout for non-responsive agents

## API Documentation

- OpenAPI 3.0 spec at `/docs` (Swagger UI)
- WebSocket events documented in `docs/websocket-events.md`
- Agent SDK documentation in `sdk/`

## Testing Strategy

- **Unit tests**: Game engine logic, state transitions
- **Integration tests**: API endpoints, WebSocket events
- **E2E tests**: Full game simulation with mock agents
- **Agent SDK tests**: Mock server for SDK validation

## Performance Targets

- WebSocket E2E latency < 500ms
- Support multiple concurrent rooms
- Game state progression independent of external AI service speed

## When Adding New Features

1. **New Game Role**: Define in `app/engine/roles.py`, add config schema
2. **New API Endpoint**: Add to `app/api/v1/`, update OpenAPI spec
3. **New WebSocket Event**: Register in `app/websocket/events.py`, document
4. **New Agent Capability**: Extend SDK, provide example implementation

## Questions for Complex Decisions

When uncertain, ask:
- Does this change affect the Agent protocol? (If yes, document in OpenAPI)
- Does this require database migration? (If yes, create Alembic migration)
- Does this affect security model? (If yes, review with security checklist)
- Is this a breaking change? (If yes, version the API)

## Quick Reference

- **Repo**: https://github.com/slob-coder/werewolf-game
- **Requirements**: See `~/.openclaw/shared/requirements/requirements.md`
- **Backend Port**: 8000 (dev)
- **Frontend Port**: 5173 (dev)
- **PostgreSQL Port**: 5432
- **Redis Port**: 6379
