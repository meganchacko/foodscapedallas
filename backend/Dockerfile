# Built from the repo root (docker build -f backend/Dockerfile .), so the image can include the
# trained model from ml/model/. The root .dockerignore limits what's sent to the build.
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first: Docker caches this layer, so code edits don't trigger a reinstall
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY ml/model ./model

# Where the app loads the health check model from (see app/config.py)
ENV MODEL_DIR=/app/model

# Run as a regular user, not root: if the app were ever compromised, the attacker wouldn't have
# root inside the container
RUN useradd --create-home --uid 1000 app
USER app

EXPOSE 8000
# Production: 2 worker processes (rate limits stay correct across them because the counts live
# in Redis). Migrations are not run here; they run as a separate step before a new version
# starts. docker-compose.yml overrides this for development (auto-reload, migrations first).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
