alias c := check
alias d := dev
alias ci := continuous_integration

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

audit:
    prek run --all-files audit

continuous_integration:
    prek run --all-files --stage manual
