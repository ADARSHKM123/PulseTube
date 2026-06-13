# PulseTube — Automated YouTube Product Trend Analytics

PulseTube discovers hot, viral products on YouTube around the clock, then hands your team a single dashboard with **the data, the pictures, what people think about it, and the video script** — exactly the brief.

An automated pipeline runs every ~2 hours (8–12×/day) to:

1. **Discover** trending products via the YouTube Data API v3 (`search.list`) across high-velocity keywords *and* any custom products you track.
2. **Capture** view / like / comment counts as a **time series**, so you see momentum and pinpoint when a product started spiking.
3. **Mine comments** and score them with **VADER** sentiment (positive / neutral / negative).
4. **Pull transcripts** (the full video script) for every video it can.

All of it is quota-aware — the pipeline tracks YouTube API units against a daily ledger and halts gracefully before exhausting the free 10,000-unit limit.

---

## Screenshots / Features

- **Live Feed** — discovered products as cards: thumbnail, channel, views/likes/comments, a "spiking" velocity badge, and a sentiment glance bar.
- **Trends Table** — multi-column sortable table with deep filtering (min views, like ratio, velocity, sentiment thresholds, transcript availability, publish window) and **one-click CSV/Excel export** of the *entire filtered set*.
- **Detail View** — a split pane: time-series growth chart + headline metrics on the left; tabbed **Video Script** (searchable transcript) and **Audience Sentiment** (distribution donut + top comments) on the right. Plus a live "refresh this video now" button.
- **Keywords** — manage global trend keywords (pause/resume) and add your own custom products to the tracking rotation.
- **System** — pipeline status, the YouTube quota meter, full configuration, and a complete ingestion run history log.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS + Recharts + lucide-react |
| Backend | FastAPI (async) + SQLAlchemy 2.0 (async) + APScheduler |
| Sentiment | VADER (`vaderSentiment`) — free, in-process, no API cost |
| Transcripts | `youtube-transcript-api` (free) — pluggable to Supadata (paid) via one env var |
| Database | PostgreSQL (production) · SQLite (zero-config local default) |

> **Why FastAPI's scheduler instead of Celery?** APScheduler runs the 8–12 daily cycles inside the FastAPI event loop, so the whole backend is a single process — no broker to operate. The pipeline is structured in phases (search → metrics → sentiment → transcripts) that each commit independently, so a mid-run quota halt keeps everything gathered up to that point. Swapping to Celery later is straightforward: the entry point is one coroutine, `app.services.pipeline.run_pipeline`.

---

## Project Structure

```
pulsetube/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers: trends, videos, keywords, system
│   │   ├── services/       # youtube client, sentiment, transcripts, pipeline
│   │   ├── workers/        # APScheduler setup (the 8–12 daily runs)
│   │   ├── config.py       # env-driven settings
│   │   ├── database.py     # async engine + session
│   │   ├── models.py       # SQLAlchemy ORM (the 5 spec entities + run/quota logs)
│   │   ├── schemas.py      # Pydantic request/response models
│   │   ├── seed.py         # demo data generator
│   │   └── main.py         # app entry point + lifespan
│   ├── schema.sql          # PostgreSQL DDL (deliverable #1)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/      # ui/ (design system) + layout/ + features/
│   │   ├── features/        # feed, table, keywords, system pages
│   │   ├── context/         # toast + shared status providers
│   │   ├── hooks/           # data fetching, debounce, transcript search
│   │   └── lib/             # api client, formatters
│   ├── Dockerfile + nginx.conf
│   └── package.json
├── docker-compose.yml       # postgres + backend + frontend
└── README.md
```

---

## Getting Started

### Option A — Local dev (fastest, uses SQLite)

**Prerequisites:** Python 3.10+, Node 18+.

**1. Backend**

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then paste your YOUTUBE_API_KEY into .env
python -m app.seed            # OPTIONAL: load demo data to explore the UI immediately

