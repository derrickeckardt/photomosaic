# Production Launch Punchlist

Status as of 2026-08-25. Supersedes the generic checklists in `DEPLOYMENT_GUIDE.md`
and `FILE_INDEX.md` (those are unverified boilerplate; this list is based on
reading the actual code).

Legend: **P0** = blocks launch entirely, **P1** = must fix before real users/money,
**P2** = production hygiene, **P3** = scale/later.

---

## P0 — Blocks launch

- [ ] **No storefront exists on the frontend.** `backend_api.py` has full
  product/order/checkout/Stripe endpoints, but `frontend_app.jsx` has no cart,
  checkout, product-purchase page, or Stripe.js/Elements integration. There is
  currently no way for a user to buy a print. Needs: product listing page,
  cart state, shipping address form, Stripe Elements checkout, order
  confirmation/history page.
- [ ] **Printful fulfillment is broken.** `send_to_printful()`
  (`backend_api.py:773-829`) opens the mosaic file (`files = {'file': open(...)}`,
  line 788) but never attaches it to the request — it POSTs `json=order_data`
  only, so the file handle is unused and leaked (never closed). It also points
  Printful at `/api/mosaic/<id>/image`, a route that doesn't exist (only
  `/download` exists). Paid orders will never actually get sent for printing.
  Fix: upload the image to Printful (or a public URL Printful can fetch, e.g.
  S3) correctly, and add error handling/retry + order-status update on failure.
- [ ] **Debug mode is hardcoded on.** `app.run(debug=True)` (`backend_api.py:931`)
  ignores `FLASK_ENV`/`DEBUG` env vars entirely. Running this as-is in
  production exposes the Werkzeug interactive debugger (remote code execution
  risk) and verbose tracebacks to end users. Fix: `app.run(debug=os.environ.get('FLASK_ENV') != 'production')`
  or better, don't use the dev server at all — run via gunicorn per the
  deployment guide, and drop `app.run()` from the production path entirely.

## P1 — Security / must-fix before real users or money

- [ ] **No CSRF protection.** Auth uses session cookies (`flask-login` +
  `CORS(..., supports_credentials=True)`), which is CSRF-exposed by default.
  Every state-changing endpoint (register, login, create/update/delete mosaic,
  create order, checkout) has no CSRF token. Add `flask-wtf` CSRF protection
  or move to a token-based auth scheme (e.g. JWT in an Authorization header —
  `PyJWT` is already a dependency but unused).
- [ ] **`CORS_ORIGINS` is documented but never read.** The deployment guide and
  `.env` template describe a `CORS_ORIGINS` variable; `backend_api.py` never
  references `os.environ.get('CORS_ORIGINS')`. `CORS(app, supports_credentials=True)`
  currently has no origin allowlist. Wire it up: `CORS(app, supports_credentials=True, origins=os.environ.get('CORS_ORIGINS', '').split(','))`.
- [ ] **Anonymous access to a private mosaic likely 500s instead of 403s.**
  `get_mosaic`/`download_mosaic` (`backend_api.py:452`, `:466`) check
  `not current_user or mosaic.user_id != current_user.id`. Flask-Login's
  anonymous user object is truthy, so `not current_user` is always `False`,
  and the code falls through to `current_user.id`, which doesn't exist on
  `AnonymousUserMixin` → `AttributeError` → 500. Fix: check
  `not current_user.is_authenticated` instead.
- [ ] **No rate limiting anywhere** — not on `/api/auth/login` or `/register`
  (brute-force/credential-stuffing risk), not on `/api/mosaic/create`
  (resource exhaustion: 500MB max upload, synchronous CPU-bound mosaic
  generation runs on the request thread). Add `Flask-Limiter` at minimum on
  auth and mosaic-create routes.
