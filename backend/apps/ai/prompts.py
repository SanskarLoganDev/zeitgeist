"""
backend/apps/ai/prompts.py
────────────────────────────
Purpose : Stores all Gemini prompt templates as named string constants.
          Keeping prompts in one file makes them easy to find, version, and
          iterate on — you never have to hunt through business logic to find
          a prompt string.

          Prompts defined here:
            CATEGORY_SUMMARY_PROMPT
              Used by GeminiClient.generate_category_summary() (Phase 2).
              Instructs Gemini to write a 2-4 sentence trend summary for a
              category, naming specific trending topics and explaining why
              they matter. Designed to be specific, not generic filler.

            SENTIMENT_TAG_PROMPT (Phase 3)
              Used by GeminiClient.generate_sentiment_tags().
              Instructs Gemini to classify a batch of trend item titles as
              Positive (hype/excitement), Negative (controversy/criticism),
              or Neutral (informational/factual). Returns JSON.

            DIGEST_EMAIL_PROMPT (Phase 3)
              Used by GeminiClient.generate_digest_email().
              Instructs Gemini to write a personalised weekly email summary
              for a user, covering their subscribed categories in plain English.

          Prompt iteration note:
            These prompts will be tuned in Phase 2 Week 5 against real ingestion
            data. The initial versions here are starting points, not final copies.
            Good prompts require real data to test against.

Used by : apps/ai/client.py — imports and uses these constants in every Gemini call

Phase    : 2 — Week 5
"""
# Prompt templates will be written in Phase 2 Week 5
# once real ingestion data is available to test against.

CATEGORY_SUMMARY_PROMPT = ""  # TODO Phase 2 Week 5
SENTIMENT_TAG_PROMPT = ""     # TODO Phase 3
DIGEST_EMAIL_PROMPT = ""      # TODO Phase 3
