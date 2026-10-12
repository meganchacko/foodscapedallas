# Load test: Find food near me

Tool: [Locust](https://locust.io), `loadtest/locustfile.py`. Endpoint: `GET /places/nearby` at a random point in Dallas County, with a random radius (0.5, 1, 2, or 5 miles). Run on 2026-10-12.

| Test | Simulated users | Requests | Failures | Requests/s | Median | p95 | p99 | Slowest |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Realistic**: each user searches every 1–3 s, for 60 s | 50 | 1,412 | 0 | 24 | 8 ms | 14 ms | 150 ms | 194 ms |
| **Capacity**: requests back to back, for 30 s | 20 | 12,040 | 0 | **415** | 31 ms | 180 ms | 230 ms | 413 ms |

**What it shows:** 50 people searching at once get answers in about 8 ms (14 ms for 95% of them), and the API keeps up with about 415 searches per second before slowing down, with no errors.

**How to read it**
- *Requests/s* in the realistic test is set by the users' pauses (50 users ÷ ~2 s), not by the server. The capacity test removes the pauses to find the server's limit.
- *p95* = 95% of requests were at least this fast. Averages hide slow outliers; percentiles show them.

**Setup and caveats**
- A laptop running the Docker Compose stack: one uvicorn process in development mode (`--reload`), and the PostGIS image running under emulation on Apple Silicon. Production would run several processes on dedicated hardware, so these numbers are a floor, not a ceiling.
- Rate limiting was turned off for the run (`RATE_LIMIT_ENABLED=false`), because every simulated user comes from one machine and would otherwise just measure the 429 responses.
- The query is fast because of the geography index on `places` (see `docs/spatial-index-benchmark.md` for what an index like that is worth).

**Reproduce**

```bash
pip install -r loadtest/requirements.txt
RATE_LIMIT_ENABLED=false docker compose up -d backend
locust -f loadtest/locustfile.py Resident --headless --users 50 --spawn-rate 10 --run-time 60s --host http://localhost:8000
locust -f loadtest/locustfile.py NoPauses --headless --users 20 --spawn-rate 20 --run-time 30s --host http://localhost:8000
docker compose up -d backend   # rate limiting back on
```
