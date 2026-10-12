# The data pipeline as an image, so it can run on a schedule in the cloud.
# Built from the repo root: docker build -f pipeline/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

COPY pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline ./pipeline

# Run as a regular user; it needs to write downloaded files to pipeline/data/
RUN useradd --create-home --uid 1000 pipeline \
    && mkdir -p pipeline/data && chown pipeline pipeline/data
USER pipeline

CMD ["python", "-m", "pipeline.run_all"]
