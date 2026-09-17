# Games

Monorepo for a collection of browser games and data processing tools.

## Structure

- `frontend/` — Vue 3 + Vite dashboard with embedded games (CPS Test, Space Invaders, Globe Hunter) and a standalone vanilla JS game (House Price Guesser). npm workspace with shared library and Tailwind CSS.
- `frontend/games/` — standalone static games served alongside the dashboard
- `frontend/shared/` — `@arcade/shared` library for localStorage state
- `etls/` — Python ETL scripts using uv workspace (real estate scraper, game score aggregation)

## Quick Start

```sh
just frontend dev     # dev server
just check            # run all checks (lint, type-check, audit)
just frontend build   # production build to frontend/dist/
```

## Checks

Each project has its own prek.toml; `just check` runs them all in parallel via prek workspace mode.

- **frontend**: Biome (lint/format), vue-tsc, npm audit
- **etls**: ruff (lint/format), ty (type check), uv audit
- **root**: builtin hooks (merge conflicts, large files, trailing whitespace, etc.)
