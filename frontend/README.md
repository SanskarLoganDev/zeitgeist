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
http://localhost:8000/api/v1
```

Override it in `.env.local`:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

To test the local frontend against the deployed Cloud Run backend, set:

```text
NEXT_PUBLIC_API_BASE_URL=https://zeitgeist-api-opowb5bpna-uc.a.run.app/api/v1
```

Then restart `npm run dev`. Next.js reads environment variables when the dev
server starts, not every time a page refreshes.

## Production container

The frontend can run on Cloud Run using the included Dockerfile. The API base
URL is passed at build time because `NEXT_PUBLIC_*` values are embedded into the
browser bundle.

```cmd
docker build ^
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://zeitgeist-api-opowb5bpna-uc.a.run.app/api/v1 ^
  -t zeitgeist-frontend .
```

Run locally:

```cmd
docker run --rm -p 3000:3000 zeitgeist-frontend
```

## Current scope

- Dashboard page with real Tech, Gaming, and News data from the backend.
- Category detail pages with paginated stored trends.
- Source filters on category pages.
- Source badge, score, source/platform links, and freshness status.
- Local session-auth screens for signup/login/logout and saved preferences.
- No AI summaries yet.
- No time-window filters yet.
