"""Load testing for Etymology API.

In one terminal, start the API:
    uv run uvicorn backend.main:app

In another terminal, run Locust (from project root):
    uv run locust -f research/load-testing/locustfile.py --host http://localhost:8000

Open http://localhost:8089 to configure and run tests.

Quick headless tests:
    Basic (20 users):
        uv run locust -f research/load-testing/locustfile.py \
            --host http://localhost:8000 --users 20 --spawn-rate 5 --run-time 30s --headless

    Heavy (200 users):
        uv run locust -f research/load-testing/locustfile.py \
            --host http://localhost:8000 --users 200 --spawn-rate 20 --run-time 30s --headless
"""

import random

from locust import HttpUser, between, task

WORDS = ["love", "time", "world", "life", "day", "man", "way", "thing", "word", "work"]
PREFIXES = ["eth", "ety", "etym", "lang", "wor", "hel", "mot", "fat"]


class User(HttpUser):
    """Simulates a user browsing etymology graphs."""

    wait_time = between(1, 3)

    @task(3)
    def view_graph(self):
        """Look up a word's etymology."""
        self.client.get(f"/graph/{random.choice(WORDS)}", name="/graph/{word}")

    @task(2)
    def search(self):
        """Type in search box."""
        self.client.get(f"/search?q={random.choice(PREFIXES)}", name="/search")

    @task(1)
    def random_word(self):
        """Click random button."""
        self.client.get("/random")
