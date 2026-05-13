"""
backend/apps/accounts/admin.py
────────────────────────────────
Purpose : Registers models from the accounts app with the Django admin panel.
          Allows staff users to view and manage User records at /admin/.

          In Phase 1 this is minimal — just enough to inspect users created
          via OAuth and debug auth issues during development.

Used by : Django admin panel — loaded automatically by Django at startup
          Staff users        — browse to /admin/ to manage users

Phase    : 1 — Week 3 (expand with UserCategoryPreference inline when models exist)
"""
from django.contrib import admin

# Phase 1 Week 3: register User model
# from .models import User
# admin.site.register(User)
