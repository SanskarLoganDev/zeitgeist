# Frontend — Next.js

Phase 1 Week 3 frontend for Zeitgeist.

The app runs on localhost and reads real trend data from the Django REST API.

## Setup

```cmd
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Open:

```text
http://localhost:3000
```

By default, the frontend calls:

```text
http://127.0.0.1:8000/api/v1
```

Override it in `.env.local`:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

To test the local frontend against the deployed Cloud Run backend, set:

```text
NEXT_PUBLIC_API_BASE_URL=https://zeitgeist-api-opowb5bpna-uc.a.run.app/api/v1
```

Then restart `npm run dev`. Next.js reads environment variables when the dev
server starts, not every time a page refreshes.

## Current scope

- Dashboard page with real Hacker News data.
- Category detail page with 10-20 items.
- Source badge, score, external link, HN discussion link, and freshness status.
- No login/auth yet.
- No AI summaries yet.
- No source/time filters yet.
