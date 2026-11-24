# PHILOS Phase 1 Security and Configuration Audit

**Status:** Stage 1 (secrets and configuration stabilization) implemented after approval. Stage 2 API authorization, admin provisioning, and token-delivery changes remain findings and recommendations only. No migrations, database connections, container starts, or destructive operations were performed.

**Scope:** `PHILOS/` only. The `AstroPixel-Source/` reference tree was not inspected or modified for this phase. Secret values are intentionally omitted.

## Executive summary

Stage 1 removed embedded database credentials and insecure database/JWT defaults. Stage 2A removed public administrator initialization, hardcoded privileged credential instructions, and username-based administrator authorization. Administrator API access now depends on the persisted `is_superuser` field. Before deployment, the operator must safely verify or promote the existing administrator account; live account state was not inspected.

Remaining high-priority findings concern annotation authorization, chunk upload ownership, and consistent visibility checks for user-owned datasets. JWTs remain in browser `localStorage` and image tile query strings pending the separate token migration. No production database or deployed credential was contacted or changed.

No actual `.env` files were found during the audits. Root and nested ignore rules now exclude environment files while allowing `.env.example`; safe backend and frontend examples are present. No Git metadata exists at the PHILOS project root, so tracked-file status cannot be confirmed.

## Severity summary

| Severity | Current findings |
|---|---|
| **Critical** | No confirmed open Stage 2A code finding. Deployment must not proceed until the existing administrator role has been verified/promoted through the controlled CLI. |
| **High** | Annotation CRUD and some search routes lack access scoping; chunk uploads are not consistently authenticated/bound to an owner; dataset details, previews, status, reprocessing, and several tile helpers need consistent visibility checks. These are Stage 2B. |
| **Medium** | JWTs remain in `localStorage` and tile query strings; public metrics and potentially verbose errors need review; no database migration workflow exists; process-local uploads/cache create multi-worker concerns. |
| **Low** | The admin CLI provisions only the initial administrator; additional administrator provisioning needs a separately reviewed operator path. Stage 2A tests are present but could not be collected in this environment because runtime dependencies are missing. |

Severity reflects code findings and the deployment gate; it does not assert that any prior credential was deployed or used. No deployment/database was contacted.

## 1. Secret and configuration audit

### Backend settings and database

At initial audit, `Backend/app/config.py` defined a default remote PostgreSQL connection with embedded credential material and separately defined database connection fields, including a password default. Stage 1 removed these defaults. `Backend/app/database.py` passes `settings.DATABASE_URL` directly to SQLAlchemy when imported, but that setting is now required explicitly and validated before use. The credential is not repeated here.

**Finding — Critical (configuration remediated in Stage 1):** A credential was committed in application source. Its present deployment/use status remains unknown. Stage 1 removed it from application defaults and requires an explicit database URL. Operators should assess credential rotation separately; this code change does not assert whether it was deployed or rotate it. Never print database URLs or passwords.

### JWT

At initial audit, `SECRET_KEY` had a placeholder fallback in `config.py`. Stage 1 removed that fallback and now requires a value of at least 32 characters with a basic diversity/placeholder check. `services/auth.py` continues to use the configured value for signing and verification. `HS256` and a 30-minute access-token lifetime remain unchanged. There is no evidence here of key rotation, revocation, or refresh-token rotation.

**Finding — High (configuration remediated in Stage 1):** Missing, short, or common placeholder signing secrets now fail configuration validation with a generic error. The configured secret is externally supplied. Keep algorithm selection fixed to the intended allowlisted algorithm rather than accepting arbitrary deployment values. Add key rotation/revocation strategy before changing token format.

### Docker Compose

At initial audit, `Backend/docker-compose.yml` fell back to weak database credentials and a placeholder JWT secret. Stage 1 removed those credential fallbacks and makes the settings required. Compose still makes the database service port externally reachable through its existing host mapping, which was preserved as instructed.

**Finding — High (credential defaults remediated in Stage 1):** Compose now uses required-variable interpolation for database URL, database password, and JWT secret. The database port mapping remains unchanged; restrict it separately if the operator's deployment topology allows. Keep production deployment secrets in its secret manager and never bake them into images.

### Environment-file policy and templates

No actual `.env` files were present in `Backend/` or `Frontend/` during inspection. Stage 1 added a root `.gitignore` plus safe backend/frontend `.env.example` files. Existing nested ignore files remain unchanged. Example templates contain placeholders only; actual environment files must stay private. Ignore rules do not untrack files already committed, and Git metadata is unavailable here to verify tracked-file status.

**Finding — Low/Medium (addressed in Stage 1):** Root and nested ignore rules exclude environment files and generated local data while explicitly permitting `.env.example` templates. Separate backend/frontend examples are present.

### Frontend configuration

The frontend API client reads `VITE_API_BASE_URL` and falls back to a local API URL. This is an endpoint address, not a backend credential. No backend secret is intended to be shipped in frontend environment variables; all `VITE_*` variables are client-visible at build time and must be treated as public.

**Finding — Low:** Document the API base URL as public configuration, validate production build configuration, and do not place database, JWT, cloud-storage, or admin secrets in `VITE_*` variables.

### Admin defaults

At initial audit, the backend identified administrators by username and exposed an unauthenticated initializer with a source-defined credential. The administrator creation utility and frontend admin login materials also contained privileged defaults. Stage 2A removed the initializer and hardcoded credential instructions, and switched authorization to the persisted superuser flag. This audit does not assume whether any prior credential was deployed or used.

## 2. API authorization audit

Legend: **Auth** means a valid login/token is required. **Authorization** means an explicit role/permission or policy check. **Ownership** means the authenticated user is compared to the target resource owner. A public route may be intentional for demo content; the issue is whether it limits results to public/demo data.

### Annotation and search routes

All routes below are in `Backend/app/routers/annotations_simple.py` or `search.py` and are currently unauthenticated.

