# Deployment

This project runs on three providers:

| Component | Provider | Source of truth |
|-----------|----------|-----------------|
| Backend (FastAPI + agent, Docker) | Railway | `Dockerfile`, `railway.json` |
| Postgres (serverless) | Neon | `DATABASE_URL` env var on Railway |
| Frontend (Vite + React + proxy) | Vercel | `github.com/RagavRida/aria-landing` |

Live URLs live in the top-level `README.md` table.

---

## 1. Backend on Railway (Docker)

Railway builds the image from the repo-root `Dockerfile` and runs it as a web service. Config comes from `railway.json` (builder, healthcheck, restart policy).

**One-time setup**

1. Sign in to [railway.app](https://railway.app) with GitHub.
2. From this repo: `railway link` and pick a project (or `railway init`).
3. `railway add --service research-agent` to create the web service.
4. `railway service link research-agent` to make it the active target.

**Environment variables** (set via `railway variable --set K=V`)

| Key | Purpose |
|-----|---------|
| `LLM_PROVIDER` | `groq` (default live), `openrouter`, or `gemini`. See Section 4. |
| `GROQ_API_KEY` | required when `LLM_PROVIDER=groq` |
| `OPENROUTER_API_KEY` | required when `LLM_PROVIDER=openrouter` |
| `GOOGLE_API_KEY` | required when `LLM_PROVIDER=gemini` |
| `TAVILY_API_KEY` | always required — web/scholar/news search |
| `DATABASE_URL` | Postgres external connection string (see §2) |
| `JWT_SECRET` | any 32+ bytes; used to sign auth tokens |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_EXPIRES_MINUTES` | `10080` (7 days) |
| `PORT` | `8000` |

**Deploy**

```bash
railway up --service research-agent --ci
railway domain          # generate a public *.up.railway.app domain
```

The Dockerfile installs Python 3.11 + dependencies and runs `uvicorn main:app --host 0.0.0.0 --port $PORT`. Healthcheck path is `/api/health`.

---

## 2. Postgres on Neon

The `users` and `queries` tables live on a Neon free serverless Postgres project (region: us-east-1). Neon has no 30-day free-tier cliff and scales to zero when idle, which suits a demo workload.

**One-time setup**

1. Create a project at [console.neon.tech](https://console.neon.tech) — any region works, us-east-1 is closest to Railway's Oregon region.
2. Copy the database connection string. Neon offers a "pooled" URL with `-pooler` in the hostname and a "direct" URL without; for this stack use the **direct** URL to avoid PgBouncer's prepared-statement pitfalls with asyncpg.
3. Replace `sslmode=require` in the URL Neon gives you with `ssl=require`. asyncpg's URL parser understands `ssl=...` (psycopg's libpq-style `sslmode=...` throws `TypeError: unexpected keyword argument 'sslmode'`). Also drop `channel_binding=require` if present — it's not an asyncpg option.
4. `railway variable set "DATABASE_URL=postgresql://…/neondb?ssl=require"` on the Railway service, then `railway redeploy`.

Schema is auto-created on first boot — `init_db()` in `db/database.py` runs `Base.metadata.create_all` against whatever `DATABASE_URL` points to, so a fresh Neon project comes up populated after the first request.

**Migration from an old Postgres** (needed if you're moving off a previous provider):

```bash
# dump — match your server's major version with the client
/opt/homebrew/opt/postgresql@18/bin/pg_dump \
  -h <old-host> -U <old-user> <old-db> \
  --no-owner --no-privileges --clean --if-exists > aria.sql

# restore
PGPASSWORD=<pw> psql "postgresql://…neondb" -v ON_ERROR_STOP=1 -f aria.sql
```

---

## 3. Frontend on Vercel

The landing + research UI live in the sibling repo at `github.com/RagavRida/aria-landing`. Vercel auto-detects Vite and builds from the repo root.

**Env vars on Vercel**: none required. The app uses same-origin `/api/*` requests; `vercel.json` rewrites them to the Railway backend:

```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://<your-railway-domain>/api/:path*" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

This keeps JWT handling same-origin and sidesteps local-DNS resolvers that refuse `*.up.railway.app`.

**Deploy**: `vercel --prod` from `~/aria-landing`.

---

## 4. Swapping LLM providers at runtime

No redeploy needed:

```bash
# See providers the running service reports as available
curl https://<your-vercel-domain>/api/models

# Hot-swap without redeploying
curl -X POST https://<your-vercel-domain>/api/models/switch \
  -H 'Content-Type: application/json' \
  -d '{"provider":"openrouter","model":"meta-llama/llama-3.3-70b-instruct:free"}'
```

OpenRouter's `:free` catalog rotates — if a model ID starts returning `404 No endpoints found`, flip `LLM_PROVIDER=groq` on Railway (or pick a currently-live OpenRouter model) and redeploy. Details in `ANALYSIS.md §3.4`.

---

## 5. Smoke test

Replace `<URL>` with the Vercel production URL.

```bash
curl -s <URL>/api/health                           # -> {"status":"healthy", ...}
curl -s <URL>/api/models | jq .active_provider      # -> current LLM provider

EMAIL="smoke_$(date +%s)@example.com"
TOKEN=$(curl -s -X POST <URL>/api/auth/signup \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"hunter2hunter2\",\"name\":\"Smoke\"}" \
  | jq -r .token)

curl -s -H "Authorization: Bearer $TOKEN" <URL>/api/history   # -> []
```

If all three succeed you have Vercel → Railway → Postgres wired end-to-end.
