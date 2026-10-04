# FoodScape Dallas

FoodScape Dallas is a website that maps food access in Dallas County. It helps city planners find food deserts and test where a new grocery store would help most, and helps residents find food near them and get there. The map uses public tract-level data (USDA Food Access Research Atlas, CDC PLACES), and a separate personal health check uses a model trained on the UCI obesity dataset.

## Repo layout

```
backend/    FastAPI app (coming in Phase 1)
frontend/   React app (coming in Phase 1)
pipeline/   data loaders for USDA, CDC, Census, OpenStreetMap, pantries (coming in Phase 3)
ml/         obesity model
```

## Running the model

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r ml/requirements.txt

cd ml
python part1.py   # linear regression via gradient descent in numpy
python part2.py   # linear regression via scikit-learn's SGDRegressor
```

Logs and plots are written to `ml/logs/` and `ml/plots/`. See `ml/README.md` for details on the model.

## Development

Copy `.env.example` to `.env` for local settings. `.env` is never committed.