| Endpoint | Auth? | Authorization? | Ownership check? | Potential vulnerability and recommended correction |
|---|---:|---:|---:|---|
| `GET /api/annotations/{dataset_id}` | No | No | No | Returns annotations for any existing dataset; optional caller-supplied `user_id` is only a filter. Require auth for private data or restrict query to public/demo datasets; scope private results by owner/collaboration policy. |
| `POST /api/annotations` | No | No | No | Anonymous callers can add annotations to any dataset and assign a chosen `user_id`. Derive user identity from token; enforce write access to the dataset and validate geometry/limits. |
| `PUT /api/annotations/{annotation_id}` | No | No | No | Any caller can change any annotation. Require authentication and annotation ownership or dataset-editor/admin permission. |
| `DELETE /api/annotations/{annotation_id}` | No | No | No | Any caller can delete any annotation. Apply the same ownership/role policy as update and record audit metadata. |
| `GET /api/search` | No | No | No | Searches all annotations and may expose private labels/descriptions. Limit search to public/demo data or authorized datasets. |
| `GET /api/search/spatial` | No | No | No | Can query annotation geometry without dataset access filtering. Scope by authorized dataset. |
| `GET /api/search/similar` | No | No | No | Reference and results are not access-filtered. Verify access to reference dataset and constrain candidate results to accessible datasets. |
| `POST /api/compare` | No | No | No | Accepts arbitrary dataset IDs and returns metadata. Require access to every requested dataset or expose only public/demo datasets. |
| `GET /api/search/datasets` | No | No | No | Search is not filtered by user ownership/demo visibility, so private datasets may be discoverable. Apply the same visibility scope as dataset listing. |

### Dataset and upload routes

These routes are in `Backend/app/routers/datasets.py`.

| Endpoint | Auth? | Authorization? | Ownership check? | Potential vulnerability and recommended correction |
|---|---:|---:|---:|---|
| `POST /api/datasets/upload/init` | No | No | No | Creates upload state and temp directory. Require auth and create a session bound to that user with strict validated size/chunk limits and expiry. |
| `POST /api/datasets/upload/chunk` | No | No | No | Writes arbitrary chunks for any known upload ID; session ID is effectively a bearer capability and has no user binding. Require auth and verify creator, index/range/aggregate size; use opaque unpredictable session IDs and safe storage keys. |
| `POST /api/datasets/upload/complete` | Yes | Partial | No session-owner check | Requires login and assigns dataset to current user, but does not establish that the completing user initiated the session. Bind session to owner and verify final byte count, chunk indices, filename/path safety, and quotas. |
| `DELETE /api/datasets/upload/{upload_id}` | No | No | No | Any caller knowing an ID can cancel/delete its temp upload. Require auth and verify session owner. |
| `POST /api/datasets/upload` | Yes | Partial | Sets new owner | Requires login and assigns ownership to uploader. Add rate/quota checks and robust content/type validation; safely normalize filenames and bound processing resources. |
| `POST /api/datasets/from-folder` | No | No | No | Filesystem processing operation is reachable without an admin/maintenance role. Make it an operator-only task or require a strong admin permission. |
| `GET /api/datasets` | Optional | Partial | Yes for list | Authenticated user listing filters to own datasets; guests see demo rows. This is a good list-level scope, subject to correct role/policy semantics. |
| `GET /api/datasets/{dataset_id}` | No | No | No | Returns details for any dataset ID. Require an access check or limit to demos. |
| `GET /api/datasets/{dataset_id}/tile-status` | No | No | No | Reveals processing and cloud-state information for any dataset. Scope to accessible datasets. |
| `PUT /api/datasets/{dataset_id}` | Yes | Yes | Yes | Requires login; blocks demo mutation and checks owner. Admin override policy is not apparent. Retain checks and centralize authorization. |
| `DELETE /api/datasets/{dataset_id}` | Yes | Yes | Yes | Requires login; blocks demo deletion and checks owner. Ensure all associated storage cleanup remains scoped and transactional. |
| `GET /api/datasets/{dataset_id}/status` | No | No | No | Reveals processing state for any ID. Scope to accessible datasets. |
| `POST /api/datasets/{dataset_id}/reprocess` | No | No | No | Triggers expensive processing with no auth/ownership check. Require owner or admin permission, quotas, and idempotency. |
| `GET /api/stats` | No | No | No | Exposes aggregate platform statistics. Decide whether public metrics are intended; otherwise require admin permission and avoid user-level detail. |
| `GET /api/datasets/{dataset_id}/preview` (preview router) | No | No | No | Preview route checks dataset existence but not visibility before serving/redirecting to preview. Restrict private dataset previews or make previews explicitly public. |

### Tile routes

Tile routes are in `Backend/app/routers/tiles.py`; static mounts are configured in `main.py`.

| Endpoint | Auth? | Authorization? | Ownership check? | Potential vulnerability and recommended correction |
|---|---:|---:|---:|---|
| `GET /api/tiles/{id}/{z}/{x}/{y}.{format}` | Optional | Yes for non-demo | Yes for non-demo | Main tile handler checks demo visibility or requires an authenticated owner. Preserve this policy. Review cache keys and cache headers so private bytes cannot be served across users; `public` cache headers on owner-only tile responses are unsafe for shared intermediaries. |
| `GET /api/tiles/{id}/batch` | Optional | Partial/unclear | Must verify | Route accepts optional user context. Confirm every requested dataset is filtered by the same owner/demo policy before tile retrieval. |
| `GET /api/tiles/{id}/prefetch/{z}` | Optional | Partial/unclear | Must verify | Potential resource amplification and private tile access; enforce dataset access, zoom/tile bounds, quotas, and rate limiting. |
| `GET /api/tiles/{id}/cache-stats` | No | No | No | May reveal cache/usage details; require admin or scope/omit operational details. |
| `GET /api/tiles/{id}/preview` | No | No | No | Serves preview for any existing dataset, including non-demo. Apply dataset visibility checks. |
| `GET /api/tiles/{id}/info` | No | No | No | Returns dimensions, zooms, bounds, and a tile URL for any dataset. Apply same visibility policy. |
| Static `/tiles` and `/datasets` mounts | No | No | No | Files exposed under mounts bypass router dependency checks if private files are stored there. Confirm only public assets are mounted; keep private uploads outside static roots and use controlled handlers. |

