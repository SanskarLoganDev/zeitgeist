"""
backend/apps/accounts/models.py
────────────────────────────────
Purpose : Defines the User model for the entire application.
          Extends Django's AbstractUser so we keep all built-in auth behaviour
          (password hashing, permissions, sessions) while adding our own fields:
          - google_id       : the unique ID from Google OAuth — used to identify
                              returning users without storing passwords
          - avatar_url      : profile picture URL from Google's OAuth response
          - onboarding_done : whether the user has completed the interest selection
                              flow (FR-02, Phase 3)

          Also defines UserCategoryPreference — the join table between a user
          and the categories they have selected on their dashboard.

Used by : config/settings/base.py  — AUTH_USER_MODEL = "accounts.User"
          apps/accounts/views.py   — creates/fetches User on OAuth callback
          apps/categories/models.py — UserCategoryPreference FK to User
          apps/trends/views.py     — reads user.preferences to filter dashboard
          Django admin              — User is registered and manageable there
          All JWT authentication    — apps/accounts/authentication.py reads User from DB

Phase    : 1 — Week 3 (implement fully when OAuth views are built)
           Stub created in Week 1 so migrations can reference AUTH_USER_MODEL.
"""
# Implementation coming in Phase 1 Week 3
