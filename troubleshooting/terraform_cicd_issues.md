# Terraform & CI/CD Troubleshooting Log

**Project:** Zeitgeist
**Stack:** Django + GCP + GitHub Actions + Terraform
**Last updated:** 2026-07-29

---

## T-01 — Variables not allowed in variable defaults

**Error**
```
Variables may not be used here.
on modules\cloud_sql\variables.tf line 12, in variable "vpc_network":
  default = "projects/${var.project_id}/global/networks/default"
```

**Cause**
Terraform does not allow referencing other variables inside a variable's `default` value. Defaults must be static strings.

**Fix**
Remove the variable entirely if it is no longer needed. If needed, pass the computed value from the root module instead of using a default.

---

## T-02 — Cloud SQL db-f1-micro invalid tier for ENTERPRISE_PLUS

**Error**
```
Error 400: Invalid request: Invalid Tier (db-f1-micro) for (ENTERPRISE_PLUS) Edition.
```

**Cause**
GCP now defaults new Cloud SQL instances to `ENTERPRISE_PLUS` edition, which requires `db-perf-optimized-N-*` tier names. `db-f1-micro` only works with `ENTERPRISE` edition.

**Fix**
Explicitly set `edition = "ENTERPRISE"` in the Cloud SQL settings block.

```hcl
settings {
  tier    = "db-f1-micro"
  edition = "ENTERPRISE"
}
```

---

## T-03 — Cloud SQL creation timeout (Terraform loses track of pending resource)

**Error**
```
Error waiting for Create Instance:
```
Followed on next apply by:
```
Error 409: The Cloud SQL instance already exists.
```

**Cause**
Cloud SQL takes 5–10 minutes to provision. Terraform's default timeout was shorter, so it gave up — but GCP continued creating the instance. On the next `apply`, Terraform tried to create it again and GCP rejected it as a duplicate.

**Fix**
1. Import the existing instance into Terraform state:
```cmd
terraform import module.cloud_sql.google_sql_database_instance.main zeitgeist-pg
```
2. Add a `timeouts` block to prevent future timeouts:
```hcl
timeouts {
  create = "20m"
  update = "20m"
  delete = "20m"
}
```

---

## T-04 — Cloud Run deletion_protection blocks terraform destroy

**Error**
```
Error: cannot destroy service without setting deletion_protection=false
```

**Cause**
The GCP Terraform provider defaults `deletion_protection = true` on Cloud Run v2 services and jobs. `terraform destroy` fails without explicitly disabling it.

**Fix**
Set `deletion_protection = false` on both resources:
```hcl
resource "google_cloud_run_v2_service" "api" {
  deletion_protection = false
}

resource "google_cloud_run_v2_job" "ingest" {
  deletion_protection = false
}
```

If resources already exist with protection enabled, disable via gcloud then re-apply:
```cmd
gcloud run services delete zeitgeist-api --region us-central1 --project PROJECT_ID --quiet
gcloud run jobs delete zeitgeist-ingest --region us-central1 --project PROJECT_ID --quiet
terraform apply
```

---

## T-05 — Cloud Run placeholder image fails startup probe

**Error**
```
STARTUP HTTP probe failed 3 times consecutively for container "hello-1" on port 8000
```

**Cause**
Google's hello-world placeholder image (`us-docker.pkg.dev/cloudrun/container/hello`) runs on port 8080, not port 8000. The startup probe configured for Django's `/api/v1/health/` on port 8000 fails against the placeholder.

**Fix**
Remove the `startup_probe` block from the Terraform Cloud Run service definition. The probe is added by the CD pipeline when the real Django image is deployed. The placeholder runs fine without a probe.

---

## T-06 — Secret Manager "not found" after terraform destroy

**Error**
```
Secret projects/.../secrets/django-secret-key/versions/latest was not found
```

**Cause**
`terraform destroy` deletes Secret Manager resources including all stored secret versions. On the next `terraform apply`, empty secret slots are recreated but Cloud Run fails to start because the values are gone.

**Fix**
Terraform must not attach Cloud Run secret refs during the first bootstrap apply.
Run `terraform apply` first to create Secret Manager shells and placeholder Cloud
Run resources with no secret env vars, then run `infra\secrets.bat`, then let CD
attach populated secrets to the real Cloud Run revision with `--set-secrets`.

**Prevention**
Use scale-to-zero instead of `terraform destroy` for daily cost savings:
```cmd
gcloud run services update zeitgeist-api --min-instances=0 --region us-central1 --project PROJECT_ID
```

---

## T-07 — IAM permission denied on secret at Cloud Run creation

