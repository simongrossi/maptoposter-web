# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-01-22

### Added
### Added
- **Backend Architecture**: Refactored backend into a modular **FastAPI** service (`backend/`).
  - Separated concerns: `main.py` (API), `fetcher.py` (Async I/O), `renderer.py` (OO Plotting).
  - Performance: Parallel fetching of OSM data.
- **API Proxy**: Frontend now communicates with the Python backend via HTTP proxy instead of local spawn, enabling separation of concerns and Docker networking.
- **Docker Compose**: Added orchestration for separated `api` and `web` services with shared volumes.
- **Map Preview**: Replaced circular selection with a rectangular zone matching the 3:4 poster aspect ratio for accurate WYSIWYG.
- **Custom Colors**: Added full UI control to customize colors (Background, Water, Roads, Parks, Text) overriding the selected theme.

### Fixed
- **Docker Volumes**: Fixed configuration to ensure generated posters are accessible by the frontend.
- **Filename Encoding**: Fixed 404 error for cities with accents (allow Unicode filenames).
- **Poster Preview**: Changed content disposition to `inline` so the "Eye" button opens the image in the browser instead of downloading it.
- **Leaflet Icons**: Fixed broken missing icon images by using CDN.
- **Themes**: Fixed missing themes in Docker by copying the directory in the build stage.
- **UX**: Fixed "Aperçu" badge interactions triggering accidental map movements.
- **Robust Caching**: Implemented MD5-based file caching to avoid filename collisions.
- **Real-time Progress (SSE)**: The application now uses Server-Sent Events to stream progress from the Python script to the UI. Users can see exactly what step is running (fetching data, rendering, etc.).
- **Cancellation ability**: Aborting the request (or reloading the page) now instantly kills the running Python process on the server.
- **Progress UI**: Replaced static loading button with a visual percent-based progress bar and an explicit "Stop" button.
- **About Page**: Added a dedicated `/about` page for credits and licensing info, decluttering the main interface.
- **Custom Layers Feature**: Users can now toggle and customize colors for additional map layers (Cycle Paths, Railways, Subway Lines) from the sidebar.
  - Frontend: New "Couches Sup." section in `+page.svelte`.
  - Backend: API support for passing custom layer definitions to Python.
  - Python: `plot_custom_layers` logic in `create_map_poster.py` to dynamically fetch and render requested features.
- **Strict Typing**: Added `src/lib/types.ts` defining `Theme`, `GenerationRequest`, `CustomLayer` interfaces.
- **API Utilities**: Created `src/lib/api.ts` to centralize fetch logic.
- **Reliable Output Parsing**: Python script now outputs a JSON array of generated files via `__JSON_RESULT_FILES__` marker.

### Changed
- **Default Radius**: Reduced default map distance from 29km to **10km** for better initial city views.
- **Python Execution path**: Replaced hardcoded user path with `env.PYTHON_PATH` (via `$env/dynamic/private`) or system fallback logic.
- **Frontend Refactor**: Migrated `+page.svelte` from `any` types to strict TypeScript interfaces.
- **File Detection**: Server no longer scans directories to find new files (preventing race conditions); it relies on the Python script's explicit output.

### Fixed
- **CSS Layout**: Removed duplicated style block that was accidentally inserted into the HTML template.
- **Race Condition**: Fixed issue where simultaneous poster generations could mix up output files.
- **Crash on Missing Config**: Server now handles missing `PYTHON_PATH` gracefully by falling back to `python`/`python3`.
- **CLI Parsing**: Fixed `unrecognized arguments` error for custom layers by correctly updating Python script argument parser.


