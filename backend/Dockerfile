FROM python:3.12-slim

WORKDIR /app

# Install dependencies first: Docker caches this layer, so code edits don't trigger a reinstall
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
