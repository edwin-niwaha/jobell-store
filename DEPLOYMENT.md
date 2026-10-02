# Railway production deployment

Deploy the `jobell-store` Django website/API. `jobell-mobile` is a separate Expo
application and has its own release process. No live deployment or database
migration is performed by preparing these files.

## Local verification — 2 October 2026

Verified with Python 3.12, Django 5.2.17, and an isolated PostgreSQL 15 database:

- All 93 tests passed, including guest checkout, cart ownership, payment
  verification, staff restrictions, registration/JWT authentication, Google login
  initiation, and order/email behavior.
- Real browser checkout and confirmation flows passed at 320px and 390px on
  mobile and 1440px on desktop, with heading layout and overflow assertions.
- No pending model migrations; dependency compatibility check passed.
- Production `check --deploy --fail-level WARNING` passed with explicit secure
  settings and dummy external-service credentials.
- Production HTTP probes passed for Railway health checks, HTTPS redirects,
  reverse-proxy HTTPS detection, and invalid-host rejection.
- Static collection passed: 1,011 files collected; all 121 literal template
  static references exist in the generated manifest. PDF generation passed.
- The pinned runtime packages match the tested environment; their base
  Linux dependency metadata was checked for missing or incompatible pins.
- The final installed-environment vulnerability audit checked 132 packages,
  including all 107 runtime packages: zero known vulnerabilities, skipped packages,
  or suppressed advisories.

The authentication upgrade uses a documented, metadata-only Djoser compatibility
wheel. Its upstream application code is unchanged. See [vendor/README.md](vendor/README.md)
for the reason, checksums, rebuild command, and maintenance requirement. Browser
Google login now submits a CSRF-protected POST and is hidden until configured.

The local Docker daemon is unavailable, so the Linux container build still needs
to pass the included CI workflow or Railway build. Real production credentials,
PostgreSQL/Redis connectivity, Cloudinary uploads, email delivery, worker
execution, and optional live payment integration require staging/release checks.
The tests exercise payment verification with mocks and send no real messages.

## Release gates

Use Python 3.12 and the production dependency lock, not the old development
environment. The lock is built from the application's runtime imports rather
than the legacy requirements file's unused CMS/editor dependencies.

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip==26.2.1
python -m pip install -r requirements-production.txt
python -m pip check
python -m pip install pip-audit
python -m pip_audit --local
python manage.py check --settings=core.settings.test
python manage.py makemigrations --check --dry-run --settings=core.settings.test
python manage.py test --noinput --settings=core.settings.test
```

Tests use an isolated SQLite database by default. For PostgreSQL parity, set
`TEST_DATABASE_URL` to a disposable PostgreSQL database whose user can create test
databases. Test settings ignore `DATABASE_URL`, disable real emails and Redis
tasks, and store test uploads in memory. Profile avatar URL rendering uses a
placeholder Cloudinary cloud name. Set `PYTHON_DOTENV_DISABLED=1` before running
the checks to prevent local `.env` credentials from masking missing test
configuration; CI sets this automatically. Never set `TEST_DATABASE_URL` to a
live customer database.

Browser checkout tests require Node, Playwright in `NODE_PATH`, and an installed
browser. Set `CHECKOUT_BROWSER_CHANNEL=chromium` for Playwright Chromium (the local
Windows default is Edge). The GitHub workflow validates both Railway config
files against the checked-in Railway schema at `.github/railway.schema.json`
(avoiding upstream rate limits), installs the browser tools, and runs
the full suite, migration drift check, dependency audit, and Docker build on Linux.

## Railway services

The schema snapshot was retrieved from `https://railway.com/railway.schema.json`
on 2 October 2026. When adding Railway configuration features, download and review
the latest upstream schema, update `.github/railway.schema.json`, and validate
both configurations before merging. CI deliberately uses the local snapshot.

### Production branch policy

Changes flow from `dev` (or another working branch) through a pull request into
`main`. Only `main` may deploy to production. Protect `main` in GitHub with a
ruleset requiring pull requests and the `test` status check from Production checks;
disable bypasses and force pushes to enforce merging rather than direct pushes.

For **both web and Celery services** in Railway's production environment, set
Settings → Source → connected branch to `main` and enable **Wait for CI**.
These are Railway dashboard settings, not fields in `railway.json`.
Keep any `dev` staging service in a separate environment with separate data and
its own deployment configuration.

Both production configurations run `scripts/check_production_branch.py` before
deployment. It rejects `dev`, other branches, and missing `RAILWAY_GIT_BRANCH`
metadata, before web migrations or worker startup. Use GitHub-triggered deployments;
local CLI uploads without GitHub branch metadata are intentionally blocked.
Do not manually override `RAILWAY_GIT_BRANCH` to bypass the guard.

