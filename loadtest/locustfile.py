"""Load test for "Find food near me" (GET /places/nearby).

Each simulated user searches near a random point in Dallas County every 1-3 seconds, like
someone adjusting filters. Run from the repo root against the local Docker stack, with rate
limiting off (every simulated user comes from this one machine):

    RATE_LIMIT_ENABLED=false docker compose up -d backend
    # realistic: 50 people searching every 1-3 seconds
    locust -f loadtest/locustfile.py Resident --headless --users 50 --spawn-rate 10 \\
        --run-time 60s --host http://localhost:8000
    # capacity: 20 clients sending requests back to back, to find the most the server handles
    locust -f loadtest/locustfile.py NoPauses --headless --users 20 --spawn-rate 20 \\
        --run-time 30s --host http://localhost:8000
    docker compose up -d backend   # rate limiting back on

Results are written up in docs/load-test.md.
"""

import random

from locust import HttpUser, between, constant, task

# Roughly Dallas County (south, north, west, east)
LATITUDES = (32.62, 32.95)
LONGITUDES = (-96.95, -96.60)


class Resident(HttpUser):
    wait_time = between(1, 3)  # pause between a user's searches

    @task
    def search_nearby(self) -> None:
        params = {
            "lat": round(random.uniform(*LATITUDES), 5),
            "lng": round(random.uniform(*LONGITUDES), 5),
            "radius": random.choice([0.5, 1, 2, 5]),
        }
        # name= groups every search under one row in the results, whatever the parameters
        self.client.get("/places/nearby", params=params, name="/places/nearby")


class NoPauses(Resident):
    """Sends the next request as soon as the last one finishes, to measure capacity."""

    wait_time = constant(0)
