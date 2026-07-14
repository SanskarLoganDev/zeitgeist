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
              Instructs Gemini to write a short category summary from the
              selected top items, naming specific trending topics without
              turning the output into a long explainer.

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
CATEGORY_SUMMARY_PROMPT = """
You are a concise trend analyst for Zeitgeist.

Write a short category summary for "{category_name}" using only the trend items below.

Requirements:
- Start with 1 sentence describing the overall trend.
- Then cover up to 5 listed top topics in 1-2 short sentences each.
- Be specific and name topics from the items.
- Do not mention source ranks, item numbers, scores, points, engagement, adds, or match ordering.
- Do not invent facts beyond the provided titles and source names.
- Do not write a Wikipedia-style explanation.
- Keep the whole response under 180 words.

Trend items:
{trend_items}
""".strip()
SENTIMENT_TAG_PROMPT = ""     # TODO Phase 3
DIGEST_EMAIL_PROMPT = ""      # TODO Phase 3
