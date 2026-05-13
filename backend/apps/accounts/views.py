"""
backend/apps/accounts/views.py
────────────────────────────────
Purpose : Handles all authentication flows for the application.

          POST /api/v1/auth/google/
            - Receives the Google OAuth authorisation code from the Next.js frontend
            - Exchanges it with Google for an ID token
            - Decodes the token to get the user's Google ID, email, name, and avatar
            - Creates or retrieves the User record in Postgres
            - Issues a signed JWT and stores it in an HTTP-only cookie
            - Returns the user profile to the frontend

          POST /api/v1/auth/logout/
            - Clears the JWT cookie

          GET /api/v1/auth/me/
            - Returns the current authenticated user's profile and preferences
            - Called by Next.js on every page load to restore auth state

Used by : apps/accounts/urls.py — routes requests to these views
          Next.js frontend       — calls these endpoints for login/logout/session restore

Phase    : 1 — Week 3
"""
# Implementation coming in Phase 1 Week 3