### Authentication and user-management routes

Routes in `Backend/app/routers/auth.py`:

| Endpoint | Auth? | Authorization? | Ownership check? | Potential vulnerability and recommended correction |
|---|---:|---:|---:|---|
| `POST /api/auth/register` | No | No | N/A | Public registration is expected, but protect against abuse with throttling, validation, and verification policy. |
| `POST /api/auth/login` | No | No | N/A | Public by design; rate limiting and generic credential errors should be confirmed. |
| `GET/PUT /api/auth/me` | Yes | Self | Yes, through current-user dependency | Authenticated self-service routes; verify update schema cannot modify role/active/password hash fields. |
| `POST /api/auth/logout` | Yes | Self | Yes, by token user | Returns logout success but appears not to revoke a stateless JWT server-side. Document client-only logout or implement revocation/short-lived token strategy. |
| `POST /api/auth/refresh` | Yes | Self | Yes, by token user | Token refresh is allowed based on a valid access token; consider refresh-token rotation and revocation. |
| `GET /api/auth/verify` | Yes | Self | Yes, by token user | Appropriate identity check; avoid relying on client-stored role claims for authorization. |

User management routes in `admin.py`:

| Endpoint | Auth? | Authorization? | Ownership check? | Potential vulnerability and recommended correction |
|---|---:|---:|---:|---|
| `GET /api/admin/stats` | Yes | Yes | N/A | Protected by persisted `is_superuser` authorization through `get_current_superuser`. |
| `GET /api/admin/users` | Yes | Yes | N/A | Protected by persisted `is_superuser` authorization; minimize returned user fields. |
| `GET /api/admin/datasets` | Yes | Yes | N/A | Protected by persisted `is_superuser` authorization. |
| `DELETE /api/admin/datasets/{id}` | Yes | Yes | N/A | Protected by persisted `is_superuser` authorization. Preserve audit logging and safe cleanup. |
| `DELETE /api/admin/users/{id}` | Yes | Yes | N/A | Protected by persisted `is_superuser`; self-deletion and deletion of the last active administrator are blocked. |
| `GET /api/admin/activity` | Yes | Yes | N/A | Protected by persisted `is_superuser`; avoid returning internal exception details. |
| `POST /api/admin/init` | Removed | N/A | N/A | Route removed in Stage 2A; anonymous calls to the old path return 404. Use the operator-controlled CLI instead. |

## 3. Token security and migration plan

### Current behavior

- `AuthContext.jsx` stores the JWT and user JSON in `localStorage`.
- `api.js` reads the token and sends it in an `Authorization: Bearer` header for Axios requests.
- `ViewerCanvas.jsx` and `ComparisonView.jsx` append the JWT to tile/image URLs as a `token` query parameter so OpenSeadragon can load image resources.
- Backend `get_current_user` accepts query tokens in addition to bearer headers.
- Query strings can be retained in browser history, server/proxy/access logs, telemetry, caches, and referrer headers. They are more likely to leak than authorization headers. `localStorage` increases impact from any successful same-origin script injection.
- The main tile route sets long-lived `public` cache headers in at least one response path despite owner-specific authorization. Shared cache behavior must be reviewed before allowing private tile URLs to be cached publicly.

### Staged migration that preserves the viewer

1. **First enforce server policy without changing token transport:** ensure query tokens are only temporarily accepted by the tile image endpoints, never logged, and excluded from caching/referrers. Apply private/no-store semantics to authenticated tile responses and verify cache keys include identity or bypass shared caches.
2. **Use a same-origin authenticated image delivery path:** configure OpenSeadragon's AJAX tile loading to attach `Authorization` headers where supported, or fetch tiles through a same-origin API proxy that validates the bearer token and streams bytes. Keep the current URL tile source as a temporary compatibility path behind a feature flag during rollout.
3. **Move browser auth to secure cookies:** introduce short-lived access credentials in `HttpOnly; Secure; SameSite` cookies and CSRF protection for state-changing requests. Migrate API calls and tile loading to cookie-backed same-origin delivery. Do not use a JavaScript-readable cookie as a substitute.
4. **Support a brief transition window:** accept existing bearer headers and legacy query tokens only for a documented period; emit deprecation telemetry without recording token values. Once all supported viewer clients use headers/cookies, reject query-string tokens and remove the query parameter dependency.
5. **Invalidate/reissue credentials safely:** once secret management and authentication are stable, rotate signing keys with a controlled overlap or invalidate existing sessions. Avoid sudden signing-key changes that strand users without a planned re-login.

## 4. Database initialization and migration strategy

`database.py` calls `Base.metadata.create_all()` in application startup, then best-effort syncs dataset metadata from cloud storage. `create_all()` can create missing tables but does not apply reviewed schema evolution, column renames, data backfills, or safe constraint changes. No Alembic migration setup was found. Startup also attempts spatial-index creation. No migration or database command was run for this audit.

Recommended approach:

1. Add Alembic with a baseline revision representing the current deployed schema; do not assume a fresh empty database.
2. Compare the baseline against representative schemas using read-only introspection and have an operator review generated diffs.
3. Require a verified backup/snapshot and tested restore procedure before any production migration.
4. Run migrations as a separate, explicitly invoked deployment step with a migration lock; do not let every app worker mutate schema at startup.
5. Use expand-and-contract changes: add compatible columns/indexes, deploy compatible code, backfill in bounded batches, then remove obsolete schema in a later release.
6. Test upgrade and rollback/forward-recovery paths against disposable databases and a sanitized snapshot. Never run a reset/drop operation as a migration strategy.
7. Keep cloud metadata sync idempotent and separate it from DDL; review failure behavior and transaction boundaries.

