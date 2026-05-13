"""
backend/apps/ingestion/orchestrator.py
────────────────────────────────────────
Purpose : The main coordinator for the daily ingestion batch job.
          This is what run_job.py calls. It runs every adapter for every
          active category, handles failures gracefully, and triggers AI
          processing after data collection is complete.

          Execution sequence:
            1. Load all active categories from DB (with their source adapter configs)
            2. For each category:
               a. For each configured source adapter:
                  - Create an IngestionRun record (status=running)
                  - Call adapter.fetch() to get raw items from the source API
                  - Call adapter.normalise() on each raw item → TrendItem
                  - Write TrendSnapshot + TrendItems to Postgres
                  - Update IngestionRun (status=success, items_fetched=N)
                  - On exception: update IngestionRun (status=failed, error_message=...)
                    log the error, and CONTINUE to the next adapter (FR-13)
            3. Phase 2+: for each category, call ai/client.py → Gemini summary
            4. Phase 3:  run cross-platform topic detection via embeddings
            5. Invalidate Redis cache for all affected categories (Phase 2)

          Key design principle (FR-13):
            Each adapter is isolated in a try/except. One failing source
            (e.g. Reddit rate-limits) never stops other sources from running.
            The last successful snapshot is always served to users.

Used by : run_job.py — calls orchestrator.run() as the job entrypoint
          apps/trends/views.py (IngestionTriggerView) — admin manual re-trigger

Phase    : 1 — Week 2 (Reddit + HN adapters only)
           Phase 2 — all 9 sources + Gemini AI processing
           Phase 3 — cross-platform detection + Redis cache invalidation
"""
# Implementation coming in Phase 1 Week 2


def run() -> int:
    """
    Main entrypoint called by run_job.py.
    Returns 0 on success, 1 if any adapter failed (for Cloud Run Job exit code).
    """
    # TODO Phase 1 Week 2: implement full orchestration loop
    return 0
