"""
backend/apps/accounts/admin.py
────────────────────────────────
Purpose : Registers models from the accounts app with the Django admin panel.
          Allows staff users to view and manage User records at /admin/.

          Registers the custom User model and OTP audit models so staff can
          inspect local authentication state during development and production
          support.

Used by : Django admin panel — loaded automatically by Django at startup
          Staff users        — browse to /admin/ to manage users

Phase    : 1 — Week 1
"""
from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import EmailVerificationOTP, User

if TYPE_CHECKING:
    EmailVerificationOTPModelAdmin: TypeAlias = admin.ModelAdmin[EmailVerificationOTP]  # noqa: UP040
else:
    EmailVerificationOTPModelAdmin = admin.ModelAdmin


@admin.register(User)
class UserAdmin(BaseUserAdmin):  # type: ignore[type-arg]
    """
    Extends Django's built-in UserAdmin so the standard user management
    interface works correctly (change password, permissions, groups etc.)

    BaseUserAdmin already provides:
      - list_display: username, email, first_name, last_name, is_staff
      - search_fields: username, email
      - fieldsets for editing all standard fields

    Email verification is exposed as a readonly timestamp so staff can confirm
    whether a user completed the OTP flow.
    """

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "email_verified_at",
    )
    readonly_fields = ("email_verified_at",)


@admin.register(EmailVerificationOTP)
class EmailVerificationOTPAdmin(EmailVerificationOTPModelAdmin):
    list_display = ("sent_to_email", "user", "attempts", "expires_at", "consumed_at", "created_at")
    list_filter = ("consumed_at", "expires_at", "created_at")
    search_fields = ("sent_to_email", "user__email", "user__username")
    readonly_fields = (
        "user",
        "code_hash",
        "sent_to_email",
        "attempts",
        "expires_at",
        "consumed_at",
        "created_at",
        "sent_at",
    )
    ordering = ("-created_at",)
