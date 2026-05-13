# Frontend — Next.js (Phase 1 Week 3)
#
# This directory will be initialised with:
#   npx create-next-app@latest . --typescript --tailwind --app --src-dir --import-alias "@/*"
#
# Scaffold is intentionally empty until Week 3 to keep the first commit focused
# on the backend pipeline and CI/CD.
#
# When initialised, the structure will be:
#   src/
#     app/                   Next.js App Router pages
#       page.tsx             Dashboard (/)
#       login/page.tsx       Login page
#       category/
#         [slug]/page.tsx    Category detail page
#     components/
#       TrendCard.tsx
#       CategorySidebar.tsx
#       SourceBadge.tsx
#       StaleIndicator.tsx
#     lib/
#       api.ts               API client (fetch wrappers for Django REST API)
#       auth.ts              JWT cookie helpers
#     types/
#       index.ts             Shared TypeScript types (TrendItem, Category etc.)