**Error**
```
Permission denied on secret: projects/.../secrets/django-secret-key/versions/latest
for Revision service account zeitgeist-app@...
```

**Cause**
GCP IAM changes are eventually consistent. Terraform created the Cloud Run service in parallel with the IAM `secretAccessor` role grant before the permission propagated.

**Fix**
Add a `null_resource` with a 60-second sleep between IAM grants and Cloud Run creation:
```hcl
resource "null_resource" "iam_propagation_delay" {
  triggers = { secret_accessor = google_project_iam_member.secret_accessor.id }
  provisioner "local-exec" {
    command     = "powershell -Command Start-Sleep -Seconds 60"
    interpreter = ["cmd", "/C"]
  }
}

resource "google_cloud_run_v2_service" "api" {
  depends_on = [null_resource.iam_propagation_delay]
}
```

---

## T-08 — undeclared variable warning in terraform.tfvars

**Warning**
```
The root module does not declare a variable named "allowed_hosts"
```

**Cause**
Variables used in `terraform.tfvars` must be declared in the root `variables.tf`. Child module variables are not automatically available at the root level.

**Fix**
Declare the variable in `infra/variables.tf` and pass it through the module block in `infra/main.tf`:
```hcl
# variables.tf
variable "allowed_hosts" {
  type    = string
  default = "localhost"
}

# main.tf — inside module "cloud_run" block
allowed_hosts = var.allowed_hosts
```

---

## CI-01 — CD pipeline: docker push permission denied

**Error**
```
denied: Permission 'artifactregistry.repositories.uploadArtifacts' denied
```

**Cause**
The service account used by GitHub Actions was missing `roles/artifactregistry.writer`. This role was omitted from the initial Terraform IAM setup.

**Fix**
Grant immediately via gcloud:
```cmd
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:SA_EMAIL" --role="roles/artifactregistry.writer"
```

Add permanently to Terraform:
```hcl
resource "google_project_iam_member" "artifact_registry_writer" {
  role   = "roles/artifactregistry.writer"
  member = "serviceAccount:${google_service_account.app.email}"
}
```

---

## CI-01b — CD pipeline: iam.serviceAccounts.getAccessToken denied before docker push

**Error**
```
Unable to acquire impersonated credentials
Permission 'iam.serviceAccounts.getAccessToken' denied
denied: Unauthenticated request. Unauthenticated requests do not have permission
"artifactregistry.repositories.uploadArtifacts"
```

**Cause**
The Artifact Registry writer role was present on the service account, but GitHub
Actions could not impersonate that service account through Workload Identity
Federation. After `terraform destroy`, the `zeitgeist-app` service account is
recreated and any service-account-level WIF IAM binding must also be recreated.

Without `roles/iam.workloadIdentityUser` on the service account for the GitHub
repository principal set, `google-github-actions/auth` can start the WIF flow but
cannot mint an access token. Docker then appears unauthenticated, so the final
push error mentions Artifact Registry upload permission even though the root
problem is impersonation.

**Fix**
Manage the GitHub WIF impersonation binding in Terraform:
```hcl
data "google_project" "current" {
  project_id = var.project_id
}

resource "google_service_account_iam_member" "github_wif_user" {
  service_account_id = google_service_account.app.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/github-pool/attribute.repository/SanskarLoganDev/zeitgeist"
}
```

Then apply and rerun the failed GitHub Actions CD workflow:
```cmd
cd infra
terraform apply
```

---

## CI-02 — CD pipeline: iam.serviceaccounts.actAs denied on migration job

**Error**
```
Permission 'iam.serviceaccounts.actAs' denied on service account zeitgeist-app@...
```

**Cause**
When `gcloud run jobs create --service-account SA` is called, GCP requires the caller to have `iam.serviceAccountUser` on the target service account — even when the caller and target are the same account.

**Fix**
Grant `serviceAccountUser` on the service account to itself:
```cmd
gcloud iam service-accounts add-iam-policy-binding SA_EMAIL --member="serviceAccount:SA_EMAIL" --role="roles/iam.serviceAccountUser" --project PROJECT_ID
```

Add permanently to Terraform using `google_service_account_iam_member` (not `google_project_iam_member`):
```hcl
resource "google_service_account_iam_member" "self_act_as" {
  service_account_id = google_service_account.app.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.app.email}"
}
```

---

## CI-03 — CD pipeline: insufficient Cloud Run permissions

**Cause**
`roles/run.developer` does not cover all operations in `cd.yml` — specifically `gcloud run jobs create --execute-now` requires additional permissions.

