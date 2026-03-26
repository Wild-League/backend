# Self-hosting the Wildleague backend

This document describes how to run the Django API and its dependencies on your own machine or server. The supported path is **Docker Compose**, which brings up PostgreSQL, the API, Nakama (realtime), and SeaweedFS (S3-compatible object storage).

## Requirements

- **Docker** and **Docker Compose** (v2 plugin: `docker compose`)
- For local development without Docker: **Python 3.11**, **PostgreSQL 16**, and dependencies from `requirements.txt`

Nakama’s published image is `linux/amd64`; on Apple Silicon, Docker will emulate amd64 (see `platform: linux/amd64` in `docker-compose.yml`).

## Quick start (Docker)

1. **Clone** this repository and `cd` into the backend directory.

2. **Environment file**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set at least:

   - `SECRET_KEY` — a long random string (required).
   - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` — database credentials (defaults in `.env.example` are fine for local use).
   - For containers on the Compose network:
     - `POSTGRES_HOST` is set to `postgres` by the `api` service in `docker-compose.yml` (you do not need to duplicate it unless you run the API outside Compose).
     - Set `SEAWEED_S3_ENDPOINT=seaweedfs-s3:8333` in `.env` so the API resolves SeaweedFS by Docker service name.
   - Optional: `SEAWEED_PUBLIC_BASE_URL` — public base URL for card images if clients cannot reach the internal S3 hostname (e.g. `http://localhost:8333` when testing from the host).

3. **Start the stack**

   ```bash
   docker compose up --build
   ```

   The API entrypoint runs migrations on startup, then starts Gunicorn on port **8000**.

4. **Create SeaweedFS S3 credentials**

   Open a shell in the SeaweedFS master container:

   ```bash
   docker compose exec seaweedfs-master weed shell
   ```

   Then create an S3 identity with access to the `cards` bucket:

   ```bash
   s3.configure -user=wildleague -access_key=wildleague -secret_key=wildleague-secret -buckets=cards -actions=Read,Write,List,Tagging,Admin -apply
   ```

   Use these values in your env file:

   - `SEAWEED_ACCESS_KEY=wildleague`
   - `SEAWEED_SECRET_KEY=wildleague-secret`
   - `SEAWEED_CARD_BUCKET=cards`

5. **Optional: seed default cards**

   After the API and SeaweedFS are healthy, seed the built-in card catalog and mirror assets into SeaweedFS (see `src/api/management/commands/seed_default_cards.py`):

   ```bash
   docker compose exec api python manage.py seed_default_cards
   ```

   Run once on a fresh database unless you use `--force` to refresh.

## Services and ports

| Service        | Role                         | Host ports (default)   |
|----------------|------------------------------|-------------------------|
| `api`          | Django + Gunicorn            | `8000`                  |
| `postgres`     | PostgreSQL 16                | `5432`                  |
| `nakama`       | Game server (realtime)       | `7349`, `7350`, `7351`  |
| `seaweedfs-s3` | S3 API for object storage    | `8333`                  |
| `seaweedfs-filer` / `master` / `volume` | SeaweedFS cluster | `8888`, `9333`, `8090`, … |

PostgreSQL is initialized with two databases: the app DB (`POSTGRES_DB`, default `wildleague`) and **`nakama`** (created by `docker/postgres-init/02-create-nakama-db.sh`). Nakama connects using the same `POSTGRES_USER` / `POSTGRES_PASSWORD` and the `nakama` database.

Game clients and tooling connect to Nakama on the gRPC/HTTP ports above; Lua modules for Nakama live under `realtime/modules/` in this repo.

## Settings module

- **`DJANGO_SETTINGS_MODULE`** — defaults via `manage.py`: `src.config.dev_settings` unless `ENV=production`, then `src.config.prod_settings`.
- For self-hosting with **environment-driven** database and SeaweedFS settings, use **`src.config.dev_settings`** and set variables in `.env` (as in `.env.example`). The checked-in `prod_settings` module is tailored to deployed infrastructure; prefer `dev_settings` plus env vars for your own deployment.

`ENV=production` switches the API container to Gunicorn **without** `--reload` (see `entrypoint.sh`).

## Reverse proxy and TLS

For a public host, terminate HTTPS at a reverse proxy (Caddy, nginx, Traefik, etc.) and forward to `api:8000`. Update Django-related settings as needed:

- `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` / `CORS_ALLOWED_ORIGINS` in `dev_settings.py` (or a forked settings module) for your domain.
- Ensure `FRONT_URL` matches your frontend origin if you rely on it for redirects or links.

## Operational notes

- **Persistence**: PostgreSQL data is stored in the `postgres_data` Docker volume; SeaweedFS volume data in `seaweedfs_data`.
- **Hot reload**: `docker compose up --watch` syncs the project into the API container for development (see `docker-compose.yml` `develop.watch`).
- **Email**: `POSTMARK_TOKEN` is referenced for Postmark; configure or stub as needed for your environment.
