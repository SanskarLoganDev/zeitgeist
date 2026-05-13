"""
backend/apps/ingestion/adapters/pubmed.py
───────────────────────────────────────────
Purpose : Fetches recently published and highly cited papers from PubMed
          using the NCBI E-utilities API. Used for Health and Research categories
          to provide authoritative medical and life science signal.

          API used:
            esearch.fcgi  — search for recent papers by topic
            efetch.fcgi   — fetch full metadata for result IDs

          Rate limit: 10 requests/second with an API key (much lower without).
          Credential: PUBMED_API_KEY from Secret Manager.

          Normalised fields:
            title        → paper title
            url          → https://pubmed.ncbi.nlm.nih.gov/{pmid}/
            source       → "pubmed"
            score        → citation count or recency rank
            score_label  → "citations"

Used by : apps/ingestion/orchestrator.py — instantiated for categories where
            CategorySourceConfig has source="pubmed"

Phase    : 2 — Week 5
"""
# Implementation coming in Phase 2 Week 5
