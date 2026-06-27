# News Aggregator — Design Doc

## Overview

A news website that scrapes articles from 1-3 sources, stores them in a database, and serves them via a REST API to a React SPA.

## Architecture

```
Scraper (bs4/playwright) ──▶ Flask API Server ──▶ SQLite DB
                                  │
                           APScheduler (periodic scrape)
                                  │
                            React SPA (Vite)
```

- **Backend:** Flask REST API + SQLite (via SQLAlchemy)
- **Frontend:** React with Vite, served separately
- **Scraping:** BeautifulSoup for static pages, Playwright for JS-rendered
- **Scheduling:** APScheduler runs scrapers every N minutes

## Data Model

### `sources`
| Column       | Type    | Notes                    |
|-------------|---------|--------------------------|
| id          | integer | PK                       |
| name        | text    | Display name             |
| url         | text    | RSS or homepage URL      |
| scraper_type| text    | Plugin identifier        |
| enabled     | boolean | Toggle on/off            |
| last_scraped| datetime| Last successful scrape   |

### `articles`
| Column       | Type    | Notes                              |
|-------------|---------|------------------------------------|
| id          | integer | PK                                 |
| source_id   | integer | FK → sources.id                    |
| title       | text    |                                    |
| url         | text    | UNIQUE — dedup key                 |
| summary     | text    | First ~300 chars or meta desc      |
| image_url   | text    | Lead image                         |
| author      | text    |                                    |
| published_at| datetime| From source, nullable              |
| scraped_at  | datetime| When we scraped it                 |
| content_hash| text    | MD5 of title+summary for change detection |

## API Endpoints

| Method | Path                  | Description                              |
|--------|-----------------------|------------------------------------------|
| GET    | /api/articles         | Paginated list, sorted by published_at DESC. Query params: `?source=1&page=1&per_page=20` |
| GET    | /api/articles/:id     | Single article detail                    |
| GET    | /api/sources          | List all enabled sources                 |
| POST   | /api/scrape           | Trigger manual scrape (all or ?source=1) |

## Scraping Pipeline

Each source has a scraper plugin function in `scrapers/<name>.py`:

```python
def scrape(soup: BeautifulSoup) -> list[dict]:
    # Returns: [{title, url, summary, image_url, author, published_at}, ...]
```

The scheduler:
1. Runs all enabled scrapers
2. For each article found, checks URL hash against DB
3. Inserts new, updates changed, skips unchanged
4. Logs per-source success/failure (one failing doesn't block others)

## Frontend (React + Vite)

**Routes:**
- `/` — Feed page with compact list of articles
- `/article/:id` — Full article detail

**Components:**
- `NavBar` — site header with title and source filter pills
- `ArticleCard` — thumbnail, title, source name, relative timestamp
- `SourceFilter` — horizontal pill list, click to filter by source
- `Feed` — main page, paginated list with "Load More" button

## Implementation Order

1. Project scaffold: Flask app, SQLite setup, React+Vite init
2. Database models and migrations
3. API endpoints (articles + sources)
4. Scraper plugins for 1-2 sources
5. APScheduler integration
6. React frontend: feed page, article card, source filter
7. Article detail page
8. Manual scrape trigger UI