## 5. Testing plan

Create isolated test fixtures with temporary SQLite/PostgreSQL test databases and injected configuration. Do not use production credentials or production data.

| Area | Required tests |
|---|---|
| Authentication | Missing/invalid/expired JWT is rejected on protected routes; disabled account rejected; password is hashed; registration/login throttling; `/me` cannot change role or account status; refresh and logout behavior matches documented revocation policy. |
| Annotation ownership | Anonymous create/update/delete rejected; user A cannot read/write/delete user B's private annotations; caller-supplied `user_id` cannot spoof identity; demo annotation policy behaves as intended; search and spatial/similar endpoints never cross visibility boundaries. |
| Dataset ownership | Users see only own plus explicitly public/demo datasets; detail, preview, status, search, comparison, and statistics follow the same visibility policy; owner may update/delete own dataset; another user and guests may not; demo dataset mutation remains blocked. |
| Chunk upload authorization | Init/chunk/complete/cancel require the same authenticated owner; foreign user cannot append, complete, or cancel; malformed indices, missing/duplicate chunks, oversized total, unsafe filename, expired session, and cross-worker session behavior are safely handled. |
| Admin authorization | Non-admin with arbitrary username denied; `is_superuser`/role policy is enforced consistently; public initialization is absent/disabled; operator provisioning cannot leak credentials; no self-delete/last-admin lockout. |
| Database configuration | Missing/placeholder `DATABASE_URL` fails at startup without printing secret material; missing/weak `SECRET_KEY` fails closed; `.env` loads only in local configuration; Compose refuses missing required secrets; logs/errors redact URLs and credentials. |
| Image tile access | Demo tiles accessible per public policy; private tiles require owner; other user and anonymous access denied; batch/prefetch/info/preview/static paths follow policy; query tokens rejected after migration; authenticated tile cache cannot cross users or be shared publicly. |
| Migration safety | Baseline and upgrade revisions work on disposable DBs; migration is explicit and not run by app startup; schema assertions and restore/recovery steps documented. |

## 6. Recommended remediation order

1. Rotate any credential embedded in source as a precaution, without asserting deployment status; remove source/default credentials and require injected DB/JWT secrets.
2. Disable/remove public admin initialization and remove all hardcoded admin password material; switch admin authorization to explicit role fields.
3. Close authorization gaps on annotations, chunk sessions, filesystem ingestion, dataset lookup/preview/status/reprocess, search, compare, and tile helper endpoints; use a shared resource-visibility policy.
4. Review private tile cache headers and static mounts before enabling private dataset access in any shared deployment.
5. Introduce secure token delivery in stages, keeping viewer compatibility until header/cookie-based tile fetches are confirmed.
6. Add Alembic and the tests listed above; only then plan a separately reviewed database migration/deployment.
7. Add root ignore rules and safe env examples; update documentation after behavior is finalized.

## Stage 1 implementation status

### Completed

- Removed database URL, database password, and remote database host defaults from application configuration. `DATABASE_URL` is now required and validated as a SQLAlchemy URL; `DB_HOST` and `DB_NAME` are derived from it for existing operator tooling.
- Removed the JWT signing key fallback. `SECRET_KEY` is required and must be at least 32 characters, contain at least 16 distinct characters, and not match common placeholder patterns. Configuration is validated when settings are instantiated during application import/startup. Startup errors are generic, and Pydantic validation output is configured to hide input values.
- Docker Compose now requires `DATABASE_URL`, `SECRET_KEY`, and `DB_PASSWORD` rather than substituting weak fallback credentials. Existing ports and service wiring were retained.
- Removed a duplicated/malformed Dockerfile command while preserving the existing Uvicorn startup command.
- Added safe backend and frontend environment examples. The frontend example contains only the public API base URL.
- Added root `.gitignore` rules for environment files (with `.env.example` exceptions), common Python/Node build artifacts, temporary files, logs, and IDE files. Existing nested ignore files were preserved.

### Files created

- `.gitignore`
- `Backend/.env.example`
- `Frontend/.env.example`

### Files modified

- `Backend/app/config.py`
- `Backend/docker-compose.yml`
- `Backend/Dockerfile`
- `README.md` (configuration setup guidance)
- `docs/security/SECURITY_AUDIT.md`

`Backend/.gitignore` and `Frontend/.gitignore` were inspected and left unchanged. No actual `.env` file was created or overwritten.

### Configuration required before startup

Set these values in the process environment or in a local `Backend/.env` file (created from `Backend/.env.example`):

- `DATABASE_URL`: required SQLAlchemy URL for the intended PostgreSQL or SQLite database. For Compose, it must address the Compose database service and use the same database name, username, and password as the database service settings.
- `SECRET_KEY`: required unique random signing secret, at least 32 characters, with sufficient randomness. Generate a new development value locally; retain any existing production signing key under operator control. This change does not rotate keys.
- `DB_PASSWORD`: required by Docker Compose for its Postgres service; it must match the password component in `DATABASE_URL` for that service.

`CORS_ORIGINS`, `DEBUG`, `LOG_LEVEL`, and the optional S3/R2 variables are documented in the example. `VITE_API_BASE_URL` is the only frontend example setting and is public client configuration. To use Compose, run it from the `Backend/` directory so Compose reads that directory's `.env` for interpolation. Replace all placeholders before startup; examples are not valid credentials.

### Validation performed

- Python syntax was checked without bytecode output: passed for all backend Python files.
- Configuration was exercised with a dummy SQLite URL and dummy random signing key; missing database URL and weak signing key were rejected: passed. No database connection was made.
- Docker Compose CLI was unavailable, so interpolation/config validation could not be run. Static YAML parsing passed with PyYAML; no containers were started.
- Secret exposure scan covered the PHILOS project source and docs. Secret values were suppressed; this report does not reproduce them.
- Remaining credential references are limited to admin provisioning/login code and generic documentation/example placeholders. The placeholder URLs in documentation/examples are not live credentials; no secret values are included in this report. Admin credential remediation is deferred to Stage 2.
- Git status/diff could not be obtained because the PHILOS workspace has no Git metadata. Changed files were reviewed directly after editing.
- Frontend build was not run because frontend configuration was not changed in a way requiring a build and dependencies/build output were not needed for these changes.

