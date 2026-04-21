# Deployment

This project runs on three providers:

| Component | Provider | Source of truth |
|-----------|----------|-----------------|
| Backend (FastAPI + agent, Docker) | Railway | `Dockerfile`, `railway.json` |
| Postgres (managed) | Render | `render.yaml` (`databases:` block only) |
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

## 2. Postgres on Render

Render's free managed Postgres hosts the `users` and `queries` tables. The `render.yaml` blueprint declares it so it can be reprovisioned from scratch:

```yaml
databases:
  - name: aria-db
    plan: free
    databaseName: aria
    user: aria
```

One-click provision: connect this repo in the Render dashboard and deploy the blueprint. Grab the external connection string from the database's dashboard page and set it as `DATABASE_URL` on the Railway service.

> **⚠️ Render free Postgres expires 30 days after creation.** The live
> database was provisioned on 2026-04-20 and will hit `status: expired`
> on **2026-05-20**. After that date the backend will 500 on any
> authed route until `DATABASE_URL` is pointed elsewhere. Migration
> options in order of effort:
>
> 1. **Extend on Render** — upgrade the same database to a paid plan
>    (~$7/mo) from the Render dashboard; no URL change needed.
> 2. **Move to Railway Postgres** — `railway add --database postgres`
>    (requires Railway paid plan), copy the new `DATABASE_URL`, dump
>    + restore with `pg_dump | psql`, then `railway variable --set`.
> 3. **Any external Postgres** — Neon, Supabase, or an old DO
>    droplet all work; just update `DATABASE_URL`.
>
> The schema is two tables (`users`, `queries`); `init_db()` on
> startup will recreate them in a fresh database if you don't care
> about preserving signups.

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
