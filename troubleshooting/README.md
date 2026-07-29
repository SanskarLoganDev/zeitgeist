# Zeitgeist Troubleshooting Log

This folder documents real bugs, deployment issues, and operational lessons from
the Zeitgeist project. The notes are committed with the repo because they are
useful project documentation, but they must never include real credentials,
secret values, Terraform state, `.env` contents, or local secret scripts.

## Files

| File | Contents |
|---|---|
| `terraform_cicd_issues.md` | Terraform, Cloud Run, Cloud SQL, Secret Manager, load balancer, CORS, auth, frontend hydration, and GitHub Actions issues. |
| `workflow.md` | Plain-English ingestion and request flow reference. |

## How To Use This Folder

When you hit an error:

1. Check here first because the fix may already be documented.
2. After fixing a new error, add the exact error message, cause, and fix.
3. Redact project-specific credentials, tokens, API keys, cookie values, OTPs,
   email passwords, database passwords, and raw Terraform state output.
4. Prefer placeholders like `PROJECT_ID`, `SA_EMAIL`, `example.run.app`, or
   `replace-me` when a command shape is useful but a real value is sensitive.

## Good Troubleshooting Entry Shape

```text
## AREA-00 - Short title

**Error**
Paste the searchable error message.

**Cause**
Explain the root cause in one or two paragraphs.

**Fix**
Show the config or command change that fixed it, with secrets redacted.

**Lesson**
Capture the reusable lesson for future projects.
```
