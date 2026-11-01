# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.1] - 2026-11-01

### Fixed
- **Geolocation responsiveness**: removed the useless reverse-geocoding request
  fired on every map load, lowered the geolocation timeout to 6 s, increased the
  accepted cached position age to 10 minutes, and checked the Permissions API
  before calling `getCurrentPosition` so a denied permission fails immediately.
- Reverse geocoding now runs immediately after a geolocation fix (no 800 ms
  debounce), aborts after 6 s, uses a 10-minute client-side cache, and no longer
  sends a forbidden `User-Agent` header from the browser.
- The geolocation recenter no longer animates the zoom, and the filtered tile
  pane is promoted to its own GPU layer to reduce mobile pan/zoom jank.

## [2.3.0] - 2026-11-01

### Added
- **Modern UI refresh**: shared dark design tokens, a full-height app shell, a
  responsive secondary-page header, refreshed controls, inputs, cards, map
  controls, progress panel, and poster list.
- **Geolocation**: a “Ma position” control on the map uses the browser
  Geolocation API to center the preview on the visitor and reverse-geocode the
  position into the city/country fields.
- **Documentation**: a rewritten, production-oriented README with badges,
  architecture, API overview, deployment, operations, and troubleshooting.
- **Mobile**: `viewport-fit=cover` and safe-area insets, 16 px form fields to
  prevent iOS focus zoom, 44 px touch targets, responsive header/navigation,
  full-screen sidebar close control, and mobile-specific map controls.

### Fixed
- Removed the leftover global navigation bar that displayed default blue links
  above the full-screen generator and added unintended page padding.
- Made the map overlay and Leaflet zoom controls responsive on small screens.
- Fixed the truncated “Position” field in the ranking builder.

### Changed
- Map controls and attribution now follow the application's dark visual style.
- Version bumped to 2.3.0.

## [2.2.1] - 2026-11-01

### Fixed
- **Preview map tiles**: removed the CARTO Dark Matter / Positron tile
  providers, which now require an API key (`API KEY REQUIRED` watermark). The
  preview uses OpenStreetMap Standard tiles only, with a CSS filter on the tile
  pane for dark/light themes. No tile API key is needed.
- Updated the preview attribution and documentation accordingly.

## [2.2.0] - 2026-11-01

**Security hardening and VPS deployment.**

### Security
- **Redis**: no published port, password required (`REDIS_PASSWORD`), internal
  Docker network, `maxmemory` with `noeviction`, healthcheck.
- **Storage**: MinIO replaced by **VersityGW** (`versity/versitygw:v1.10.0`),
  private bucket, credentials from environment, no anonymous policy, no
  console, no published port.
- **Posters**: private bucket + HMAC-signed expiring download URLs streamed by
  the API. Legacy `/minio_storage/` now returns `410`.
- **API**: signed anonymous sessions, per-IP daily quota, per-session
  concurrency cap, global queue cap, request size limit, ownership checks on
  task status/history/download. CORS removed. OpenAPI docs disabled by default.
- **Validation**: strict Pydantic models (theme path traversal, format,
  distance, dimensions, DPI, pixel budget, custom layers/colors, extra fields).
- **Worker**: 2 GiB memory limit, concurrency 1, one process per task, soft/hard
  timeouts, sanitized client errors, Matplotlib mathtext disabled for labels.
- **Containers**: pinned images, non-root API/worker/web, `no-new-privileges`,
  `cap_drop`, log rotation, `.dockerignore` excluding `.env`.
- **Retention**: posters older than 7 days or beyond 2000 objects are deleted
  lazily (Redis lock).

### Added
- `.env.example` with no default secret, `scripts/init-env.sh` secret generator.
- `SECURITY.md` threat model, residual risks and verification checklist.
- VPS + Caddy deployment guide, Compose config validation in CI, security tests.
- `docker compose` healthchecks and restart policies for api/redis/storage/nginx.
- Storage/runtime resource limits and per-service CPU limits.

### Changed
- Storage interface preserved for the worker (S3/boto3), so the Celery task
  contract is unchanged; the worker now returns `file_key` and the API signs it.
- Frontend proxies forward the session cookie and `Set-Cookie`; custom paper
  sizes are no longer ignored by the SvelteKit proxy.
- Distance capped at 25 km and output at 100 Mpx, with client-side validation.
- History is scoped to the current session ("Historique de session").
- Removed the obsolete root `Dockerfile` (unused monolith, unpinned base).
- Moved `pytest` / `pytest-mock` to `requirements-dev.txt`; the production
  image no longer ships test tooling.
- Removed the legacy `/posters/{filename}` route and the committed
  `static/posters/*.png` files: they exposed old generated maps (personal
  locations) and are no longer used now that posters come from private S3.

