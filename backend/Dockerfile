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

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
