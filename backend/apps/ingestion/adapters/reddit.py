"""
DEFERRED: Reddit is not currently an active Zeitgeist source.

Reason:
As of 2026, Reddit API access for personal scripts is gated by approval and is
not reliably available for this project. Do not wire Reddit into seed data,
models, or the orchestrator until API access is explicitly verified first.

If Reddit becomes viable later, reintroduce this adapter only after:
  1. API access is approved and credentials are available.
  2. A live fetch test confirms the API response shape.
  3. Tests cover missing/invalid credentials and source failure isolation.
"""