**Fix**
Replace `roles/run.developer` with `roles/run.admin` which is a superset and covers all Cloud Run operations used in the CD pipeline:
```hcl
resource "google_project_iam_member" "cloud_run_admin" {
  role   = "roles/run.admin"
  member = "serviceAccount:${google_service_account.app.email}"
}
```

---

## CI-04 — GitHub Actions Node.js 20 deprecation warnings

**Warning**
```
Node.js 20 actions are deprecated. Actions will be forced to run with Node.js 24
by default starting June 2nd, 2026.
```

**Cause**
`google-github-actions/auth@v2` declared `node20` as its runtime.

**Fix**
1. Upgrade `google-github-actions/auth` from `@v2` to `@v3`
2. Add `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` at workflow level as GitHub's recommended opt-in:
```yaml
env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true
```

---

## Complete IAM role checklist for zeitgeist-app service account

Run after every `terraform destroy` if not using scale-to-zero:

| Role | Type | Purpose |
|---|---|---|
| `secretmanager.secretAccessor` | Project | Read secrets at runtime |
| `cloudsql.client` | Project | Connect to Postgres via Auth Proxy |
| `logging.logWriter` | Project | Write logs to Cloud Logging |
| `aiplatform.user` | Project | Call Vertex AI (Phase 2) |
| `artifactregistry.writer` | Project | Push Docker images from CD |
| `run.admin` | Project | All Cloud Run operations in CD |
| `iam.serviceAccountUser` | SA-level | Create Cloud Run Jobs that run as itself |

All 7 roles are managed by Terraform in `infra/modules/cloud_run/main.tf` and recreated automatically on every `terraform apply`.

---

*Auto-updated during development. New issues added as they are encountered.*

---

## CI-05 — Migration job crashes with CORS system check error

**Error**
```
?: (corsheaders.E013) Origin '' in CORS_ALLOWED_ORIGINS is missing scheme or netloc
```

**Cause**
Two root causes working together:

1. `os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")` on an empty string produces `[""]` — a list containing one empty string. Django's CORS system check sees `""` as an invalid origin and crashes before migrations run.

2. The migration job in `cd.yml` did not set `CORS_ALLOWED_ORIGINS` or `ALLOWED_HOSTS` in `--set-env-vars`, so Django received empty strings for both.

**Fix — two parts:**

Part 1 — Filter empty strings in `production.py`:
```python
# Wrong — produces [""] when env var is empty
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")

# Correct — filter() removes empty strings
CORS_ALLOWED_ORIGINS = list(filter(None, os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")))
ALLOWED_HOSTS = list(filter(None, os.environ.get("ALLOWED_HOSTS", "").split(",")))
```

Part 2 — Add both vars to the migration job in `cd.yml`:
```yaml
--set-env-vars "...,ALLOWED_HOSTS=localhost,CORS_ALLOWED_ORIGINS=http://localhost:3000"
```

**Lesson**
Django runs ALL system checks at startup before executing any management command including `migrate`. Any invalid setting crashes the process before the command runs. Always set all required env vars on migration jobs, not just DB credentials.

---

## CI-06 — Cloud Run startup probe times out after deployment

**Error**
```
Container failed to become healthy. Startup probes timed out after 4m
```

**Cause**
Cloud Run's default startup probe checks port 8080. Our Django app runs on port 8000 via gunicorn (`--bind 0.0.0.0:8000`). Cloud Run was probing the wrong port, getting no response, and marking the container unhealthy.

**Fix**
Add `--port 8000` to the `gcloud run services update` command in `cd.yml`:
```yaml
gcloud run services update zeitgeist-api \
  --image ... \
  --port 8000 \        ← tells Cloud Run our app is on port 8000
  --region ...
```

**Prevention**
Always match the port in `--bind` inside the Dockerfile CMD with the `--port` flag in the deploy command. Cloud Run defaults to 8080 — any app not running on 8080 must explicitly declare its port.

---

## Design Decision — Secret Manager population outside Terraform

**Decision**
Terraform creates Secret Manager resource shells only. Secret values are populated
manually via `infra\secrets.bat` after every `terraform apply`. This is intentional.

**Why Terraform does not store secret values**
Terraform writes everything it manages into `terraform.tfstate` — a plain JSON file.
If Terraform stored secret values (via `google_secret_manager_secret_version`), those
values would appear in plaintext in the state file. If the state file were ever committed
to Git, uploaded to a shared location, or accessed by an unauthorised party, all
credentials would be exposed.

