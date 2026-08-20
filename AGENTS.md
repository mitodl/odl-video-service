# ODL Video Service — AI Agent Instructions

A video hosting platform for MIT's Office of Digital Learning (ODL). Videos are stored in AWS S3, transcoded via AWS MediaConvert (`mitol-django-transcoding`), and delivered through signed CloudFront URLs. Authentication is handled by Keycloak (federating to MIT Touchstone). Access control is managed via **KeycloakGroups** (historically called MoiraLists — renamed in migration `0040`).

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Framework | Django 4.2, Django REST Framework |
| Package manager | `uv` (not pip, not poetry) |
| Database | PostgreSQL 18 |
| Cache / broker | Redis 8 |
| Async tasks | Celery + celery-redbeat (scheduled tasks) |
| Auth | Keycloak OIDC via `social-auth-app-django` |
| Video delivery | AWS S3 + CloudFront (signed URLs) |
| Transcoding | AWS MediaConvert (via `mitol-django-transcoding`) |
| Frontend | React 15, Redux, Flow types, Webpack 5 |
| JS test runner | Mocha + Chai + Enzyme |
| JS package manager | Yarn 1.22.22 |
| Node version | 24.14.0 |
| Linting (Python) | `ruff` |
| Linting (JS) | ESLint + prettier-eslint |
| Containerization | Docker Compose |

---

## Running Tests

### Python tests

```bash
# Full test suite (pytest + migration checks)
./scripts/test/python_tests.sh

# Just pytest directly
uv run pytest

# Single file or test
uv run pytest ui/models_test.py
uv run pytest ui/models_test.py::test_video_model_s3keys

# With coverage
uv run pytest --cov .
```

`pytest.ini` configures `--reuse-db` (schema is reused between runs; use `--create-db` to force a fresh schema). All AWS/Celery/external env vars are pre-set to fake values in `pytest.ini` so no real `.env` is needed for tests.

### JavaScript tests

```bash
# All JS tests
yarn test          # or: npm run test

# With coverage
yarn coverage

# Watch mode
yarn watch

# Single file
./scripts/test/js_test.sh static/js/components/VideoPlayer_test.js
```

---

## Linting and Formatting

### Python

```bash
# Check formatting
uv run ruff format --check . --exclude '*/migrations/'

# Apply formatting
uv run ruff format . --exclude '*/migrations/'

# Check lint rules (and auto-fix)
uv run ruff check --fix . --exclude '*/migrations/'
```

Migrations are excluded from ruff linting and formatting — never run ruff on migration files.

### JavaScript

```bash
# ESLint
yarn lint          # lint static/js

# Format with prettier-eslint
yarn fmt           # write changes
yarn fmt:check     # check only (no writes)

# SCSS lint
yarn scss_lint
```

### Pre-commit (all checks)

```bash
pre-commit run --all-files
```

Pre-commit runs: `ruff-format`, `ruff`, `detect-secrets`, `shellcheck`, `actionlint`, `yamllint`, `shfmt`, and a custom `drf-lint` hook that detects N+1 risks in DRF serializers. The `drf_lint_baseline.json` file records known baseline violations.

---

## Development Server

```bash
# Start all services (web, celery, webpack watch, postgres, redis, nginx)
docker-compose up

# Access the app at http://localhost:8089 (via nginx proxy)
# Direct Django app at http://localhost:8087
# Webpack dev server at http://localhost:8082
```

The `web` service runs `uwsgi`, the `watch` service runs webpack in dev mode with HMR, and the `celery` service runs both the worker and beat scheduler (`-B` flag).

---

## Django Apps

| App | Location | Purpose |
|-----|----------|---------|
| `ui` | `ui/` | Core domain: Video, Collection, KeycloakGroup models; REST API; video upload/transcode/playback; edX integration |
| `cloudsync` | `cloudsync/` | Async tasks for syncing video data to AWS S3 and Cloudfront; YouTube sync |
| `mail` | `mail/` | Email notifications via Mailgun |
| `techtv2ovs` | `techtv2ovs/` | Migration data app for importing legacy TechTV content |
| `odl_video` | `odl_video/` | Project root: settings, URLs, Celery config, base models (`TimestampedModel`), custom envs helpers |
| `s3_sync` | `s3_sync/` | Standalone S3 sync scripts (not a Django app, no `apps.py`) |

