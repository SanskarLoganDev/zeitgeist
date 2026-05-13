"""
backend/apps/ai/client.py
───────────────────────────
Purpose : Wrapper around the Vertex AI SDK for all AI calls made by the application.
          Centralises all Gemini and embedding API interactions in one place so
          prompts, retry logic, and error handling are not scattered across the codebase.

          Classes:
            GeminiClient
              - generate_category_summary(category, trend_items) -> str
                  Calls Gemini with the CATEGORY_SUMMARY_PROMPT template.
                  Returns a 2-4 sentence plain-English trend summary.
                  Called once per category per ingestion run (Phase 2).

              - generate_sentiment_tags(trend_items) -> dict[item_id, str]
                  Batch-calls Gemini to classify multiple items as
                  Positive / Negative / Neutral in a single API call.
                  Called during ingestion for all items in a category (Phase 3).

              - generate_digest_email(user, category_summaries) -> str
                  Generates personalised weekly digest email content.
                  Called by the weekly scheduler job (Phase 3).

            EmbeddingClient (Phase 3)
              - embed(texts: list[str]) -> list[list[float]]
                  Calls Vertex AI text-embedding-004 model.
                  Returns a list of embedding vectors (one per input text).
                  Used by cross_platform.py for cosine similarity comparison.

          All methods are called ONLY from the ingestion job (run_job.py) or
          the weekly digest scheduler — never per user request (NFR-06).

Used by : apps/ingestion/orchestrator.py — GeminiClient for summaries + sentiment
          apps/ai/cross_platform.py      — EmbeddingClient for topic detection
          Weekly digest scheduler        — GeminiClient for email generation (Phase 3)

Phase    : 2 — Week 5 (GeminiClient)
           Phase 3 — EmbeddingClient
"""
# Implementation coming in Phase 2 Week 5
