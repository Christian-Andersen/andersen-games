# Games

Monorepo for a collection of browser games and data processing tools.

## Structure

- `frontend/` — Vue 3 + Vite dashboard with embedded games (CPS Test, Space Invaders, Globe Hunter) and a standalone vanilla JS game (House Price Guesser). npm workspace with shared library and Tailwind CSS.
- `frontend/games/` — standalone static games served alongside the dashboard
- `frontend/shared/` — `@arcade/shared` library for localStorage state
- `etls/` — Python ETL scripts using uv workspace (real estate scraper, game score aggregation)

## Quick Start

```sh
just run     # dev server (dashboard + the standalone games)
just check   # run all checks (lint, type-check, audit)
just build   # production build to frontend/dist/
```

## House Price Guesser data

The game's `data.json` and photos are generated from the Domain scraper's output in
`etls/real-estate/data/`, which is gitignored.

```sh
just scrape       # scrape newly sold listings into etls/real-estate/data/
just game-data    # rebuild data.json + images from what has been scraped
just refresh-game # both, which is what keeps the daily challenge current
```

`export.py` keeps only playable listings (real price, sale date, at least one
bedroom, residential, land size, at least one photo), sorts them newest sale
first, and downloads every photo each listing has into
`frontend/games/house-price-guesser/images/` — around 18 per house. The daily
challenge walks that list backwards from the most recent sale, so index 0 is
always the newest house.

Each house also carries the sale method taken from domain's status line (private
treaty, auction, or sold prior to auction) and a link back to the original
listing. Auction results and private treaties price quite differently, which
makes the sale method useful context when guessing.

Photos are re-encoded to AVIF at their native 720px on the longest edge, because
domain.com.au's CDN only accepts signed URLs and will not serve a smaller crop.
Quality is kept high (q80) on purpose: the images are the whole game, and the
saving from compressing them harder is not worth how soft they look. Tune with
`--max-dimension`, `--quality` and `--max-images` (0, the default, keeps them
all).

Files in an image folder that the current export does not reference are deleted
automatically, so changing format or size never leaves old copies behind.

Photos live in a shared content-addressed pool under `images/<shard>/<sha256>`,
sharded by the first two hex digits. Each file is named after the SHA-256 of its
own bytes, so a picture appearing in more than one listing is stored once and
referenced from each. The hash is exact rather than perceptual, so a real
duplicate always collapses while two different photos never merge. An
`image_cache.json` maps CDN URLs to pool paths, which keeps repeat exports off
the network entirely.

Use `--dry-run` to inspect without downloading, and `--prune` to also delete
shards the current export no longer references.

Scrape notes: domain.com.au sits behind Akamai, which serves a behavioural
interstitial to a cold browser and blocks sustained scraping. The scrapers wait
for that challenge to resolve (`utils.wait_until_ready`), and repeated runs may
need a break before they are served listings again.

## Checks

Each project has its own prek.toml; `just check` runs them all in parallel via prek workspace mode.

- **frontend**: Biome (lint/format), vue-tsc, npm audit
- **etls**: ruff (lint/format), ty (type check), uv audit
- **root**: builtin hooks (merge conflicts, large files, trailing whitespace, etc.)
