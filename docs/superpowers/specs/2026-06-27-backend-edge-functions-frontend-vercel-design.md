# Backend → Supabase Edge Functions, Frontend → Vercel

## Architecture

```
┌──────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Vercel  │────→│ Supabase Edge    │────→│ Supabase PG      │
│ Frontend │     │ Functions (API)  │     │ (Database)       │
│  (React) │     │  (TypeScript)    │     │                  │
└──────────┘     └──────────────────┘     └─────────────────┘
                       ↑                           ↑
                ┌──────┴──────────┐     ┌─────────┴──────────┐
                │ GitHub Actions   │     │ Supabase Studio    │
                │ (Daily Scrapers) │     │ (Admin Dashboard)  │
                │  (Python)        │     │                    │
                └─────────────────┘     └────────────────────┘
```

## Sections

### 1. Supabase Edge Functions (API layer, replaces Flask)

- Single `api` function at `supabase/functions/api/index.ts`
- Routes all requests internally: `GET /articles`, `GET /articles/:id`, `GET /articles/search`, etc.
- Uses `supabase-js` with service_role key for DB access
- CORS headers on all responses
- Scrape endpoints removed (GH Actions handles scraping autonomously)

### 2. Frontend on Vercel

- GitHub Pages config reverted: `base` removed, all paths use `/` not `/news/`
- `vercel.json` added for SPA rewrites
- `src/api.js` defaults to `https://ofzuqyqvhxibbaqxlmyn.functions.supabase.co/api`
- `.github/workflows/deploy.yml` deleted (Vercel auto-deploys from GitHub)
- Build: `npm run build` from `frontend/`, output `dist/`

### 3. Scrapers on GitHub Actions (daily cron)

- `.github/workflows/scrape.yml`: scheduled every 6 hours
- Standalone entrypoint `scrape_and_store.py`: creates `SupabaseDB`, runs `ScrapeOrchestrator`
- No Flask dependency
- 7 non-Playwright scrapers work; 6 Playwright scrapers gracefully fail on GH runners
- Secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`

## File Changes

### New files
- `supabase/functions/api/index.ts` — Edge Function router + all route handlers
- `supabase/functions/api/_shared/cors.ts` — CORS helper
- `.github/workflows/scrape.yml` — daily scraper cron
- `frontend/vercel.json` — SPA rewrites for Vercel

### Modified files
- `frontend/vite.config.js` — remove `base: '/news/'`
- `frontend/index.html` — revert paths from `/news/...` to `/...`
- `frontend/public/sw.js` — revert precache URLs from `/news/...` to `/...`
- `frontend/public/manifest.json` — revert `start_url` and icon paths
- `frontend/src/api.js` — default `BASE` to Edge Functions URL

### Deleted files
- `backend/Dockerfile` — no longer needed
- `backend/.dockerignore` — no longer needed
- `.github/workflows/deploy.yml` — replaced by Vercel auto-deploy

### Unchanged
- `backend/` directory kept as-is (scraper code still needed for GH Actions)
- `backend/supabase_db.py` — scrapers use this in GH Actions
- `backend/scraper_runner.py` — already has lazy imports for Playwright scrapers
- `backend/sources.yaml` — scraper configuration
- All test files