### Tests not executed

- No application test suite was present or run.
- No database connection, migration, reset, or data operation was performed.
- No Docker container was started or recreated.
- No production or deployed credential was inspected for use or rotated.
- No frontend build was run.

### Remaining security issues after Stage 1 (historical; Stage 2A status follows)

- **Critical/High:** Source-defined privileged credentials remain in the admin initialization route and `Backend/create_admin.py`; a default admin password is also displayed/referenced in frontend/admin materials. These are Stage 2 privileged account provisioning/authentication issues and were not changed under this phase's strict scope.
- **High:** Public admin initialization and username-based admin authorization remain unchanged.
- **High:** Annotation access controls, chunk upload ownership, dataset visibility consistency, search/comparison scope, tile helper access, and private tile cache behavior remain to be addressed in Stage 2.
- **Medium:** JWTs remain in `localStorage` and tile query strings until the separately approved viewer-compatible token migration.
- **Medium:** Application startup still uses `create_all()` rather than a reviewed migration workflow; no database schema work was authorized or performed.
- **Low:** The root README's weak JWT example was replaced with the required-secret setup guidance. Admin provisioning code and frontend admin UI still contain privileged credential references; remediate those together in Stage 2 and review associated documentation then.

### Manual operator actions

1. Prepare a local `Backend/.env` from the example and replace every placeholder. Keep the real file untracked and out of shared logs/screenshots.
2. For Compose, ensure `DATABASE_URL` points at the Compose Postgres service and its username/database/password agree with `POSTGRES_USER`, `POSTGRES_DB`, and `DB_PASSWORD`.
3. Supply a unique random `SECRET_KEY` in each environment. Do not change deployed signing keys as part of this code update; schedule any rotation separately if desired.
4. Before startup, verify the intended database target from the operator's secret manager/configuration without printing the URL or password.
5. Do not invoke the existing admin creation/reset utilities as part of this stage; have Stage 2 remediate privileged credentials and provisioning first.

## 7. Stage 2A administrator authentication and provisioning

### Findings and changes

- The prior administrator initializer was a public API route with a source-defined credential. The route has been removed; anonymous requests to its old path receive the framework's normal not-found response.
- The previous admin check compared usernames. Backend administrator endpoints now depend on the existing `get_current_superuser` dependency, which requires a valid active user and checks the persisted `User.is_superuser` flag.
- The `User` model already contains a persisted `is_superuser` Boolean. No new column or schema migration was required or performed.
- `UserResponse` now includes `is_superuser`, populated from the authenticated backend user record. The frontend uses this response field for administrator navigation; the backend remains authoritative for every admin API request.
- The administrator user deletion path now protects the last active superuser rather than a particular username.
- The operator CLI (`Backend/create_admin.py`) prompts for identity interactively and obtains the password via hidden input. For a new account it requires a repeated password and applies the existing password hashing helper. For an existing account it verifies the current password and promotes the persisted role without changing the password or account identity. It refuses to run if an administrator already exists. PostgreSQL advisory locking and SQLite immediate transactions serialize first-admin provisioning.
- Hardcoded privileged password material/default credential instructions were removed from the admin route, CLI, frontend admin login materials, and root setup README. The administrator login forms now accept an operator-supplied email and password and use the backend `is_superuser` response field. No password or token is returned in provisioning output.

### Files modified

- `Backend/app/routers/admin.py`
- `Backend/app/schemas.py`
- `Backend/create_admin.py`
- `Frontend/src/pages/AdminLoginPage.jsx`
- `Frontend/src/pages/LoginPage.jsx`
- `Frontend/src/components/common/ProtectedRoute.jsx`
- `docs/security/SECURITY_AUDIT.md`

### Files created

- `Backend/tests/conftest.py`
- `Backend/tests/test_admin_security.py`

### Tests executed and results

- Python AST syntax parsing for all backend source and test files: passed.
- `pytest -q tests/test_admin_security.py` was attempted. Collection stopped before any test ran because this environment lacks the backend runtime dependency `aiofiles`; the environment also lacks the authentication dependencies `passlib` and `python-jose`. No packages were installed.
- No database was connected. The test fixtures use an isolated in-memory SQLite database and temporary directories when run in an environment with the project dependencies installed.
- Frontend build was not run because `Frontend/node_modules` is absent. Node is available, but dependencies were not installed.
- Git status/diff is unavailable because the PHILOS directory has no Git metadata. Changed files were reviewed directly.

### Tests not executed

- Ten tests covering anonymous initialization, admin authorization, username/role spoofing, operator provisioning, password hashing, and existing user login are present but did not execute because test collection could not import the missing runtime dependencies.
- No live or production database, migration, reset, or account operation was performed.

### Manual operator actions required before deployment

1. Supply the existing intended `DATABASE_URL` and `SECRET_KEY` from the operator's secret configuration; this change does not inspect or rotate deployed secrets.
2. Before deploying the backend role-check change, run `python create_admin.py` in a controlled environment pointed at the intended database. If the existing administrator's `is_superuser` flag is already true, the tool refuses to make changes. If the existing administrator has the flag unset, use that account's current email, username, and current password twice in the hidden prompts to promote it. The command does not alter the password. If the operator cannot verify the existing account, do not deploy the role-check cutover until access is safely established.
3. If no administrator exists, use the same command to create the first administrator with a new password entered through hidden prompts. Do not pass passwords as command-line arguments or run the command against production as part of this code change.
4. Run the new test suite in a development environment with `Backend/requirements.txt` and pytest installed before deployment.

### Remaining risks

