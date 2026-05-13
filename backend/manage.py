"""
backend/manage.py
─────────────────
Purpose : Django's command-line utility for development tasks.
          Used to run the dev server, apply migrations, create superusers,
          run management commands, and run the test suite locally.

Used by : Developer directly — never called in production or by any other file.
          Cloud Run uses gunicorn (config/wsgi.py) in production.
          CI pipeline calls: python manage.py migrate  (before tests)
          You call:          python manage.py runserver
                             python manage.py createsuperuser
                             python manage.py makemigrations
                             python manage.py migrate

NOT used by : Dockerfile (uses gunicorn), run_job.py (uses django.setup() directly)
"""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