Using `google_secret_manager_secret` (shell only) keeps the state file clean.
Values are written directly to GCP's encrypted storage via `gcloud secrets versions add`
and never touch any local file except `secrets.bat` which is gitignored.

**Why Cloud Run reads secrets at startup, not on demand**
Cloud Run injects secrets as environment variables before the container process starts.
Environment variables are set once at process start by the OS — there is no mechanism
to inject new env vars into an already-running process. Django reads `os.environ["DJANGO_SECRET_KEY"]`
at settings load time (import time), which happens during container startup.

For the Cloud Run Job (ingestion), "startup" and "when the scheduler calls it" are
the same event — the scheduler causes a fresh container to start, secrets are injected,
the job runs, the container exits. There is no idle container waiting for the scheduler.

**Why this differs from production**
In production, `terraform destroy` is almost never run. Infrastructure is permanent.
Secrets are populated once during initial project setup and never wiped.
The `secrets.bat` bootstrap step exists only because we destroy and recreate
infrastructure repeatedly during development to save cost.

In production, secret population would be automated as part of the CD pipeline
(Option 3) — the pipeline reads values from a secure store (e.g. GitHub Secrets)
and calls `gcloud secrets versions add` automatically on first deploy.

**Correct order every time after terraform destroy**
```
1. cd infra && terraform apply     ← creates empty secret shells and placeholder Cloud Run with no secret refs
2. Copy terraform output api_url hostname into infra\terraform.tfvars allowed_hosts
3. cd .. && infra\secrets.bat      ← adds secret versions to the shells
4. cd infra && terraform apply     ← updates non-secret Cloud Run env vars such as ALLOWED_HOSTS
5. cd .. && git push origin main   ← CD deploys real images and attaches secrets with --set-secrets
```

---

## T-09 — secrets.bat fails with NOT_FOUND after terraform destroy

**Error**
```
ERROR: (gcloud.secrets.versions.add) NOT_FOUND: Secret
[projects/.../secrets/django-secret-key] not found.
```

**Cause**
`secrets.bat` adds values to existing Secret Manager resources.
After `terraform destroy`, those resources no longer exist.
Running `secrets.bat` before `terraform apply` means the shells
don't exist yet — `gcloud secrets versions add` has nothing to add to.

**Correct order — every time after terraform destroy:**
```
1. terraform apply    ← creates secret shells (and all other infrastructure)
2. secrets.bat        ← fills the shells with values
3. terraform apply    ← update allowed_hosts with new Cloud Run URL
4. git push main      ← CD pipeline deploys Django image
```

**Wrong order that causes this error:**
```
secrets.bat           ← fails — shells don't exist yet
terraform apply
```

---

## T-10 — Cloud Run secret chicken-and-egg during fresh terraform apply

**Error**
```
Secret projects/.../secrets/django-secret-key/versions/latest was not found
```
or Cloud Run creation fails because `django-secret-key:latest` / `db-password:latest`
does not exist yet.

**Cause**
After `terraform destroy`, Secret Manager resources and all secret versions are
deleted. The first `terraform apply` can create new empty secret shells, but it
cannot also create a Cloud Run revision that references `secret:latest` because
GCP validates the referenced secret version during Cloud Run revision creation.

Terraform should also not create `google_secret_manager_secret_version` resources
for real credentials because Terraform writes managed values into
`terraform.tfstate`, which is plain JSON. Secret values in Terraform state would
expose credentials if the state file were committed, uploaded, or accessed by an
unauthorised user.

**Fix**
Split ownership:

| Owner | Responsibility |
|---|---|
| Terraform | Infrastructure shells: Secret Manager resources, Cloud SQL, Artifact Registry, service account, IAM, placeholder Cloud Run service/job |
| `infra\secrets.bat` | Add real secret versions directly with `gcloud secrets versions add` |
| GitHub Actions CD | Deploy real API/job images and attach populated secrets with `--set-secrets` |

Terraform Cloud Run resources must not contain `value_source.secret_key_ref`
blocks. The API service and ingestion job are created with placeholder images and
non-secret env vars only. CD then creates the real runtime revisions:

```yaml
gcloud run services update zeitgeist-api \
  --image ... \
  --port 8000 \
  --set-secrets "DJANGO_SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest"

gcloud run jobs update zeitgeist-ingest \
  --image ... \
  --set-secrets "DJANGO_SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest,NYTIMES_API_KEY=nytimes-api-key:latest,RAWG_API_KEY=rawg-api-key:latest,FOOTBALL_DATA_API_KEY=football-data-api-key:latest,CRICKET_DATA_API_KEY=cricket-data-api-key:latest"
```

