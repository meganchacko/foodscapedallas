# FoodScape Dallas

FoodScape Dallas is a website that maps food access in Dallas County. It helps city planners find food deserts and test where a new grocery store would help most, and helps residents find food near them and get there. The map uses public tract-level data (USDA Food Access Research Atlas, CDC PLACES), and a separate personal health check uses a model trained on the UCI obesity dataset.

## Repo layout

```
backend/              FastAPI app (Python 3.12)
frontend/             React + TypeScript app (Vite)
pipeline/             data loaders for USDA, CDC, Census, OpenStreetMap, pantries
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

The map needs data: run the pipeline once (see [Loading the data](#loading-the-data)). For the map's gray background without a watermark, add a free CARTO key to `.env` as `CARTO_API_KEY` (https://carto.com/basemaps/apikey) and restart the frontend.

### API

| Endpoint | Returns |
| --- | --- |
| `GET /health` | Whether the API, database, and cache are up (200 or 503) |
| `GET /tracts` | Every tract as GeoJSON: population, obesity %, both food access definitions, priority area flags, distance to the nearest grocery store. Cached in Redis; the pipeline clears the cache after loading |
| `GET /places?type=` | Grocery stores, pantries, and farmers markets as GeoJSON points; `type` is optional |

Interactive docs: http://localhost:8000/docs

### The map

- Shade tracts by **food access** (either USDA definition) or **adult obesity rate**.
- **Priority areas** outline tracts with low food access *and* an adult obesity rate above the county median. They show where the two problems occur together, not that one causes the other.
- Pins for grocery stores, pantries, and farmers markets, filterable by type.
- Click a tract for its details.

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

### Database migrations

The schema is managed with Alembic (`backend/alembic/versions/`). The backend container runs `alembic upgrade head` on startup, so `docker compose up` always has the latest schema. Tests run against a separate `foodscape_test` database that they create and drop themselves.

```bash
alembic -c backend/alembic.ini upgrade head                       # apply migrations to the dev database
alembic -c backend/alembic.ini revision --autogenerate -m "..."   # draft a migration after changing app/db/models.py
alembic -c backend/alembic.ini check                              # confirm the models and migrations match
```

`.env` holds local settings and secrets and is never committed. Keep `.env.example` up to date when adding settings.

## Loading the data

The data pipeline is a separate program from the API. It downloads public data for Dallas County and loads it into the database.

```bash
pip install -r pipeline/requirements.txt
docker compose up -d db                # the database must be running and migrated
python -m pipeline.run_all             # from the repo root
```

It needs a free Census API key in `.env` (`CENSUS_API_KEY`, sign up at https://api.census.gov/data/key_signup.html). Downloaded files are cached in `pipeline/data/raw/`; delete that folder to download fresh copies. Every loader is idempotent: running the pipeline again updates rows in place instead of duplicating them.

### Data sources

| Data | Source | Notes |
| --- | --- | --- |
| Tract boundaries | Census TIGER/Line 2020, Dallas County | 645 tracts |
| Block centers + population | Census TIGER/Line 2020 + Census API (2020 redistricting data) | Population per tract is the sum of its blocks |
| Food access, 2019 definition | USDA Food Access Research Atlas 2019 (Large Retailer Access Map) | Counts supermarkets and large grocery stores |
| Food access, 2025 definition | USDA Food Access Research Atlas 2025 (SNAP-authorized Retailer Access Map) | Counts any SNAP-authorized store, including convenience stores |
| Adult obesity | CDC PLACES 2025 release | Modeled estimates, not diagnoses |
| Grocery stores, farmers markets | OpenStreetMap (Overpass API) | Supermarkets and greengrocers; marketplaces with "farmers" in the name |
| Food pantries | Hand-entered from the North Texas Food Bank pantry finder | `pipeline/seeds/pantries.csv` |

Both food access definitions use the standard low-access threshold: more than 1 mile from a store in urban areas, 10 miles in rural areas, measured in a straight line.

### Known limitations

- **The 2019 food access data is on 2010 tract boundaries.** The pipeline translates it to 2020 tracts using the Census 2020-to-2010 tract relationship file. Flags come from the 2010 tract covering most of a 2020 tract's land; low-access population is split by land area, which assumes people are spread evenly. 565 of 645 Dallas tracts sit at least 99% inside a single 2010 tract, and only 6 straddle 2010 tracts that disagree on the food-desert flag.
- **The 2019 data reflects stores as of 2019.** Supermarkets that opened or closed since then aren't counted.
- **The two definitions give very different maps.** Under the 2019 supermarket definition, 111 Dallas tracts are low-income and low-access; under the 2025 any-SNAP-store definition, 6 are. Neither is wrong; they answer different questions.
- **Two tracts have no data** (48113980000, 48113980100): unpopulated special-use areas.
- **OpenStreetMap is volunteer-mapped.** Grocery coverage in Dallas is good but not complete, farmers markets are sparse, and SNAP/WIC acceptance is almost never recorded (stored as unknown).

## Running the original model

```bash
pip install -r ml/requirements.txt
cd ml
python part1.py   # linear regression via gradient descent in numpy
python part2.py   # linear regression via scikit-learn's SGDRegressor
```

Logs and plots are written to `ml/logs/` and `ml/plots/`. See `ml/README.md` for details on the model.
