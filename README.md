# StudyTrack

StudyTrack is a full-stack personal study coach. It records study sessions in one persistent data source, turns that history into explainable analytics, and helps students plan realistically for multiple exams.

## Features

- **Sessions** — Log study duration, subject, mood, productivity, and reflections; review or remove prior sessions.
- **Insights** — See subject progress, duration and mood patterns, smart recommendations, cognitive stability, burnout signals, and focus efficiency.
- **Daily Advisor** — Get an explainable recommendation for a subject, session length, and break rhythm. After 12 sessions across two subjects, it also shows a confidence-labelled Random Forest productivity prediction.
- **Study Replay** — Review a chronological timeline of sessions, study footprint, focus changes, and subject-switch patterns.
- **Multi-exam Planner** — Create exams with a date, module count, and daily availability. StudyTrack generates dated study, revision, and final-review modules; tracks completion; ranks priorities; and flags at-risk or unrealistic plans.
- **Resettable demo** — Reset restores the complete seeded workspace: subjects, sessions, exams, generated tasks, completion state, and trained-model state.

## Run locally

### Without Docker

This mode uses the backend's local SQLite database and does not require PostgreSQL or Docker.

```bash
# Terminal 1
cd backend
.venv/bin/uvicorn app.main:app --reload

# Terminal 2
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API documentation is at `http://localhost:8000/docs`.

### With Docker Compose

Copy the example local environment and choose a non-default development password:

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:5173`. Docker Compose starts PostgreSQL, the FastAPI API, and the Vite frontend.

## Quality checks

```bash
cd backend && .venv/bin/pytest -q
cd frontend && npm run build
docker compose config
```

## Data and deployment

- PostgreSQL is the source of truth in Compose and production. Browser storage is never used for study data.
- This first release is a single resettable demo workspace; authentication, collaboration, and mentor views are intentionally out of scope.
- `.env.example` contains **local-demo defaults only**. Never commit `.env`, and use deployment-managed secrets plus a managed PostgreSQL instance in production.
- The legacy `Mini-Project` folder is reference material and is not part of this standalone application repository.
