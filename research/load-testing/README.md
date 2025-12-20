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

## Results (Local, 20 concurrent users, 20 seconds)

| Endpoint | Median | 95th % | Max |
|----------|--------|--------|-----|
| `/graph/{word}` | 530ms | 3100ms | 3600ms |
| `/search` | 130ms | 520ms | 1200ms |
| `/random` | 140ms | 1200ms | 1900ms |
| `/health` | 8ms | 58ms | 77ms |

**Throughput**: ~8 req/sec with 20 users, 0 failures.

### Key optimization
Query only the ~7 definitions needed per graph instead of loading all 40K.
This improved `/graph` from 1900ms → 530ms (3.6x faster).
