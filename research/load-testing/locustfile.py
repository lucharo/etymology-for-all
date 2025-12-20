"""Load testing for Etymology API.

Run with:
    uv run locust -f locustfile.py --host http://localhost:8000

Then open http://localhost:8089 to configure and start the test.
"""

from locust import HttpUser, between, task


class EtymologyUser(HttpUser):
    """Simulates a typical user browsing etymology graphs."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    @task(3)
    def search_common_word(self):
        """Search for common English words."""
        words = ["love", "time", "world", "life", "day", "man", "way", "thing", "word", "work"]
        import random

        word = random.choice(words)
        self.client.get(f"/graph/{word}", name="/graph/{word}")

    @task(2)
    def search_with_autocomplete(self):
        """Simulate typing in search box."""
        prefixes = ["eth", "ety", "etym", "lang", "wor"]
        import random

        prefix = random.choice(prefixes)
        self.client.get(f"/search?q={prefix}", name="/search?q={prefix}")

    @task(1)
    def random_word(self):
        """Click the random word button."""
        self.client.get("/random")

    @task(1)
    def health_check(self):
        """Health check endpoint."""
        self.client.get("/health")
