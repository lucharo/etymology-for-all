"""Load testing for Etymology API.

In one terminal, start the API:
    uv run uvicorn backend.main:app

In another terminal, run Locust (from project root):
    uv run locust -f research/load-testing/locustfile.py --host http://localhost:8000

Open http://localhost:8089 (Locust web UI) to configure and run tests.

Test scenarios:
    Normal:  20 users, 5/sec spawn, 60s  (typical usage)
    Stress:  100 users, 10/sec spawn, 60s  (busy day)
    HN hug:  500+ users, 50/sec spawn, 120s  (front page spike)

Headless example:
    uv run locust ... --users 100 --spawn-rate 10 --run-time 60s --headless
"""

import random

from locust import HttpUser, between, task

# Common test data
COMMON_WORDS = ["love", "time", "world", "life", "day", "man", "way", "thing", "word", "work"]
SEARCH_PREFIXES = ["eth", "ety", "etym", "lang", "wor", "hel", "mot", "fat"]


class CasualUser(HttpUser):
    """Typical user: browses slowly, reads content between clicks."""

    weight = 3  # 3x more common than power users
    wait_time = between(2, 5)

    @task(3)
    def view_graph(self):
        """Look up a word's etymology."""
        self.client.get(f"/graph/{random.choice(COMMON_WORDS)}", name="/graph/{word}")

    @task(2)
    def search(self):
        """Type in search box."""
        self.client.get(f"/search?q={random.choice(SEARCH_PREFIXES)}", name="/search")

    @task(1)
    def random_word(self):
        """Click random button."""
        self.client.get("/random")


class PowerUser(HttpUser):
    """Engaged user: explores quickly, clicks many words."""

    weight = 1
    wait_time = between(0.5, 2)

    @task(5)
    def view_graph(self):
        """Rapidly explore word etymologies."""
        self.client.get(f"/graph/{random.choice(COMMON_WORDS)}", name="/graph/{word}")

    @task(3)
    def search(self):
        """Quick searches."""
        self.client.get(f"/search?q={random.choice(SEARCH_PREFIXES)}", name="/search")

    @task(2)
    def random_word(self):
        """Spam random button."""
        self.client.get("/random")


class HNVisitor(HttpUser):
    """HN spike: lands on site, looks at 1-3 words, leaves."""

    weight = 0  # Enable for spike tests, disable CasualUser/PowerUser
    wait_time = between(3, 8)  # Reading the graph takes time

    def on_start(self):
        """Each visitor looks at a few words then bounces."""
        self.words_to_view = random.randint(1, 3)
        self.words_viewed = 0

    @task
    def view_graph(self):
        """Look at a word, maybe leave."""
        self.client.get(f"/graph/{random.choice(COMMON_WORDS)}", name="/graph/{word}")
        self.words_viewed += 1
        if self.words_viewed >= self.words_to_view:
            self.stop()  # Bounce after viewing 1-3 words
