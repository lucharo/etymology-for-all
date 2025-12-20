# Load Testing Research

## How Rate Limiting Works

**Per-IP rate limiting** means each user's IP address has its own request bucket.

```
User A (IP: 1.2.3.4) → 30 requests/min allowed
User B (IP: 5.6.7.8) → 30 requests/min allowed (separate bucket)
User C (IP: 9.10.11.12) → 30 requests/min allowed (separate bucket)
```

So 1000 users = 30,000 requests/minute total capacity.

### How it works with Cloudflare + HF Spaces

```
User Browser (IP: 1.2.3.4)
    ↓
Cloudflare (static frontend)
    ↓
User's browser makes API calls directly to:
    ↓
HF Spaces backend (sees user's real IP via X-Forwarded-For header)
```

Each user's browser talks directly to the API. The rate limiter sees their real IP.

## What happens when limits are exceeded?

| Scenario | HTTP Status | What happens |
|----------|-------------|--------------|
| User exceeds their rate limit | 429 Too Many Requests | Request rejected immediately |
| Server overloaded (too many total requests) | 503 or timeout | Requests queue, slow down, may fail |

**429 is intentional throttling** - "slow down, you're making too many requests"
**503/timeout is capacity issue** - "server can't keep up with total load"

## Current Rate Limits

| Endpoint | Limit | Why |
|----------|-------|-----|
| `/graph/{word}` | 60/min | Main feature, generous limit |
| `/random` | 30/min | Lower to prevent abuse |
| `/search` | 120/min | Autocomplete fires rapidly while typing |

## Running Load Tests

```bash
# Start the API
uv run uvicorn backend.main:app &

# Run Locust (opens web UI at http://localhost:8089)
uv run locust -f research/load-testing/locustfile.py --host http://localhost:8000
```

## Results

TODO: Run against HF Spaces deployment and document:
- Max concurrent users before degradation
- Average response times under load
- Memory usage patterns
