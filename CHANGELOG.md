# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