- [ ] **`SECRET_KEY` silently falls back to a hardcoded dev string**
  (`backend_api.py:33`) if the env var isn't set. Combined with debug mode,
  this is a real risk if the app is ever deployed without the env var
  correctly injected. Fail loudly instead: raise at startup if
  `SECRET_KEY` is unset and `FLASK_ENV=production`.
- [ ] **Mosaic generation is synchronous and unbounded.** A single request can
  upload up to 500MB across many tile images and generate up to 10000x10000
  output, blocking a worker thread for the duration. No async job queue
  (Celery/RQ) exists yet — acceptable for a soft launch with low traffic, but
  will produce request timeouts and worker starvation under any real load.
  At minimum, lower `MAX_CONTENT_LENGTH` to something realistic and add a
  request timeout; plan async processing before marketing push.
- [ ] **No image-content validation beyond file extension.** `allowed_file()`
  only checks the extension; Pillow will happily attempt to decode anything
  with that extension. Combine with no `Image.MAX_IMAGE_PIXELS` cap — a
  malicious "decompression bomb" upload can exhaust memory/CPU.

## P2 — Production hygiene / correctness

- [ ] **Two conflicting requirements files.** `DEPLOYMENT_GUIDE.md` step 3 says
  `pip install -r requirements.txt`, but that file only lists
  `Pillow/numpy/scipy` — none of Flask, Flask-SQLAlchemy, Flask-Login, Stripe,
  etc. The real backend deps are in `backend_requirements.txt`, which the
  guide's install step never references. Following the guide as written will
  break at `python backend_api.py`. Consolidate into one requirements file (or
  clearly document which is for the CLI tool vs. the web app) and fix the
  guide.
- [ ] **No `.env.example`.** The guide says `cp .env.example .env`; that file
  doesn't exist. `.env` is present but empty. Add a real `.env.example` with
  all the variables the guide already documents.
- [ ] **Non-jpg uploads mishandle output filename.** `generate_mosaic_image()`
  (`backend_api.py:836-871`) builds the output path via
  `target_path.replace('target_', 'mosaic_').replace('.jpg', '_mosaic.jpg')`.
  For a `.png`/`.webp`/etc. upload, the `.jpg` replace is a no-op, so the
  "mosaic" file keeps the original extension while still being saved via
  `mosaic.save(output_path, quality=95, ...)` (JPEG-only options). Normalize
  output format/extension explicitly instead of string-replacing the input
  filename.
- [ ] **No structured logging or error monitoring configured.** Errors are
  `print()`ed (e.g. Printful failures) or swallowed into generic 500 JSON
  responses. No Sentry/equivalent wired up despite being mentioned in the
  deployment guide.
- [ ] **No file-upload/order rate limiting or per-user quotas** — a free user
  can currently create unlimited mosaics/storage with no cap, which directly
  undercuts the "free unlimited mosaics, paid prints" business model's cost
  assumptions.
- [ ] **No automated CI** — tests exist and pass (44/44 as of this writing) but
  nothing runs them on push/PR.
- [ ] **No database migrations.** Schema is created via `db.create_all()` only;
  no Alembic/Flask-Migrate, so any future schema change to a live DB has no
  safe upgrade path.

## P3 — Scale / later

- [ ] Async mosaic generation via Celery + Redis (already called out in
  `DEPLOYMENT_GUIDE.md`'s own scaling section).
- [ ] Move uploaded/generated images from local filesystem to S3 (or
  equivalent) + CDN.
- [ ] Read replicas / connection pooling once concurrent load appears.
- [ ] Uptime monitoring (UptimeRobot or similar) and analytics wiring.

---

## What's already solid

- Password hashing (`werkzeug.security`), basic input validation on
  register (username/email/password format), pagination caps, and upload
  dimension/tile-size clamping are all implemented correctly.
- 404/500 error handlers exist and don't leak internals in their JSON bodies.
- `tests/` (44 tests) pass cleanly against `photo_mosaic.py` and the backend
  units that are covered.
- Session cookies are configured with `Secure`/`HttpOnly`/`SameSite=Lax`.
