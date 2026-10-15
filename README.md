# FoodScape Dallas

FoodScape Dallas is a website that maps food access in Dallas County. It helps city planners find food deserts and test where a new grocery store would help most, and helps residents find food near them and get there. The map uses public tract-level data (USDA Food Access Research Atlas, CDC PLACES), and a separate personal health check uses a model trained on the UCI obesity dataset.

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

### The map

- Shade tracts by **food access** (either USDA definition) or **adult obesity rate**.
- **Priority areas** outline tracts with low food access *and* an adult obesity rate above the county median. They show where the two problems occur together, not that one causes the other.
- Pins for grocery stores, pantries, and farmers markets, filterable by type.
- Click a tract for its details.

### Find food near me

- Search by address or place name, or share your location (the browser asks first; coordinates are only used for the search and aren't stored).
- Results within 0.5 to 10 miles, closest first, filterable by type and SNAP acceptance.
- A notice when the location is in a low food access area, outside Dallas County, or has nothing nearby (with a one-click wider search).
- **Transit directions** on every result: opens Google Maps on the public transit tab, from the searched location to the place's address (a plain Google Maps link; no API key).

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

Frontend (from `frontend/`): `npm test` (Vitest), `npm run lint`, `npm run build`. See `frontend/README.md`.

### Health check

- A short questionnaire about habits (no height, weight, name, or location). Returns an estimated likelihood of obesity among people with similar answers in the survey data, and which answers moved it, described as patterns in the data, not causes.
- Not medical advice, and says so on every screen. Men and people over 61 get a note that the estimate is less reliable for them.
- When a changeable habit is the top factor *and* the healthier answer would lower the estimate, it suggests nearby grocery stores or farmers markets, linking to Find food near me.
- Answers are saved only if the user opts in, with a random ID generated in their browser.
- A model card page explains the model, its accuracy by group, and its limits. See `ml/README.md`.

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
| SNAP acceptance, SNAP farmers markets | USDA SNAP Retailer Locator data (stores authorized 2005–2025) | Current authorizations only |

Both food access definitions use the standard low-access threshold: more than 1 mile from a store in urban areas, 10 miles in rural areas, measured in a straight line.
