# Import Desk

Python CSV imports with row checks, retries, and a scheduled sample feed.

[![Build and test](https://github.com/Jaryn2/import-desk/actions/workflows/check.yml/badge.svg)](https://github.com/Jaryn2/import-desk/actions/workflows/check.yml)

[Project page and walkthrough](https://jaryn2.github.io/projects/import-desk/) · [Code guide](GUIDE.md) · [Learning guide](docs/LEARNING.md)

## Run it

Install Python 3.12 or newer and Docker with Compose. Run these commands from this repo's root:

```sh
python scripts/setup.py
docker compose up --build -d
```

Open http://127.0.0.1:5402. Sign in as `demo`, using the `DEMO_PASSWORD` in your new `.env` file. The setup script makes random local passwords. It keeps existing settings when run again.

Use the sample button to load fictional records. The background worker also imports a generated fleet reading every five minutes.

The ports bind to localhost. Stop the app with `docker compose stop`. Saved data stays in a Docker volume. Starting with `docker compose up -d` keeps those records. The screenshots show a workspace after following the sample tasks; a fresh database has less history.

## Check it

Tests use a separate database and ports. They do not edit the demo database.

```sh
python -m venv .venv
# Activate .venv using the command for your shell.
python -m pip install -r requirements-dev.txt
python scripts/setup.py --test
docker compose --env-file .env.test -f compose.test.yaml up --build -d
python scripts/wait_ready.py
python -m pytest tests integration -q
docker compose --env-file .env.test -f compose.test.yaml down
```

The Docker build runs TypeScript checks and builds the React frontend. Python tests cover validation and service behavior. Integration tests send real HTTP requests and check PostgreSQL records. The workflow runs the same steps on GitHub. Open its badge for the result of the current commit.

## Structure

- `web/src`: React pages, TypeScript requests, and CSS.
- `app`: Python routes, database access, and processing logic.
- `app/schema.sql`: tables and database rules.
- `integration`: complete requests against the running API and test database.
- `docs`: screenshots, measured results, and explanations.

## Scope

This is a personal learning project with sample data. The app runs locally; the public project page is a walkthrough. It is not a production service or software used by a former employer.

The scheduled feed generates sample readings. No live fleet system, Azure job, or Power BI report is connected.

LLMs helped with implementation, tests, documentation, and explanations of unfamiliar parts of the stack. The guides are included so I can study the code and explain its decisions. See [verification notes](docs/VERIFICATION.md) for the measured checks and remaining work.
