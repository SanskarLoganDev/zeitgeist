"""
backend/apps/accounts/models.py
────────────────────────────────
Purpose : Defines the User model for the entire application.
          Extends Django's AbstractUser so we keep all built-in auth behaviour
          (password hashing, permissions, sessions) while adding our own fields.

          Week 1 stub — contains only the bare minimum so that:
            1. AUTH_USER_MODEL = "accounts.User" in settings/base.py resolves
            2. Django can create the initial migration and boot successfully
            3. pytest + CI pass without errors

          Week 3 additions (do not add until OAuth views are being built):
            - google_id       : unique ID from Google OAuth response
            - avatar_url      : profile picture URL from Google
            - onboarding_done : whether user completed interest selection (Phase 3)

          UserCategoryPreference (the join table between User and Category)
          is also added in Week 3 when the Category model exists to FK into.

Used by : config/settings/base.py   — AUTH_USER_MODEL = "accounts.User"
          apps/accounts/views.py    — creates/fetches User on OAuth callback (Week 3)
          apps/categories/models.py — UserCategoryPreference FK to User (Week 3)
          apps/trends/views.py      — reads user preferences to filter dashboard (Week 3)
          Django admin              — User visible and manageable at /admin/
          apps/accounts/authentication.py — reads User from DB per request (Week 3)

Phase    : 1 — Week 1 (stub, enough for migrations and CI to pass)
           Phase 1 — Week 3 (full implementation: google_id, avatar_url, preferences)
"""
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model — Week 1 stub.

    Inherits all standard Django fields:
      username, email, first_name, last_name,
      is_staff, is_active, date_joined, last_login,
      password (hashed), groups, user_permissions.

    Why AbstractUser and not AbstractBaseUser?
      AbstractUser gives us the full Django auth system for free —
      admin integration, permission framework, login views — without
      reimplementing any of it. AbstractBaseUser is for cases where you
      want to completely replace the auth system. We don't.

    Why a custom User model at all?
      Django's documentation strongly recommends always starting with a
      custom User model, even if it's empty like this. Changing AUTH_USER_MODEL
      after the first migration is very painful (requires wiping the database).
      Starting with a custom model now means Week 3 fields (google_id, avatar_url)
      can be added with a simple migration — no pain.

    Additional fields added in Week 3:
      google_id       = models.CharField(max_length=128, unique=True, null=True)
      avatar_url      = models.URLField(blank=True, default="")
      onboarding_done = models.BooleanField(default=False)
    """

    class Meta:
        db_table = "accounts_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.email or self.username