**2026-07-03 source cleanup note**
Reddit is no longer an active source. Its API access is approval-gated and was
not verified for this project, so `reddit-client-id` and `reddit-client-secret`
must not be wired into Cloud Run, Secret Manager, seed data, or Django models.
Future sources must be API-verified with a live fetch before code, schemas,
secrets, or CD wiring are added.

**Correct fresh-start sequence**
```cmd
cd infra
terraform apply
terraform output api_url

REM Copy hostname only into infra\terraform.tfvars:
REM allowed_hosts = "zeitgeist-api-xxxxx-uc.a.run.app"

cd ..
infra\secrets.bat

cd infra
terraform apply

cd ..
git push origin main
```

**Important**
`allowed_hosts` should contain only the hostname, not `https://`. Example:
```hcl
allowed_hosts = "zeitgeist-api-xxxxx-uc.a.run.app"
```

---

## T-11 — Terraform plan removes Cloud SQL `/cloudsql` volume mounts

**Plan**
```
- volume_mounts {
  - mount_path = "/cloudsql" -> null
  - name       = "cloudsql" -> null
}
```

**Cause**
The Terraform Cloud Run resources declared the Cloud SQL volume:
```hcl
volumes {
  name = "cloudsql"
  cloud_sql_instance {
    instances = [var.db_connection]
  }
}
```

but the containers did not explicitly mount that volume. Cloud Run had a live
`/cloudsql` mount, but Terraform saw it as drift and planned to remove it.

**Why this is dangerous**
Django connects to Cloud SQL through a Unix socket path:
```text
DB_HOST=/cloudsql/PROJECT:REGION:INSTANCE
```

That path only exists if the `cloudsql` volume is mounted inside the container at
`/cloudsql`. Without it, migrations, API database access, and ingestion job
database access can fail even if a lightweight health endpoint still returns 200.

**Fix**
Add an explicit `volume_mounts` block to both Cloud Run containers:
```hcl
volume_mounts {
  name       = "cloudsql"
  mount_path = "/cloudsql"
}
```

This must be present in:
- `google_cloud_run_v2_service.api.template.containers`
- `google_cloud_run_v2_job.ingest.template.template.containers`

After applying the fix, run:
```cmd
cd infra
terraform apply
```

Expected plan shape:
```text
+ volume_mounts {
+   mount_path = "/cloudsql"
+   name       = "cloudsql"
+ }
```

---

## CI-07 — Smoke test returns HTTP 301 redirect

**Error**
```
Health check HTTP status: 301
ERROR: Health check failed — Cloud Run serving previous revision
```

**Cause**
The Cloud Run service was reachable, but Django returned a redirect instead of
the health JSON. In production, `SECURE_SSL_REDIRECT = True` tells Django to
redirect HTTP requests to HTTPS.

Cloud Run terminates HTTPS at the platform edge and forwards the request to the
container over HTTP with an `X-Forwarded-Proto: https` header. Without
`SECURE_PROXY_SSL_HEADER`, Django sees the internal hop as plain HTTP and issues
a 301 redirect even though the public request was already HTTPS.

Do not fix this by adding `curl -L` to the smoke test. That would hide a proxy
configuration problem and can become a redirect loop for real users.

**Fix**
Tell Django to trust Cloud Run's forwarded proto header:
```python
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

After committing and pushing the fix, rerun CD. The smoke test should receive:
```text
Health check HTTP status: 200
```

---

## T-12 — Terraform wants to roll Cloud Run back to placeholder image after CD

**Plan**
```text
~ image = "us-central1-docker.pkg.dev/.../api:<sha>" -> "us-docker.pkg.dev/cloudrun/container/hello:latest"

- env {
  - name = "DJANGO_SECRET_KEY" -> null
  - value_source.secret_key_ref ...
}

- env {
  - name = "DB_PASSWORD" -> null
  - value_source.secret_key_ref ...
}
```

**Cause**
Terraform and GitHub Actions CD were both touching the same Cloud Run runtime
fields.

Terraform creates the API service and ingestion job during bootstrap with:

```text
image = us-docker.pkg.dev/cloudrun/container/hello:latest
secret env vars = none
```

That placeholder is required after a fresh `terraform destroy` because the real
Artifact Registry image and Secret Manager versions may not exist yet.

After bootstrap, CD updates the same Cloud Run resources with:

```text
image = real API/job image from Artifact Registry
secret env vars = DJANGO_SECRET_KEY, DB_PASSWORD, GOOGLE_CLIENT_* as needed
```

On a later `terraform plan`, Terraform compares its bootstrap config to the live
CD-managed revision and tries to "fix" Cloud Run back to the placeholder image
and no secret env vars.

**Why this is dangerous**
Applying that plan would break the deployed API/job by replacing the real Django
image with the hello-world placeholder and removing runtime secrets.

**Fix**
Keep the placeholder for first bootstrap, but tell Terraform to ignore runtime
fields owned by CD:

```hcl
resource "google_cloud_run_v2_service" "api" {
  lifecycle {
    ignore_changes = [
      client,
      client_version,
      scaling,
      template[0].containers[0].image,
      template[0].containers[0].env,
    ]
  }
}

