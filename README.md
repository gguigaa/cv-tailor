# CV Tailor

A self-hosted web application that uses the Claude API to generate job-tailored resumes from a single master CV. Paste a job description, get an ATS-optimized resume in seconds — in Portuguese or English.

## The Problem

Sending the same resume to every job posting is inefficient. Each role has its own language, requirements, and culture. Adapting manually is tedious. CV Tailor automates the process: maintain one comprehensive Master CV, paste the job description, and Claude selects, adapts, and rewrites the content to maximize the match — including ATS keyword alignment.

## Features

- **Master CV in two languages** — maintain separate PT and EN versions; switch via header toggle
- **AI-powered generation** — Claude reads your full Master CV and rewrites it for the specific role
- **Natural language adjustments** — refine the output conversationally ("make it more concise", "emphasize technical leadership")
- **PDF export** — professional typography via WeasyPrint, with customizable accent color per user
- **Generation history** — last 50 generations with full snapshots of the CV and prompt used at generation time
- **Version restore** — roll back to any previous Master CV or prompt version directly from history
- **Multi-user** — isolated profiles per user; closed registration (admin-only account creation)
- **Persistent sessions** — JWT with automatic refresh, stays logged in for up to 30 days

## Tech Stack

**Backend**
- Python / FastAPI
- SQLAlchemy + SQLite
- Alembic (migrations)
- WeasyPrint (PDF generation)
- JWT authentication (bcrypt + python-jose)
- Anthropic API (Claude)

**Frontend**
- Vanilla JS SPA (no framework)
- Served as static files by FastAPI

**Infrastructure**
- Docker + Docker Compose
- Bitbucket Pipelines (CI/CD)
- Self-hosted on private cloud

## Project Structure

```
cv-tailor/
├── backend/
│   ├── app/
│   │   ├── core/          # Config, database, security
│   │   ├── models/        # SQLAlchemy models (User, CVProfile, GeneratedCV)
│   │   ├── routers/       # Auth, users, profile, CV generation, admin
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   └── main.py        # App entrypoint, static file serving, admin seed
│   ├── alembic/           # Database migrations
│   ├── Dockerfile
│   └── docker-entrypoint.sh
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── docker-compose.yml
```

## Data Model

```
users (1) ──── (1) cv_profiles   # One profile per user (PT/EN CV + base prompt)
  │
  └────────── (N) generated_cvs  # Full history with CV and prompt snapshots
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Anthropic API key

### Setup

```bash
git clone https://github.com/your-username/cv-tailor.git
cd cv-tailor
cp .env.example .env
```

Edit `.env` with your values:

```env
ANTHROPIC_API_KEY=your_key_here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=choose_a_password
SECRET_KEY=generate_a_random_secret
```

### Run

```bash
docker compose up -d
```

The app will be available at `http://localhost:8000`. An admin account is created automatically on first run.

## Usage

1. Log in with your admin credentials
2. Go to the **Master CV** tab and paste your complete CV in Markdown
3. Go to the **Job** tab and paste the full job description
4. Click **Generate →**
5. Use the adjustment field to refine the output conversationally
6. Export to PDF when ready

## Design Decisions

- **Closed registration** — no public sign-up; accounts are created by the admin. Designed for personal use and sharing with trusted people.
- **Centralized API key** — one Anthropic key on the server, shared across users. Cost per generation is ~$0.03–0.07 with Claude Sonnet.
- **SQLite** — sufficient for personal/small-group use; no external database dependency.
- **Snapshot history** — every generation saves a copy of the Master CV and prompt used, so you can track what version of your CV produced the best results.

## License

MIT