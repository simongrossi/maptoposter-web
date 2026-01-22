# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-01-22

### Added
- **Custom Layers Feature**: Users can now toggle and customize colors for additional map layers (Cycle Paths, Railways, Subway Lines) from the sidebar.
  - Frontend: New "Couches Sup." section in `+page.svelte`.
  - Backend: API support for passing custom layer definitions to Python.
  - Python: `plot_custom_layers` logic in `create_map_poster.py` to dynamically fetch and render requested features.
- **Strict Typing**: Added `src/lib/types.ts` defining `Theme`, `GenerationRequest`, `CustomLayer` interfaces.
- **API Utilities**: Created `src/lib/api.ts` to centralize fetch logic.
- **Reliable Output Parsing**: Python script now outputs a JSON array of generated files via `__JSON_RESULT_FILES__` marker.

### Changed
- **Python Execution path**: Replaced hardcoded user path with `env.PYTHON_PATH` (via `$env/dynamic/private`) or system fallback logic.
- **Frontend Refactor**: Migrated `+page.svelte` from `any` types to strict TypeScript interfaces.
- **File Detection**: Server no longer scans directories to find new files (preventing race conditions); it relies on the Python script's explicit output.

### Fixed
- **Race Condition**: Fixed issue where simultaneous poster generations could mix up output files.
- **Crash on Missing Config**: Server now handles missing `PYTHON_PATH` gracefully by falling back to `python`/`python3`.