### Key models in `ui`

- `Collection` — a grouping of videos with KeycloakGroup-based view/admin access control
- `Video` — video record with S3 keys, transcode status, subtitle support, YouTube status
- `VideoFile` — individual encoded video file linked to a Video
- `KeycloakGroup` — replaces the old `MoiraList` (renamed in migration `0040`); used for collection/video access control
- `EdxEndpoint` — an Open edX instance to which video metadata is posted (uses `EncryptedTextField` for credentials)

---

## Key Architectural Patterns

### Authentication and Authorization
- Keycloak OIDC via `social-auth-app-django` backend (`social_core.backends.keycloak.KeycloakOAuth2`)
- `USE_KEYCLOAK=True` (default) enables Keycloak; set `False` for local dev without Keycloak (falls back to `ModelBackend`)
- Keycloak groups from the JWT `user_groups` claim are synced to Django `is_staff`/`is_superuser` via `odl_video.pipeline.assign_user_groups`
- Access to Collections/Videos is controlled via `KeycloakGroup` M2M fields (`view_lists`, `admin_lists`, `video_view_lists`)
- **Historical note**: `KeycloakGroup` was previously called `MoiraList` (MIT's mailing list permission system). Migration `0040` renamed it. Old variable names or comments may still reference "Moira."

### AWS Integration
- Four S3 buckets: upload (`VIDEO_S3_BUCKET`), transcode (`VIDEO_S3_TRANSCODE_BUCKET`), thumbnail (`VIDEO_S3_THUMBNAIL_BUCKET`), subtitle (`VIDEO_S3_SUBTITLE_BUCKET`)
- CloudFront delivers private video content via signed URLs (requires `CLOUDFRONT_PRIVATE_KEY` and `CLOUDFRONT_KEY_ID`)
- Video transcoding uses **AWS MediaConvert** via `mitol-django-transcoding`; job template is at `config/mediaconvert.json`

### edX Integration
- `EdxEndpoint` records (created in Django admin) hold the `base_url`, OAuth2 `client_id`/`secret_key` (encrypted), and `edx_video_api_path` for each Open edX instance
- A `Collection` is linked to an `EdxEndpoint` via `CollectionEdxEndpoint` (M2M through-table); `edx_course_id` on the collection identifies the target course
- When `edx_course_id` is first set, OVS **auto-assigns** an endpoint: course IDs containing `:xpro+` → endpoint with `.xpro.` in its URL; all others → endpoint with `.learn.` in its URL
- The **Sync Videos with edX** button triggers `post_collection_videos_to_edx` (Celery task in `ui/tasks.py`), which POSTs all `COMPLETE` video files to `<base_url>/api/val/v0/videos/` using a short-lived JWT fetched via `client_credentials` grant
- Both HLS and MP4 formats (excluding `ORIGINAL`) are pushed; verify at `<edx-base>/admin/edxval/video/`

### Celery
- Tasks are defined in `ui/tasks.py`, `cloudsync/tasks.py`, `mail/tasks.py`
- Scheduled tasks use `celery-redbeat` (Redis-backed beat scheduler)
- In tests: `CELERY_TASK_ALWAYS_EAGER=True` executes tasks synchronously

### Frontend (React)
- **React 15** — class components, no hooks; `enzyme-adapter-react-15` for testing
- **Flow types** (not TypeScript) — `.flowconfig` present, `flow-bin` installed
- Redux + redux-thunk + redux-actions for state management
- Video.js 8 for video playback with quality selector, HLS, annotations
- Material Design via `rmwc` and `@material/*` v0.33 (old MDC Web API)
- Entry points in `static/js/entry/`; bundled via Webpack 5

### N+1 Detection
- `nplusone` middleware is enabled in `DEBUG=True` mode (dev/local only)
- `drf-lint` pre-commit hook catches ORM queries inside DRF serializer methods
- `drf_lint_baseline.json` tracks known baseline violations — update it when adding intentional query access in serializers

---

## Test File Naming Conventions

- **Python**: `*_test.py` suffix (e.g., `models_test.py`, `views_test.py`) — MIT ODL convention
- **JavaScript**: `*_test.js` suffix (e.g., `VideoPlayer_test.js`, `App_test.js`)
- **Do not** create `test_*.py` or `test_*.js` files — they break from convention and may not be picked up by the test scripts correctly

---

## Settings and Environment

- Settings module: `odl_video.settings` (specified in `pytest.ini` as `--ds=odl_video.settings`)
- Custom env helpers (`get_string`, `get_bool`, `get_int`, etc.) live in `odl_video/envs.py` — use these instead of `os.environ` directly
- Copy `.env.example` to `.env` for local setup
- `DISABLE_WEBPACK_LOADER_STATS=True` is required in test environments (set in `pytest.ini`) to avoid webpack stats file errors

### Important environment variables

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret key |
| `DATABASE_URL` | Postgres connection string |
| `REDIS_URL` | Redis URL |
| `USE_KEYCLOAK` | Enable/disable Keycloak auth (default `True`) |
| `VIDEO_S3_BUCKET` | Upload bucket |
| `VIDEO_CLOUDFRONT_DIST` | CloudFront distribution ID |
| `VIDEO_CDN_DISTRIBUTION_ID` | CloudFront CDN distribution ID (mandatory; used alongside `VIDEO_CLOUDFRONT_DIST`) |
| `CLOUDFRONT_PRIVATE_KEY` | RSA private key for signed URLs (single-line, `\n` escaped) |
| `FIELD_ENCRYPTION_KEY` | Key for `EncryptedTextField` fields |
| `VIDEO_S3_TRANSCODE_ENDPOINT` | MediaConvert endpoint URL for your AWS region |
| `TRANSCODE_JOB_TEMPLATE` | Path to job template (default: `config/mediaconvert.json`) |
| `AWS_ACCOUNT_ID` | 12-digit AWS account ID (used to build the MediaConvert IAM role ARN) |
| `AWS_ROLE_NAME` | IAM role name that MediaConvert assumes for transcoding |
| `MAILGUN_URL` / `MAILGUN_KEY` | Email delivery |
| `ODL_VIDEO_DB_DISABLE_SSL` | Set `True` for local dev without SSL on Postgres |

### Opt-in django-aqueduct settings modules

`odl_video.settings` remains the default and is untouched — nothing below changes
its behavior. Two additional, opt-in settings modules exist for projects that
want typed/validated settings via [django-aqueduct](https://github.com/mitodl/django-aqueduct):

- `odl_video.aqueduct_settings` — a Pydantic `BaseSettings` model
  (`AqueductSettings`) generated by django-aqueduct's codegen v2 (static AST
  discovery of `odl_video/settings.py` plus the mitol EnvParser registry).
  The file is split into managed regions: `# >>> aqueduct:generated:*`
  regions are rewritten by the generator; hand-written refinements (required
  fields, cross-field timing validation, the conditional
  `INSTALLED_APPS`/`MIDDLEWARE`/`CELERY_BEAT_SCHEDULE` branches, derivations
  from `django_aqueduct.derivations`) live in the
  `# >>> aqueduct:preserved:*` region and survive regeneration. List/dict
  settings fed non-JSON env values (comma-separated, Python-literal, or a
  bare `[*]`) are parsed by the generator-emitted `NoDecode` +
  `_aqueduct_decode_*_fields` validators in the
  `aqueduct:generated:container_decoders` region, so no custom env source is
  needed. `*_URL` fields are kept as plain `str` — `enrich_url_types` is
  left OFF. 0.9.0's opt-in `pydantic.AnyUrl` promotion serializes top-level
  fields back to `str`, but a promoted field still holds an `AnyUrl` *object*
  at runtime, which breaks two consumers here: the in-validator Redis/Celery
  fallback chain calls `.strip()` on `CELERY_BROKER_URL` (an `AnyUrl` has no
  `.strip()`), and that value is nested into the `CACHES` dict where the
  field serializer never reaches, leaving an `AnyUrl` where redis expects a
  `str`. `str` is the correct type for a Django settings-injection model. It
  also defines `DevAqueductSettings`, which layers a Vault source configured
  entirely from `VAULT_*` env vars (`django_aqueduct.sources.dev`) on top for
  local dev without a `.env` file.
- `odl_video.settings_aqueduct` / `odl_video.settings_aqueduct_dev` — thin
  shims that call `django_aqueduct.configure_django_settings(...)` with
  `AqueductSettings` / `DevAqueductSettings` respectively, using the
  `pre_configure` hook to initialize Sentry from the validated model before
  Django settings exist.

Select one by setting `DJANGO_SETTINGS_MODULE=odl_video.settings_aqueduct` (or
`..._aqueduct_dev`) instead of the default `odl_video.settings`.

Generation and drift/parity checks are configured in `[tool.aqueduct]` in
`pyproject.toml`:

```bash
# Regenerate (merges into managed regions, preserves hand-written code).
# --enrich-usage is a safe static AST scan of app code for `settings.X`
# comparisons that would justify a Literal/range constraint (currently a
# no-op for this codebase, but re-run it so new comparison sites are picked
# up). Do NOT use --enrich-runtime (it imports the settings module).
uv run python manage.py generate_aqueduct_settings \
    --enrich-usage ui --enrich-usage cloudsync --enrich-usage mail \
    --enrich-usage odl_video --enrich-usage techtv2ovs
# CI drift check for the generated regions
uv run python manage.py generate_aqueduct_settings --check
# Parity gate: model vs odl_video.settings under the same environment
uv run python manage.py check_aqueduct_settings
```

(`django_aqueduct` is not in the legacy `INSTALLED_APPS`; to run these
commands, invoke the command classes directly under
`DJANGO_SETTINGS_MODULE=odl_video.settings` — see the PR that introduced
them — or add the app temporarily.)

---

## Common Gotchas for AI Agents

1. **React 15, not modern React** — No hooks, no functional components with state. Use `React.Component` class syntax.
2. **Flow types, not TypeScript** — Type annotations use Flow syntax (`// @flow`, `: string`, `?string`).
3. **`uv` for Python** — All Python commands must be prefixed with `uv run` (e.g., `uv run pytest`, `uv run python manage.py`). Do not use `pip install`.
4. **`yarn` for JS** — Use `yarn add` / `yarn install`, not `npm install`.
5. **Moira → KeycloakGroup rename** — The permission group model was `MoiraList`, now `KeycloakGroup`. Migrations reference both names. Don't re-introduce `MoiraList`.
6. **Migrations excluded from ruff** — Never run `ruff format` or `ruff check` on files in any `migrations/` directory.
7. **`--reuse-db` is the default** — Tests reuse the DB schema. If you add a migration, run `uv run pytest --create-db` on the first run.
8. **Warnings-as-errors in tests** — `conftest.py` turns warnings into errors. New deprecation warnings from your code will fail tests.
9. **`social_django` conditionally enabled** — It is commented out of `INSTALLED_APPS`/`MIDDLEWARE` defaults but added at runtime when `USE_KEYCLOAK=True`. Don't hardcode it into the base lists.
10. **Encrypted fields** — `EdxEndpoint.client_id` and `secret_key` use `EncryptedTextField` from `django-encrypted-model-fields`. They require `FIELD_ENCRYPTION_KEY` to be set.
11. **`TimestampedModel` base** — All domain models should extend `TimestampedModel` from `odl_video.models`, which provides `created_at`, `updated_at`, and a custom manager with auto-updated `updated_at` on `.update()`.
12. **JS test files must match `*_test.js`** — The test runner glob is `static/**/*/*_test.js`. Files not matching this pattern are silently ignored.