resource "google_cloud_run_v2_job" "ingest" {
  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].template[0].containers[0].image,
      template[0].template[0].containers[0].env,
    ]
  }
}
```

Ownership after this fix:

| Owner | Fields |
|---|---|
| Terraform | Service/job existence, IAM, service account, Cloud SQL mount, resources, scaling, port, scheduler |
| CD | Real container image and secret runtime env vars |

**Verification**
Run:

```cmd
cd infra
terraform fmt -recursive
terraform validate
terraform plan
```

Expected: `terraform plan` must not show image changes back to
`us-docker.pkg.dev/cloudrun/container/hello:latest`, and must not remove
CD-attached secret env vars from `zeitgeist-api` or `zeitgeist-ingest`.
After the final fix, the expected result is:

```text
No changes. Your infrastructure matches the configuration.
```

---

## T-13 — Adding new secrets makes Terraform replace WIF IAM binding

**Plan**
```text
# module.cloud_run.google_service_account_iam_member.github_wif_user must be replaced
-/+ resource "google_service_account_iam_member" "github_wif_user" {
  ~ member = "principalSet://..." -> (known after apply) # forces replacement
}

# module.cloud_run.null_resource.iam_propagation_delay must be replaced
-/+ resource "null_resource" "iam_propagation_delay" {
  ~ triggers = {
    ~ "github_wif_user" = "..." -> (known after apply)
  }
}

Plan: 4 to add, 0 to change, 2 to destroy.
```

**Cause**
This is not the Cloud Run placeholder-image drift bug from T-12.

The root module had:
```hcl
module "cloud_run" {
  depends_on = [module.cloud_sql, module.artifact_registry, module.secrets]
}
```

When new Secret Manager resources are added, `module.secrets` has pending
changes. Because the whole `cloud_run` module depended on the whole `secrets`
module, Terraform deferred data reads inside `module.cloud_run`, including the
project-number lookup used to build the GitHub Workload Identity Federation
principal string.

That made the WIF IAM member value appear as `(known after apply)`, so Terraform
planned to destroy and recreate the IAM binding and the dependent
`iam_propagation_delay` `null_resource`.

**Why this is unnecessary**
Cloud Run no longer references Secret Manager resources in Terraform. Terraform
creates secret shells only. `infra\secrets.bat` adds secret values, and GitHub
Actions CD attaches those populated secrets to Cloud Run with `--set-secrets`.

So `module.cloud_run` does not need to depend on `module.secrets`.

**Fix**
Remove `module.secrets` from the `cloud_run` module `depends_on`:
```hcl
module "cloud_run" {
  depends_on = [module.cloud_sql, module.artifact_registry]
}
```

Then re-run:
```cmd
terraform plan
```

Expected plan when adding NYT/RAWG secrets:
```text
Plan: 2 to add, 0 to change, 0 to destroy.
```

**If you need a one-time safe apply before this fix is committed**
Use targeted apply to create only the two new Secret Manager shells:
```cmd
terraform apply -target='module.secrets.google_secret_manager_secret.secrets["nytimes-api-key"]' -target='module.secrets.google_secret_manager_secret.secrets["rawg-api-key"]'
```

---

## CI-08 — API CORS breaks after frontend Cloud Run deployment

**Browser error**
```text
Access to fetch at 'https://zeitgeist-api-...run.app/api/v1/auth/me/'
from origin 'https://zeitgeist-frontend-82456441710.us-central1.run.app'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is
present on the requested resource.
```

The network row can still show `200 OK`. That means the API responded, but the
browser refused to expose the response to JavaScript because the CORS response
header was missing.

**Cause**
Cloud Run may expose more than one usable service URL format. In this project,
the frontend has been reached through:
```text
https://zeitgeist-frontend-opowb5bpna-uc.a.run.app
https://zeitgeist-frontend-82456441710.us-central1.run.app
```

The CD workflow originally updated `zeitgeist-api` with only the URL returned by
`gcloud run services describe zeitgeist-frontend --format value(status.url)`.
When the browser used the regional/project-number URL instead, Django's
`CORS_ALLOWED_ORIGINS` did not contain that exact origin and `django-cors-headers`
did not emit `Access-Control-Allow-Origin`.

Manual fixes can also be overwritten by the next successful CD run if `cd.yml`
still computes the incomplete origin list.

**Debug commands**
Check deployed API env vars:
```cmd
gcloud run services describe zeitgeist-api --region us-central1 --project zeitgeist-499322 --format="yaml(spec.template.spec.containers[0].env)"
```

Check the actual CORS response header:
```cmd
curl.exe -i -H "Origin: https://zeitgeist-frontend-82456441710.us-central1.run.app" https://zeitgeist-api-opowb5bpna-uc.a.run.app/api/v1/auth/me/
```

**Fix**
In `.github/workflows/cd.yml`, include both frontend URL formats when deploying
the API:
```yaml
FRONTEND_URL=$(gcloud run services describe zeitgeist-frontend \
  --region ${{ env.GCP_REGION }} \
  --project ${{ env.GCP_PROJECT_ID }} \
  --format 'value(status.url)')
