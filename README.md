# FoodScape Dallas

FoodScape Dallas is a website that maps food access in Dallas County. It helps city planners find food deserts and test where a new grocery store would help most, and helps residents find food near them and get there. The map uses public tract-level data (USDA Food Access Research Atlas, CDC PLACES), and a separate personal health check uses a model trained on the UCI obesity dataset.

## Repo layout

```
backend/              FastAPI app (Python 3.12)
frontend/             React + TypeScript app (Vite)
pipeline/             data loaders for USDA, CDC, Census, OpenStreetMap, pantries (coming in Phase 3)
ml/                   obesity model
docker-compose.yml    local stack: PostGIS, Redis, backend, frontend
.github/workflows/    CI: lint, backend tests, frontend build, Docker builds
```

## Running the app

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
cp .env.example .env   # then set a real POSTGRES_PASSWORD
docker compose up --build
```

| Service  | URL                                                              |
| -------- | ---------------------------------------------------------------- |
| Frontend | http://localhost:5173                                            |
| Backend  | http://localhost:8000 (API docs at http://localhost:8000/docs)   |
| Postgres | localhost:5432                                                   |
| Redis    | localhost:6379                                                   |

Stop with `docker compose down`. Add `-v` to also delete the database volume.

## Development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt ruff pre-commit
pre-commit install   # runs ruff automatically on every git commit
```

Backend tests need Postgres and Redis running (`docker compose up -d db redis`), then from the repo root:

```bash
pytest
ruff check . && ruff format --check .
```

Frontend: see `frontend/README.md`.

`.env` holds local settings and secrets and is never committed. Keep `.env.example` up to date when adding settings.

## Running the original model

```bash
pip install -r ml/requirements.txt
cd ml
python part1.py   # linear regression via gradient descent in numpy
python part2.py   # linear regression via scikit-learn's SGDRegressor
```

Logs and plots are written to `ml/logs/` and `ml/plots/`. See `ml/README.md` for details on the model.
