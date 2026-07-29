@echo off
REM ---------------------------------------------------------------------------
REM Zeitgeist Secret Manager bootstrap template
REM
REM Copy this file to secrets.bat and replace every placeholder with real values.
REM Do not commit secrets.bat. It is intentionally ignored by .gitignore.
REM
REM Prerequisites:
REM   1. gcloud is installed and authenticated.
REM   2. gcloud config set project YOUR_PROJECT_ID has been run, or PROJECT_ID
REM      below has been updated.
REM   3. Terraform has already created the Secret Manager secret containers.
REM ---------------------------------------------------------------------------

set PROJECT_ID=replace-with-your-gcp-project-id

echo Adding Django and database secrets...
echo replace-with-long-random-django-secret-key | gcloud secrets versions add django-secret-key --project=%PROJECT_ID% --data-file=-
echo replace-with-cloud-sql-db-password | gcloud secrets versions add db-password --project=%PROJECT_ID% --data-file=-

echo Adding source API keys...
echo replace-with-nytimes-api-key | gcloud secrets versions add nytimes-api-key --project=%PROJECT_ID% --data-file=-
echo replace-with-rawg-api-key | gcloud secrets versions add rawg-api-key --project=%PROJECT_ID% --data-file=-
echo replace-with-football-data-api-key | gcloud secrets versions add football-data-api-key --project=%PROJECT_ID% --data-file=-
echo replace-with-cricket-data-api-key | gcloud secrets versions add cricket-data-api-key --project=%PROJECT_ID% --data-file=-

echo Adding SMTP settings...
echo smtp.example.com | gcloud secrets versions add smtp-host --project=%PROJECT_ID% --data-file=-
echo replace-with-smtp-username-or-email | gcloud secrets versions add smtp-host-user --project=%PROJECT_ID% --data-file=-
echo replace-with-smtp-password-or-app-password | gcloud secrets versions add smtp-host-password --project=%PROJECT_ID% --data-file=-

echo Done. Verify secret versions in GCP Secret Manager before running CD.