PROJECT_NUMBER=$(gcloud projects describe ${{ env.GCP_PROJECT_ID }} \
  --format 'value(projectNumber)')
FRONTEND_REGIONAL_URL="https://zeitgeist-frontend-$PROJECT_NUMBER.${{ env.GCP_REGION }}.run.app"
TRUSTED_ORIGINS="http://localhost:3000,$FRONTEND_URL,$FRONTEND_REGIONAL_URL"
```

Then pass `TRUSTED_ORIGINS` to both:
```yaml
CORS_ALLOWED_ORIGINS=$TRUSTED_ORIGINS
CSRF_TRUSTED_ORIGINS=$TRUSTED_ORIGINS
```

Because the value contains commas, use a custom delimiter with `gcloud`:
```yaml
--set-env-vars "^|^...|CORS_ALLOWED_ORIGINS=$TRUSTED_ORIGINS|CSRF_TRUSTED_ORIGINS=$TRUSTED_ORIGINS"
```

---

## FE-01 — Minified React error #418 after deployment

**Browser error**
```text
Uncaught Error: Minified React error #418
```

**Cause**
This is a hydration mismatch. Next.js sends server-rendered HTML first, then
React attaches to that HTML in the browser. The first browser render must match
the server HTML exactly.

Known causes found in this project:

1. The dashboard server could not read browser `localStorage`, so it rendered
   default category preferences. The browser could read `localStorage` during
   the initial client render and immediately render a different preference
   state. React detected that the text/HTML did not match and raised error #418.

2. `formatLastUpdated()` used `Intl.DateTimeFormat` without a fixed timezone.
   Locally, the Next.js server and browser usually share the same machine
   timezone, so no mismatch appears. In Cloud Run, the server renders in UTC
   while the user's browser renders in local time. The same timestamp can
   become different text during hydration, for example `Jul 7, 6:36 PM` on the
   server and `Jul 7, 2:36 PM` in the browser.

**Fix**
Do not read `localStorage` inside the initial `useState` render path for a
server-rendered Client Component. Render the same default state as the server,
then load browser-only preferences after hydration:
```tsx
const [selectedSlugs, setSelectedSlugs] = useState<string[]>(allCategorySlugs);

useEffect(() => {
  const localPreferences = readLocalPreferences();
  if (localPreferences === null) {
    return;
  }

  window.setTimeout(() => {
    setSelectedSlugs(localPreferences);
  }, 0);
}, []);
```

For timestamp text rendered by both server and browser, pin the timezone:
```ts
return new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZone: "UTC"
}).format(date);
```

**Verification**
If local dev works but production still shows `#418`, test whether production
rendering is the difference:
```cmd
cd frontend
npm run build
npm run start
```

Then open `http://localhost:3000` and check the browser console.

---

## AUTH-01 — Forgot-password request returns generic 500 during local SMTP testing

**Error**
```text
Request failed with status 500.
```

**Cause**
The password-reset request endpoint created an OTP and then attempted to send
email through SMTP. When SMTP failed, the exception bubbled up as a generic 500.
The frontend also started the resend cooldown even though the request failed,
which made the UI look as if an email had been sent.

**Fix**
Handle password-reset email failures the same way registration verification
email failures are handled:

- catch the email exception in the API view
- delete the just-created OTP so a failed send does not leave an active code
- return a clear 503 response
- start the frontend resend cooldown only after a successful request

**Where to check errors**

Local backend errors appear in the terminal running:

