# Load Testing Research

## Two Types of Tests

| Test | Purpose | Rate Limiting |
|------|---------|---------------|
| **Load test** | Server capacity - can it handle N users? | Off |
| **Rate limit test** | Throttling works - blocks excessive requests? | On |

Note: Locust runs all users from one IP, so rate limit tests show all users sharing one bucket (not realistic for production where each user has their own IP).

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

## Current Rate Limits (based on p95 latency)

Rate limits are calculated from 95th percentile latency to ensure the server
isn't overwhelmed even under load:

```
limit ≈ 60 seconds / p95_latency
```

| Endpoint | p95 Latency | Calculated | Limit Set |
|----------|-------------|------------|-----------|
| `/graph/{word}` | 3100ms | 19/min | 20/min |
| `/random` | 1200ms | 50/min | 50/min |
| `/search` | 520ms | 115/min | 120/min |

## Running Load Tests

See [`locustfile.py`](locustfile.py) docstring for setup instructions.

## Load Test Results (rate limiting disabled)

| Users | Failures | p50 Latency | Throughput |
|-------|----------|-------------|------------|
| 20 | 0% | 150ms | 7 req/s |
| 200 | 0% | 10 sec | 10 req/s |

Server handles 20 users well. At 200 users it slows significantly but doesn't crash.

### Key optimization
Query only the definitions needed per graph instead of loading all 40K.
This improved `/graph` from 1900ms → 530ms (3.6x faster).
