# Hardening: what this project demonstrates

Each row links to working code and a way to see it for yourself.

| What it shows | How | Proof | Numbers |
| --- | --- | --- | --- |
| **Caching** | Cache-aside in Redis for `/tracts` and `/geocode`; the pipeline clears the map cache after loading | `X-Cache: HIT`/`MISS` header; `backend/tests/test_tracts.py`, `test_geocode.py` | `/tracts`: ~263 ms (MISS) → ~1 ms (HIT) |
| **Response timing** | Middleware times every request | `Server-Timing` header (Chrome dev tools → Network → Timing) | Every response |
| **Spatial indexing** | GIST indexes on `geom::geography` for meters-based queries | `python -m scripts.benchmark_spatial_index` → [`spatial-index-benchmark.md`](spatial-index-benchmark.md) | People within 1 mile: 33 ms → 0.28 ms (~119x) |
| **Performance under load** | Locust load test of `/places/nearby` | [`load-test.md`](load-test.md) | 50 users: median 8 ms, p95 14 ms; capacity ~415 req/s, 0 errors |
| **Rate limiting** | Per-client, per-minute counters in Redis (`INCR` + `EXPIRE`), shared by every server process; fails open if Redis is down | `backend/tests/test_rate_limit.py`; 31 address searches in a minute → `429` with `Retry-After` | geocode 30/min, health check 20/min, nearby/map 60/min |
| **Observability** | One JSON log line per request with a request ID, returned as `X-Request-ID` | `docker compose logs backend`; `backend/tests/test_request_logging.py` | Every request |
| **Privacy in logs** | Logs record paths only: never search text, health check answers, or IPs (the rate limiter keys on a hash of the IP that expires in 60 s) | `test_searched_addresses_never_reach_the_logs`, `test_health_check_answers_never_reach_the_logs` | |
| **Graceful degradation** | Redis down → map still loads from Postgres, rate limiting allows requests; Nominatim down → 503 with a retry message | `test_tracts_still_work_when_redis_is_down`, `test_requests_are_allowed_if_redis_is_down`, `test_nominatim_failure_is_a_503` | Fails fast (Redis retries off) |
| **Idempotent data pipeline** | Upserts on stable source keys; removes places that disappear from a source | `pipeline/tests/test_loading.py`; running `python -m pipeline.run_all` twice gives identical counts | |
| **Responsible ML** | No leaky inputs, cross-validation, calibration, per-group results, synthetic-data effects documented, suggestions checked against the model | Model card page; `ml/tests/`, `backend/tests/test_health_check.py` | ROC AUC 0.855 (0.69 on real-looking rows) |
| **CI** | Lint, backend + pipeline + ML tests (with real PostGIS and Redis), frontend lint + tests + build, Docker builds on every push | `.github/workflows/ci.yml` | |

**Moved to Phase 9:** running the pipeline on a schedule. It only makes sense once the database is deployed (a weekly job on a laptop runs only if the laptop is on).