The CI workflow runs on pushes and pull requests targeting `main` and `dev`.
It validates code but does not deploy it. Railway deploys the merged `main`
commit after its checks pass when Wait for CI is enabled.
See [Railway autodeploy settings](https://docs.railway.com/deployments/github-autodeploys)
and [Git branch metadata](https://docs.railway.com/variables/reference).

1. Back up the existing PostgreSQL database and verify how to restore it before
   running new migrations. Preserve existing Cloudinary assets and any local
   uploads separately; local `media/` is intentionally excluded from the image.
2. Connect the repository to Railway. If this workspace's parent directory is
   the repository root, select `/jobell-store` as the service root. If the
   `jobell-store` directory itself is the repository, use `/`.
3. Add PostgreSQL and Redis services. Keep their connection URLs in Railway
   variables; never commit credentials.
4. Create the web service with `railway.json`. The Dockerfile installs the locked
   dependencies and builds hashed static assets without production secrets.
   Runtime uses Gunicorn, listens on Railway's `PORT`, logs to stdout/stderr, and
   runs as a non-root user.
5. Copy the variable names from `.env.production.example` into Railway and fill
   their values. Set `DATABASE_URL` from the PostgreSQL service reference and
   `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND` from Redis. Set
   `DB_SSL_REQUIRE` according to the database endpoint: Railway private
   networking typically uses `False`; a TLS endpoint requires `True`.
   Set `COMPANY_NAME=Jobell Inc.` and `SITE_NAME=Jobell Inc.` in existing
   services as well; Railway variables override the defaults in the code.
   The storefront header uses `COMPANY_NAME` followed by the `Storefront` label.
6. Generate a new unique `SECRET_KEY`, for example with
   `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Set the public
   HTTPS domain in `SITE_URL`, `ALLOWED_HOSTS`, `BASE_DOMAIN`,
   `CSRF_TRUSTED_ORIGINS`, and `CORS_ALLOWED_ORIGINS`. Include the assigned Railway
   hostname if you will access it directly. Avoid wildcard hosts/origins.
7. Configure Cloudinary for persistent uploads and Resend with a verified sender
   domain (or authenticated SMTP). The deployment check rejects missing media
   and email configuration. Update admin recipient and support addresses.
8. Configure `GOOGLE_KEY` and `GOOGLE_SECRET` if browser Google login is wanted.
   Register `https://YOUR_DOMAIN/oauth/complete/google-oauth2/` with the provider
   and test a complete sign-in on staging. The local tests verify initiation,
   CSRF protection, and return destinations without contacting Google.
   Manual Mobile Money and cash on delivery work without Flutterwave keys. If
   online Flutterwave payments are enabled, configure all three
   `FLUTTERWAVE_*` variables and the provider webhook URL
   `/orders/payment/flutter/webhook/`.
   Unconfigured/invalid webhook requests are rejected; successful events are
   verified with the provider before payment is recorded.
9. Railway accepts one web pre-deploy command. The configured shell command runs
   `check --deploy --fail-level WARNING` and then `migrate --noinput`, joined with
   `&&` so a failed check prevents migrations. Review the migration plan and
   database backup first. A failed check or migration blocks the rollout.
10. Create a second service from the same image/source for Celery. Select
    `railway.worker.json` as its config file and share the production variables.
    It has no public domain or HTTP health check. Start it after web migrations
    succeed. Confirm it connects to Redis and registers the order email tasks.

The `/health/` endpoint returns 200 only when PostgreSQL is reachable, or a
generic 503 on failure. It supports Railway's health-check hostname and internal
HTTP probes without redirecting; all other pages retain HTTPS enforcement.

The repository retains Railway's existing JSON config workflow. Railway's
[config reference](https://docs.railway.com/config-as-code/reference) currently
describes this as a legacy format; check its migration notice before creating
new services or changing the infrastructure workflow.

## Validate the deployed release

- Confirm `/health/` is 200, HTTP redirects to HTTPS on storefront routes, and
  unknown hosts are rejected.
- Open the storefront, product, cart, checkout, confirmation, login, and staff
  pages. Check 320px mobile and desktop layouts, product images, and static assets.
- Place one clearly labelled test order with permission to use the production
  shop. Verify pickup/delivery totals, stock, order ownership, manual payment
  status, and the admin processing flow. Do not charge a real payment merely to
  test the UI.
- Verify confirmation/admin email delivery and inspect worker/web logs. Check
  that email and WhatsApp product links use the public HTTPS domain.
- Test staff access, session persistence, logout, and protected order pages.
- Check print/PDF reports and existing uploaded images after the release.

## Rollback

Keep the previous healthy Railway image available. Roll back the web and worker
to the same release if application checks fail. Code rollback does not reverse
database migrations: inspect backwards compatibility before reversing anything,
and use the verified backup/restore plan when required. Do not delete live data
or media to repair a release.

## Dependency maintenance

Regenerate the lock in a clean Python 3.12 environment with pip-tools after
reviewing changes to `requirements-production.in`, then repeat all release gates:

```sh
python -m pip install pip-tools
python scripts/compile_requirements.py
python -m pip install -r requirements-production.txt
python -m pip_audit --local
```

Sources: [Django support policy](https://www.djangoproject.com/download/),
[Railway Django guide](https://docs.railway.com/guides/django),
[Railway health checks](https://docs.railway.com/deployments/healthchecks).