python -m uvicorn app.main:app --reload --port 8000
```

**2. Frontend** (new terminal)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to the backend on port 8000.

### Option B — Docker (PostgreSQL, production-like)

```bash
cp backend/.env.example backend/.env     # set YOUTUBE_API_KEY
docker compose up --build
```

Open **http://localhost:8080**. PostgreSQL, the API+scheduler, and the nginx-served frontend all come up together.

---

## Getting a YouTube Data API key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or select one).
3. **APIs & Services → Library →** search **"YouTube Data API v3" →** Enable.
4. **APIs & Services → Credentials → Create Credentials → API key.**
5. Copy the key into `backend/.env` as `YOUTUBE_API_KEY=...` and restart the backend.

The free tier grants **10,000 units/day**. PulseTube defaults stay well under it (`search.list` = 100 units; batched `videos.list` = 1 unit per 50 videos; `commentThreads.list` = 1 unit). Tune `SEARCH_KEYWORDS_PER_RUN`, `PIPELINE_INTERVAL_MINUTES`, and `COMMENTS_MAX_PER_VIDEO` in `.env` to trade coverage against quota.

---

## Configuration (backend/.env)

| Variable | Default | Purpose |
|----------|---------|---------|
| `YOUTUBE_API_KEY` | — | **Required** for live ingestion |
| `DATABASE_URL` | SQLite file | Set to `postgresql+asyncpg://…` for Postgres |
| `PIPELINE_INTERVAL_MINUTES` | `120` | 120 = 12 runs/day (spec range 120–180) |
| `RUN_PIPELINE_ON_STARTUP` | `false` | Fire a run 20s after boot (burns quota) |
| `SEARCH_KEYWORDS_PER_RUN` | `3` | Keywords searched per cycle (round-robin) |
| `SEARCH_ORDER` | `viewCount` | `viewCount` \| `relevance` \| `date` \| `rating` |
| `SEARCH_PUBLISHED_WITHIN_DAYS` | `7` | Only surface recent (viral) uploads |
| `DAILY_QUOTA_LIMIT` | `10000` | Free-tier ceiling |
| `QUOTA_SAFETY_BUFFER` | `500` | Stop this far below the ceiling |
| `COMMENTS_MAX_PER_VIDEO` | `100` | Comment threads pulled for sentiment |
| `TRANSCRIPT_PROVIDER` | `youtube-transcript-api` | `youtube-transcript-api` (free) \| `supadata` (paid) |
| `SUPADATA_API_KEY` | — | Only if `TRANSCRIPT_PROVIDER=supadata` |

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/trends` | Paginated, filtered, sorted trends feed |
| `GET` | `/api/trends/export.csv` | CSV export honoring all active filters |
| `GET` | `/api/stats/overview` | Headline dashboard stats + top movers |
| `GET` | `/api/videos/{id}` | Full detail (metadata + latest sentiment) |
| `GET` | `/api/videos/{id}/history` | Time-series metric snapshots |
| `GET` | `/api/videos/{id}/transcript` | Full transcript text |
| `POST` | `/api/videos/{id}/refresh` | Live re-pull of one video (~2 units) |
| `GET/POST/PATCH/DELETE` | `/api/keywords` | Manage tracked keywords |
| `GET` | `/api/system/status` | Pipeline state, quota, config, totals |
| `GET` | `/api/system/runs` | Ingestion run history |
| `POST` | `/api/system/run` | Trigger an ingestion cycle now |

Interactive API docs are auto-generated at **http://localhost:8000/docs**.

---

## Database Schema

The five core entities from the spec, plus two operational tables:

- `tracked_keywords` — global + custom keywords, with search rotation state
- `videos_snapshot` — metadata, images, and denormalized latest metrics/sentiment for fast dashboard queries
- `video_metrics_history` — time-series of views/likes/comments per run
- `transcripts` — full-text video scripts
- `sentiment_analytics` — aggregate VADER distributions + sampled comments
- `pipeline_runs` — operational log of each ingestion cycle
- `quota_usage` — daily YouTube API unit ledger (Pacific-time keyed)

Full DDL is in [`backend/schema.sql`](backend/schema.sql). The app also creates these tables automatically on first boot, so the SQL file is optional for local SQLite.

---

## Error Handling & Resilience

- **Quota exhaustion** — reserved *before* each call (Google counts failures too); the run halts to `halted_quota` and resumes after the Pacific-midnight reset.
- **Missing transcripts** — recorded as `unavailable`/`error` with a backoff retry policy; the UI shows a clear message instead of breaking.
- **Disabled comments** — handled silently; a zero-row prevents re-spending quota every cycle.
- **Hidden like counts** — tolerated (some channels hide likes); ratio simply omitted.
- **Transient upstream 5xx** — retried with backoff before the phase records an error.
- **Overlapping runs** — a lock prevents the scheduler and manual triggers from running cycles concurrently.
```