- The operator must verify/promote the existing administrator before deployment; otherwise an account previously authorized only by username may lose admin access. This is an explicit rollout gate because live account state was not inspected.
- The new CLI provisions only the initial administrator. Adding further administrators should use a separately reviewed operator workflow; public role assignment is intentionally unavailable.
- Annotation permissions, chunk-upload ownership, dataset visibility, search/comparison scope, tile helper access, and private tile caching remain Stage 2B work.
- JWT storage in `localStorage` and query-string tile tokens remain for the separately scoped token migration.

## Stage 2B API authentication, authorization, and ownership

### Status and policy

Stage 2B implementation is complete for the inspected annotation, dataset, tile helper, search/comparison, and chunk-upload routes. No database schema change or migration was required. The user approved this demo policy: demo datasets and annotations are publicly readable; an authenticated creator owns writes to their annotations. Admin permissions use the persisted `User.is_superuser` field.

- **Demo resources:** publicly readable. Authenticated users may create annotations on demos. Only an annotation creator or an admin may update/delete a demo annotation. Ordinary users cannot update, delete, or reprocess a demo dataset.
- **Private datasets:** visible to their owner and admins. Only the owner or an admin may modify or reprocess them. Outsiders receive 404 for private dataset lookups.
- **Private annotations:** visible through their private parent dataset to its owner/admin. Annotation creators can update/delete their own annotations; the private dataset owner and admin may curate them.
- **Search and comparison:** annotation full-text, spatial, and similar search only return annotations on visible datasets; references and explicitly requested IDs are checked. Dataset search is visibility scoped. Comparison rejects duplicate IDs and returns 404 if any referenced dataset is missing or inaccessible.

### Endpoint changes

- `GET /api/annotations/{dataset_id}` checks parent dataset visibility; its optional user filter only filters results and does not grant access.
- `POST /api/annotations` requires authentication, checks dataset write eligibility, and always sets `user_id` from the authenticated principal.
- `PUT` and `DELETE /api/annotations/{annotation_id}` require authentication, check parent visibility, and enforce creator/admin or private dataset owner/admin permission.
- Dataset listing, details, processing status, tile status, previews, and statistics apply the same demo/owner/admin visibility policy. Update, delete, and reprocessing additionally enforce write access.
- `/datasets/from-folder` now requires backend superuser authorization.
- Tile batch, tile, preview, prefetch, info, and cache-stat helper routes check dataset visibility. Private tile/preview responses use private no-store headers and are proxied through the authenticated API where possible; private resources are not redirected to public object URLs.
- Public `StaticFiles` mounts for `/tiles` and `/datasets` were removed because they bypassed route-level authorization. Guarded API tile and preview routes remain available.
- Chunked upload initialization requires authentication and binds a session to its owner. Every subsequent chunk, completion, and cancellation verifies that owner. Sessions expire after 24 hours; chunk index, byte count, aggregate size, filename, upload state, and assembly size are validated. Per-session locks serialize concurrent operations and cleanup is constrained to the configured temp directory.
- Ordinary dataset upload also validates the client filename and enforces a configured size limit while streaming.

### Files changed

- Modified: `Backend/app/routers/annotations_simple.py`, `Backend/app/routers/datasets.py`, `Backend/app/routers/search.py`, `Backend/app/routers/tiles.py`, `Backend/app/main.py`, `Backend/tests/conftest.py`, `Backend/tests/test_dataset_authorization.py`, `docs/security/SECURITY_AUDIT.md`.
- Created: `Backend/app/services/authorization.py`, `Backend/tests/test_resource_authorization.py`, `Backend/tests/test_chunk_upload_security.py`.

### Tests and validation

- Added isolated tests for anonymous/owner/cross-user annotation access and mutation, spoofed annotation user IDs, demo annotation behavior, search scoping, dataset listing/details/status/mutation/reprocessing/statistics/previews, dataset search/comparison, and chunk upload authentication/ownership/index/size/expiry behavior.
- Requested pytest groups were attempted, including the search/comparison and chunk upload tests. Each attempt stopped at test collection because the environment lacks the `aiofiles` runtime dependency. No test body executed; dependencies were not installed.
- No production or operator database was contacted, no database contents were changed, no migration was run, and no service/container was started.
- Python syntax and final working-tree checks are recorded in the implementation handoff. Frontend build and browser validation were not run because frontend code and configuration were not changed.

### Remaining risks and manual actions

- Chunk upload sessions and locks are held in process memory. Multi-worker deployments must use one worker or sticky routing to ensure follow-up requests reach the owning process. A shared session store would require separate design approval.
- Existing private objects in a publicly readable object-storage bucket may remain directly accessible outside PHILOS; route checks cannot revoke public bucket/object permissions. Operators should confirm bucket policy independently before relying on API ownership controls.
- The Python test suite must be run in an environment with the project's declared backend dependencies installed before deployment. No production rollout, credential rotation, tile token migration, or Stage 2C work is included here.

## Stage 2B.2 storage isolation and frontend hardening

### Public and private storage separation

- `AWS_BUCKET_NAME` remains the public/demo bucket, and only demo datasets are uploaded there. Public URL generation now requires an explicit public-asset flag; the public tile cache path is used only by demo routes.
- Private assets use the distinct `PRIVATE_S3_BUCKET_NAME` bucket. It uses the configured S3-compatible account credentials and endpoint, but is never passed to a public URL builder. Private preview and tile API routes first apply dataset visibility checks, then fetch only from this private bucket. Private responses retain `private, no-store` cache metadata.
- Private cloud uploads are enabled only when `PRIVATE_S3_BUCKET_NAME` differs from `AWS_BUCKET_NAME` and `PRIVATE_S3_BUCKET_PRIVATE_ACCESS_CONFIRMED=True`. That boolean is an operator attestation, not a remote policy check. The application cannot prove bucket policy from configuration alone. If confirmation is absent or the bucket name is invalid, private uploads remain local; authenticated routes use local files, and report unavailable when known legacy cloud-only files have no local copy. Private routes never fall back to the public/demo bucket.
- Local tile and preview files remain supported. Public demo cloud previews are served locally when available; otherwise the backend checks the canonical demo object key before redirecting. An absent object yields 404 and a storage request failure yields 503.
- The same bucket name and object-key layout were used by older releases for both visibility classes. No objects were read, moved, deleted, or migrated by this change. Existing private objects may still be directly readable if the old bucket/domain policy allows it; private cache metadata does not revoke that access.

