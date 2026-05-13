"""
backend/config/wsgi.py
──────────────────────
Purpose : WSGI application entrypoint for the Django API server.
          WSGI (Web Server Gateway Interface) is the standard Python interface
          between a web server (gunicorn) and a Django application.

          When gunicorn starts inside the Docker container, it imports this file
          and calls the `application` object to handle every incoming HTTP request.

Used by : Dockerfile CMD — gunicorn config.wsgi:application
          This is the production entrypoint for all API traffic.

NOT used by : run_job.py (ingestion job), manage.py (dev CLI), or tests.
              Tests use Django's test client directly, bypassing WSGI entirely.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
application = get_wsgi_application()
