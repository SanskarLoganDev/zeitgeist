"""
backend/apps/ai/cross_platform.py
───────────────────────────────────
Purpose : Detects when the same topic is trending across multiple platforms
          simultaneously — e.g. a new AI model that appears in r/MachineLearning
          on Reddit, in an arXiv paper, AND in an HN top story on the same day.

          This is the "trending everywhere" feature (FR-10, FR-15).

          How it works:
            1. After ingestion completes, collect all TrendItem titles for a
               category, grouped by source.
            2. Call EmbeddingClient.embed() to get a vector for each title.
            3. Compute pairwise cosine similarity between items from DIFFERENT sources.
            4. Items from 2+ sources with similarity > 0.82 are considered the
               same topic — write a CrossPlatformTopic record.
            5. The record is read by the dashboard API and surfaced as a
               "trending everywhere" badge at the top of the category page.

          Threshold of 0.82 was chosen to avoid false positives (e.g. two unrelated
          articles that happen to share common tech words). This will be tuned
          based on real data in Phase 3.

          Why this matters:
            A single Reddit post might be noise. The same topic appearing on Reddit,
            HN, and arXiv simultaneously is a much stronger signal that something
            genuinely significant is happening.

Used by : apps/ingestion/orchestrator.py — called as the last step after all
            adapters have run and AI summaries have been generated.

Phase    : 3
"""
# Implementation coming in Phase 3