### Required environment configuration

New optional backend variables are documented in `Backend/.env.example` and passed through `Backend/docker-compose.yml`:

- `PRIVATE_S3_BUCKET_NAME`: a dedicated bucket distinct from `AWS_BUCKET_NAME`.
- `PRIVATE_S3_BUCKET_PRIVATE_ACCESS_CONFIRMED`: default `False`; set to `True` only after an operator independently verifies that the dedicated bucket has public access disabled and its policy grants access only to the application.

With either setting absent or confirmation false, new private datasets remain local. The code validates a confirmed bucket name and rejects using the public bucket as the private bucket. It does not inspect a real storage policy and must not be treated as proof of deployment security.

### Existing private object transition plan

1. Inventory legacy private dataset IDs and their tiles/previews in the old shared bucket without deleting or moving any objects.
2. Independently inspect and document the actual old bucket/domain policy. Do not infer it from PHILOS configuration.
3. Provision a distinct private bucket and verify its policy denies public reads. Set the new variables only after that review.
4. Back up and plan a controlled migration of each legacy private object to the private bucket; this code intentionally does not migrate them automatically.
5. Verify API retrieval with owner and non-owner accounts, local fallback, and object policy. Keep the old objects until a separate operator-approved cleanup plan is complete.

### Metadata sanitization and logging

- Dataset API responses allowlist imagery metadata fields: dimensions, band count/details, projection, geotransform, bounds, zoom, driver, and pixel size. Storage URLs, upload/error text, object flags, local paths, and all unapproved fields are omitted. The allowlist is applied through `DatasetResponse`, including nested dataset responses.
- Storage upload failures persist only a generic message. Storage initialization, upload, deletion, and metadata logs no longer print bucket names, endpoints, object URLs, local paths, or raw storage exception text.

### Frontend preview lifecycle

- `Home` and `ViewerInfo` use `useDatasetPreview`. Private previews use the authenticated API client and blob URLs; public demos continue to use the public preview route.
- The hook associates results with a dataset/source key, ignores stale requests, revokes a late stale blob immediately, and revokes the active object URL during effect cleanup on replacement or unmount. UI error state resets when dataset/source changes; failures render the React-managed placeholder.
- No frontend test runner or component testing dependencies are configured. The frontend has a production `build` script and lockfile, but `node_modules` is not present in the reviewed environment. The smallest follow-up is to add a focused Vitest + React Testing Library test setup for the hook and preview consumers, then run the existing locked production build.

### Validation status and residual risks

- Backend tests use isolated in-memory SQLite fixtures and fake S3 clients. The environment has no Python 3.11 (only Python 3.12.3), and backend test collection is blocked by missing `aiofiles`; no test bodies have been verified in this environment. The Dockerfile targets Python 3.11 but does not include pytest or test sources.
- The current bucket policy is unknown. Operators must verify both new and legacy bucket policies directly. Existing public cache entries or copies of legacy private objects may remain until the separately reviewed transition is completed.
- No database, migration, Docker service, GitHub, or real storage service was accessed for Stage 2B.2.

## Stage 2B.3 critical security corrections

### Dataset response cache isolation

- The process-wide response cache no longer includes `/api/datasets` paths. This covers the dataset list and nested detail/status/preview metadata routes before any response can be placed in or retrieved from the shared cache.
- All `/api/datasets` responses receive `Cache-Control: private, no-store`, including anonymous demo listings. This deliberately disables shared caching for these routes; the public demo data remains available but is not served from a cross-user cache.
- The health endpoint remains the only application-level cached route. Its response is not user- or dataset-specific.
- Cache tests exercise owner detail access followed by foreign-user and anonymous requests, and ensure owner/foreign/anonymous dataset listings stay scoped.

### Docker data volume mapping

- `Backend/Dockerfile` keeps `WORKDIR /home/user/app`; `Backend/app/config.py` resolves `BASE_DIR` to `/home/user/app` in that image.
- Compose now mounts host `Backend/uploads`, `Backend/tiles`, `Backend/datasets`, and `Backend/temp` to `/home/user/app/uploads`, `/home/user/app/tiles`, `/home/user/app/datasets`, and `/home/user/app/temp`, respectively. These match the paths used for source uploads, generated tiles, previews, and temporary upload sessions. The mounts are sibling directories and do not overlap application code.
- Containers were not started. Operators should validate host permissions and confirm bind-mounted files survive a disposable local container recreation before deployment.

### Cleanup failure and retry behavior

- Cloud delete helpers now surface unavailable or failed operations instead of reporting success. S3 multi-object delete responses containing per-object errors are treated as incomplete; raw service details are not returned.
- Dataset deletion removes cloud assets from the dataset's matching tier before local assets, then removes the database row. Any cloud or local failure aborts before row deletion. Operations are idempotent so an operator can retry against the retained dataset ID after partial cleanup.
- Expiry cleanup retains the database row unless all asset cleanup succeeds. A failed cleanup is retried on a later scheduler pass. If cloud deletion succeeded but local deletion failed, the retry repeats cloud deletion safely and continues with remaining local files.
- Admin user deletion now stops if any owned dataset could not be safely deleted, retaining the user and the dataset row that needs retry. Earlier datasets in the same request may already have been deleted successfully; the remaining user/dataset records permit a subsequent retry.
- Legacy private dataset markers (`tiles_uploaded_to_cloud` and `preview_url`) stop destructive deletion. Private cloud markers (`private_tiles_uploaded_to_cloud` and `private_preview_uploaded`) require private storage availability before deletion. Private routes still never query the legacy public bucket. Unknown legacy objects without markers cannot be identified automatically.

