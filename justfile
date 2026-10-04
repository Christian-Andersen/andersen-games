alias c := check
alias r := run

[private]
default:
    @just --list

setup:
    cd ./frontend && npm install --silent
    cd ./etls/absgame/ && uv sync --locked
    cd ./etls/real-estate/ && uv sync --locked

build:
    cd ./frontend && npm run build

check:
    prek run --all-files

# Dev server for the dashboard and the standalone games in frontend/games/
run:
    cd ./frontend && npm run dev

# Scrape newly sold Domain listings into etls/real-estate/data/
scrape:
    cd ./etls/real-estate/ && uv run python daily.py

# Rebuild the guesser's data.json and photos from whatever has been scraped
game-data:
    cd ./etls/real-estate/ && uv run python export.py

# Scrape then rebuild, which is what keeps the daily challenge current
refresh-game: scrape game-data

audit:
    prek run --all-files audit

ci: setup
    prek run --all-files --stage manual
