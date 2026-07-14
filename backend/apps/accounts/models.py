"""
backend/apps/accounts/models.py
────────────────────────────────
Purpose : Defines the User model for the entire application.
          Extends Django's AbstractUser so we keep all built-in auth behaviour
          (password hashing, permissions, sessions) while adding our own fields.

Used by : config/settings/base.py   — AUTH_USER_MODEL = "accounts.User"
          apps/accounts/views.py    — signup, signin, email OTP, password reset
          apps/categories/models.py — UserCategoryPreference FK to User
          apps/trends/views.py      — reads preferences for dashboard filtering
          Django admin              — User visible and manageable at /admin/
          Django session auth       — reads User from DB per request

Phase    : 1 — custom user and session auth
           Phase 2 — email verification and password reset OTP
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model used by Django's built-in session authentication.

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
      Starting with a custom model now lets us add product-specific auth fields
      with normal migrations instead of replacing Django's default user later.
    """

    class Meta:
        db_table = "accounts_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.email or self.username

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    email_verified_at = models.DateTimeField(null=True, blank=True)


class EmailVerificationOTP(models.Model):
    """One-time email verification code for a user registration."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_otps",
    )
    code_hash = models.CharField(max_length=128)
    sent_to_email = models.EmailField()
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_email_verification_otp"
        verbose_name = "email verification OTP"
        verbose_name_plural = "email verification OTPs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["sent_to_email", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.sent_to_email} @ {self.created_at:%Y-%m-%d %H:%M}"


class PasswordResetOTP(models.Model):
    """One-time password reset code for a user account."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_otps",
    )
    code_hash = models.CharField(max_length=128)
    sent_to_email = models.EmailField()
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_password_reset_otp"
        verbose_name = "password reset OTP"
        verbose_name_plural = "password reset OTPs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["sent_to_email", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.sent_to_email} @ {self.created_at:%Y-%m-%d %H:%M}"
