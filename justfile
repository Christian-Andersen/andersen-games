alias c := check
alias d := dev

[private]
default:
    @just --list

setup:
    cd ./frontend && npm install --silent
    cd ./etls/absgame/ && uv sync --locked
    cd ./etls/real-estate/ && uv sync --locked

build:
    just frontend build

check:
    prek run --all-files

dev:
    just frontend dev