```cmd
python manage.py runserver localhost:8000
```

If using the production-like job path locally, check the terminal running:

```cmd
python run_job.py
```

In Cloud Run, check service logs:

```cmd
gcloud run services logs tail zeitgeist-api --region us-central1 --project zeitgeist-499322
```

**How to see the full error**
Production React errors are minified. Reproduce locally in development mode to
see the full message:
```cmd
cd frontend
npm run dev
```

Then open `http://localhost:3000` and check the browser console.

---

## AUTH-02 — Public auth endpoints need app-level rate limiting

**Risk**
```text
/api/v1/auth/login/
/api/v1/auth/signup/
/api/v1/auth/verify-email/
/api/v1/auth/resend-verification/
/api/v1/auth/password-reset/request/
/api/v1/auth/password-reset/confirm/
```

Without request throttling, a public launch can attract automated login attempts,
OTP brute-force attempts, and email-send abuse. Even if the attacker cannot sign
in, excessive requests can consume Cloud Run concurrency, Cloud SQL connections,
and SMTP quota.

**Cause**
Django and Django REST Framework do not automatically rate-limit custom API
views. Password hashing and SMTP sends are relatively expensive operations, so
they need a cheap reject path before doing the work.

**Fix**
Add cache-backed application rate limiting around public auth mutations:

- IP-level limits to reduce broad request floods.
- Email-level limits to protect a specific account from repeated attempts.
- HTTP `429 Too Many Requests` responses before password checks or email sends.

The runtime knobs are:
```text
AUTH_RATE_LIMIT_WINDOW_SECONDS=60
AUTH_RATE_LIMIT_IP_REQUESTS=30
AUTH_RATE_LIMIT_EMAIL_REQUESTS=10
```

CD must pass these values to `zeitgeist-api` in `.github/workflows/cd.yml`.

**Follow-up**
This is app-level protection. It is useful and cheap, but it only runs after the
request reaches Django. For network-edge throttling before Cloud Run, use Cloud
Armor behind an external Application Load Balancer.

---

## AUTH-03 — OTP records must be invalidated after resend and max attempts

**Risk**
If users can request many active OTP records for the same email, each OTP's
attempt counter gives another small brute-force window. A six-digit OTP with
five attempts is acceptable per active code, but many simultaneous active codes
unnecessarily increase the total attempts available for one email.

**Fix**
When issuing a new registration or password-reset OTP, consume older active OTPs
for the same email/purpose. When a code reaches the configured max attempts,
consume it so it cannot be retried.

Current OTP settings:
```text
EMAIL_VERIFICATION_OTP_TTL_MINUTES=10
EMAIL_VERIFICATION_MAX_ATTEMPTS=5
EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS=60
```

---

## CI-09 — Backend regional Cloud Run URL returns Bad Request 400

**Error**
```text
https://zeitgeist-api-82456441710.us-central1.run.app/api/v1/health/
Bad Request (400)
```

while the hash-style backend URL works:
```text
https://zeitgeist-api-opowb5bpna-uc.a.run.app/api/v1/health/
{"status":"ok"}
```

**Cause**
Cloud Run can expose more than one usable URL format for the same service.
Django rejects requests when the incoming `Host` header is not present in
`ALLOWED_HOSTS`. CD originally set only the hostname returned by:
```cmd
gcloud run services describe zeitgeist-api --region us-central1 --project zeitgeist-499322 --format "value(status.url)"
```

That left the other valid Cloud Run hostname blocked by Django host validation.

**Fix**
In `.github/workflows/cd.yml`, compute and pass all backend hostnames to the
real API service deployment:
```yaml
API_HOST=${API_URL#https://}
PROJECT_NUMBER=$(gcloud projects describe ${{ env.GCP_PROJECT_ID }} \
  --format 'value(projectNumber)')
API_REGIONAL_HOST="zeitgeist-api-$PROJECT_NUMBER.${{ env.GCP_REGION }}.run.app"
API_LEGACY_HOST="zeitgeist-api-opowb5bpna-uc.a.run.app"
API_ALLOWED_HOSTS="$API_HOST,$API_REGIONAL_HOST,$API_LEGACY_HOST"
```

Then use:
```yaml
ALLOWED_HOSTS=$API_ALLOWED_HOSTS
```

**Important**
The `ALLOWED_HOSTS=localhost` values used by the reusable Cloud Run database
maintenance job do not need the public host list. That job runs Django
management commands such as `migrate` and `seed_categories`; it does not serve
public HTTP traffic. `localhost` only satisfies Django's production system
checks.

---
