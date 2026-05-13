"""
backend/apps/trends/admin.py
──────────────────────────────
Purpose : Registers trend-related models in the Django admin panel.
          The most important admin registration in the whole project — this is
          where staff can see exactly what data the ingestion job produced
          and debug any issues (FR-19).

          What admins can see here:
            - IngestionRun log: every run, its status, items fetched, any errors
            - TrendSnapshot: the snapshot records per category per day
            - TrendItem: individual trending posts, with source, score, URL

Used by : Django admin panel — loaded automatically by Django at startup
          Staff users — use this daily to verify ingestion health

Phase    : 1 — Week 2 (register as soon as models exist)
"""
from django.contrib import admin

# Phase 1 Week 2:
# from apps.ingestion.models import IngestionRun
# from .models import TrendSnapshot, TrendItem
# admin.site.register(IngestionRun)
# admin.site.register(TrendSnapshot)
# admin.site.register(TrendItem)