### Fixed
- `CACHE_DIR` environment variable was ignored by `backend/cache.py`.
- `S3_PUBLIC_URL` / `build_public_url` were referenced but undefined in
  `/history`, causing silent empty history.
- Public `/history` and `/download/{task_id}` leaked other users' posters.
- Path traversal through the `style` parameter in `load_theme`.
- Unbounded `distance`/`width`/`height`/`dpi` could OOM the worker.

## [2.1.1] - 2026-01-23

### Fixed
- **Theme Selection**: Fixed a regression where selecting a specific theme (e.g., "Neon Cyberpunk") was ignored by the backend due to API parameter mismatch (`theme` vs `style`).
- **Accessibility**: Resolved multiple a11y warnings in the Sidebar controls by using proper interactive elements (`<button>`) instead of generic click handlers.
- **Type Safety**: Synchronized TypeScript interfaces with Python Pydantic models to prevent future API contract regressions.

### Improved
- **Performance**: Implemented **Adaptive Polling** for task status. The client now uses exponential backoff with jitter to reduce server load and wakes up instantly upon progress updates.

## [2.1.0] - 2026-01-23

### Added
- **Presets / Favorites**: User can now save, load, and delete favorite configurations (City, Theme, Layers...) locally in the browser.
- **Backend History**: New `/history` endpoint listing recent global generations directly from S3.
- **Bulk Export**: Generate posters for ALL themes in a single click (optimized One-Fetch-Multi-Render + ZIP).
- **ETA & Progress**: Live "Estimated Time Remaining" display during generation.
- **Improved UX**: 
  - Visual **Paper Ratio Preview** in sidebar.
  - Better key handling for caching (distinguish Bulk ZIP vs Single Image).
  - Enhanced Accessibility (ARIA labels on all inputs).
- **Advanced Print Settings**:
  - Support for **A4, A3, 30x40cm** and **Custom** paper sizes.
  - **DPI Selection** (150, 300, 600) for professional printing.
  - **Margins Control**: Precise margin adjustments in inches.
- **Improved Validation**: Strict validation for inputs with inline error messages.
- **Polling Transparency**: Translated and granular status updates during generation.

### Changed
- **UX**: Replaced native `alert()` with non-blocking UI error banners.
- **CI**: Upgraded CI workflows and Docker images to **Node.js 22** for Vite 6 compatibility.
- **Accessibility**: Added ARIA attributes and improved mobile UX (bouncing badge).

## [2.0.0] - 2026-01-23

**Major Industrialization & Cloud-Native Refactor**

### Architecture
- **Microservices**: Decomposed monolithic backend into `API` (FastAPI), `Worker` (Celery), and `Front` (SvelteKit).
- **Stateless Worker**: Moved from filesystem storage to **S3 (MinIO)** for poster storage.
- **Poll-based API**: Replaced SSE with robust Task ID polling mechanism.
- **Gateway**: Introduced Nginx as the single entry point.

### Added
- **Quality Assurance**: Added CI/CD Pipeline (`.github/workflows/ci.yml`).
- **Testing**: Added Pytest suite for Backend and Vitest/Playwright for Frontend.
- **Security**: Added Rate Limiting (SlowAPI), Security Headers (Nginx), and Sentry monitoring.
- **Mobile UX**: Added responsive Sidebar Drawer and mobile toggle controls.
- **Map Themes**: Interactive map now switches tile providers (Dark/Light/OSM) based on selected style.
- **Caching**: Implemented MD5-hash based caching on S3 to skip regeneration of identical requests.

### Changed
- **Performance**: Optimized Matplotlib memory usage and ensured explicit figure closing.
- **Config**: All sensitive configs moved to Environment Variables.

---

## [0.2.0] - 2026-01-22

### Added
- **Backend Architecture**: Refactored backend into a modular **FastAPI** service (`backend/`).
  - Separated concerns: `main.py` (API), `fetcher.py` (Async I/O), `renderer.py` (OO Plotting).
  - Performance: Parallel fetching of OSM data.
- **API Proxy**: Frontend now communicates with the Python backend via HTTP proxy instead of local spawn.
- **Docker Compose**: Added orchestration for separated `api` and `web` services.
- **Map Preview**: Replaced circular selection with a rectangular zone matching the 3:4 poster aspect ratio.
- **Custom Colors**: Added full UI control to customize colors overriding the selected theme.
- **Smart Caching**: Implemented file existence check to avoid re-rendering same parameters.

### Fixed
- **Docker Volumes**: Fixed configuration to ensure generated posters are accessible by the frontend.
- **Filename Encoding**: Fixed 404 error for cities with accents (allow Unicode filenames).
- **Poster Preview**: Changed content disposition to `inline`.