### Frontend metadata compatibility

- `ViewerInfo` now reads `dataset.extra_metadata`, matching the dataset response schema. This metadata is already sanitized by the response allowlist; storage URLs, errors, storage flags, and internal paths remain omitted. Nested imagery values are rendered as JSON strings so React does not receive raw objects as children.
- No frontend test runner is configured, and dependencies are not installed in the current environment. A focused hook/component test requires a project-approved frontend test setup before it can be executed.

### Stage 2B.3 validation and remaining requirements

- Added isolated backend tests for cross-principal dataset cache behavior, private list isolation, local deletion failure/retry, cloud deletion failure/retry, expiry cleanup retry, and legacy marker retention.
- Static Python syntax validation and JavaScript syntax checks are run for this stage; pytest collection may remain blocked by missing backend dependencies. No database, storage service, or container is contacted.
- The private bucket confirmation setting remains an operator attestation, not a policy verification. Operators must verify the actual private bucket policy and plan legacy object inventory/migration independently. Existing legacy public-bucket objects are not automatically moved or deleted.
- Local fallback persistence now maps to the Docker image's resolved directories, but host permissions and deployment-level persistence still require an operator check.

## Stage 2B.3.1 private response cache headers and test isolation

### Private response headers

- Private dataset responses under the configured `/datasets` API prefix continue to bypass process caching and receive `private, no-store`.
- Private tile batch responses and private tile info, prefetch, and cache-stat responses now receive `private, no-store`. A batch request contains one dataset ID only; it cannot combine public demo and private dataset assets. Demo-only batch responses retain their public behavior.
- Dataset search, statistics, comparison, annotation-by-dataset, annotation text/spatial/similarity search, and admin GET responses receive `private, no-store` when they contain private resource data. Demo-only public responses do not receive the new private directive.
- Private tile storage failure responses also carry `private, no-store`; authorization and dataset visibility checks are unchanged.

### Test storage isolation

- `Backend/tests/conftest.py` sets `USE_S3=False`, clears all public and private bucket/endpoint credentials, sets private access confirmation to false, and assigns upload/tile/dataset/temp paths under the OS temporary directory before application modules are imported.
- An assertion test verifies the ordinary test configuration cannot enable public or private cloud storage. Tests that exercise cloud behavior use fake S3 clients or mocked storage methods; no real storage service is required.
- Focused tests cover private batch and search headers, private tile helper headers, annotation search, dataset stats, admin stats, and preservation of demo-only response behavior.

### Legacy object handling

- Objects from the former shared bucket whose legacy markers are absent may be orphaned or inaccessible to PHILOS. Private routes must never retrieve them from the old public bucket, whether markers are present or absent.
- Operators must inventory legacy keys with provider-side administrative tools, verify the actual old bucket/domain policy, and plan any migration or deletion as a separate reviewed operator procedure.
- PHILOS does not automatically migrate, delete, or expose legacy objects. The application cannot identify every unmarked object from dataset metadata alone.

## Stage 2B.1 integration corrections

### Preview authorization and URL handling

- Private previews in the dataset card and viewer information panel are fetched as blobs through `GET /api/tiles/{dataset_id}/preview`. The existing API client's bearer-token interceptor supplies authentication; the browser renders a temporary object URL and revokes it when the component changes or unmounts.
- Demo previews continue to load through the public preview API route, which may redirect to the configured public demo asset URL. Missing or failed private preview requests resolve to the existing placeholder state.
- Dataset API responses now omit `extra_metadata.preview_url`. The frontend no longer reads storage URLs from metadata. Cloud upload logging no longer writes the public URL, bucket name, or preview URL to logs unnecessarily.
- Preview and tile uploads now set public cache directives only when the dataset is marked demo; private uploads use `private, no-store`. This cache metadata does not make an object private if the bucket or custom domain allows public reads.

### Comparison and spatial-search contracts

- `getComparisonData` now sends `POST /api/compare` with `{ "dataset_ids": [...] }`, matching the backend contract and its existing visibility/ownership checks. Code search found no caller of this helper; the in-viewer comparison renders two tile viewers directly.
- `spatialSearch` now sends `GET /api/search/spatial` with `dataset_id` and `bbox` query parameters. Code search found no caller of this helper; the backend continues to apply the existing dataset visibility scope.

### Storage findings and deployment limitations

- S3-compatible uploads use predictable `tiles/{dataset_id}/...` and `previews/{dataset_id}_preview.jpg` keys. The service can construct public URLs from `R2_PUBLIC_URL`; demo routes may redirect to those URLs. Private routes proxy through the backend and use private no-store response headers.
- The application does not inspect a live bucket policy. If the configured public domain or bucket grants direct reads to these keys, private objects already stored there may be reachable outside PHILOS regardless of API authorization or cache-control headers. This review makes no claim about a deployed bucket's actual policy.
- Recommended deployment separation: put demo assets in a deliberately public bucket/domain and private user assets in a separate private bucket with public access disabled and server-side authenticated reads. If prefixes in a shared bucket are used instead, enforce the public/private boundary in the bucket policy and verify it independently. Existing private objects require an operator-planned inventory and migration; this change did not access or alter storage objects.

### Stage 2B.1 tests and environment

- Added isolated tests for public demo preview responses, authorized and unauthorized private preview access, missing previews, storage URL omission from dataset API metadata, comparison method/body, spatial search dataset scoping, and private/public preview upload cache metadata using a fake S3 client.
- Python 3.11 is not available in the inspected local environment; only Python 3.12.3 is installed. The backend Dockerfile targets Python 3.11. No dependency or system package was installed.
- Backend test execution remains blocked during collection by missing `aiofiles`; no test body executed. Run the backend suite in an isolated Python 3.11 environment matching the declared requirements and GDAL system runtime before deployment.
