# API Versioning Strategy

**Date**: 2026-02-11
**Task**: Medium Priority #5 - API Versioning
**Status**: COMPLETE

---

## Overview

AlphaVelocity uses **URL-prefix versioning** for its API. All versioned endpoints live under `/api/v1/`. Legacy (unversioned) endpoints remain available but return RFC 8594 deprecation headers directing consumers to their v1 replacements.

### Base Paths

| Path Prefix | Status | Description |
|-------------|--------|-------------|
| `/api/v1/`  | **Current** | Recommended for all new integrations |
| `/` (root)  | **Deprecated** | Legacy endpoints; will be removed after sunset date |

---

## Deprecated Endpoints

The following legacy endpoints have v1 replacements and return deprecation headers on every response:

| Legacy Endpoint | Method | V1 Replacement |
|-----------------|--------|----------------|
| `/momentum/{ticker}` | GET | `/api/v1/momentum/{ticker}` |
| `/momentum/top/{limit}` | GET | `/api/v1/momentum/top/{limit}` |
| `/portfolio/analysis` | GET | `/api/v1/portfolio/analysis` |
| `/portfolio/analyze` | POST | `/api/v1/portfolio/analyze` |
| `/portfolio/analysis/by-categories` | GET | `/api/v1/portfolio/analysis/by-categories` |
| `/portfolio/analyze/by-categories` | POST | `/api/v1/portfolio/analyze/by-categories` |
| `/categories` | GET | `/api/v1/categories` |
| `/categories/{name}/analysis` | GET | `/api/v1/categories/{name}/analysis` |
| `/categories/{name}/tickers` | GET | `/api/v1/categories/{name}/tickers` |
| `/cache/status` | GET | `/api/v1/cache/status` |
| `/cache/clear` | POST | `/api/v1/cache/clear` |

---

## Deprecation Headers

When you call a deprecated legacy endpoint, the response includes three headers per [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594):

| Header | Value | Description |
|--------|-------|-------------|
| `Deprecation` | `true` | Indicates the endpoint is deprecated |
| `Sunset` | `2026-06-30` | Date after which the endpoint may be removed |
| `Link` | `</api/v1/...>; rel="successor-version"` | URL of the replacement endpoint |

### Example

```bash
curl -i http://localhost:8000/momentum/NVDA
```

Response headers:

```
HTTP/1.1 200 OK
Deprecation: true
Sunset: 2026-06-30
Link: </api/v1/momentum/NVDA>; rel="successor-version"
Content-Type: application/json
...
```

The response body is identical to the legacy endpoint — only headers are added.

---

## Migration Guide

### Step 1: Update Base URL

Change your API base URL from the root path to `/api/v1/`:

```diff
- GET /momentum/NVDA
+ GET /api/v1/momentum/NVDA

- POST /portfolio/analyze
+ POST /api/v1/portfolio/analyze

- GET /categories
+ GET /api/v1/categories
```

### Step 2: Handle Deprecation Headers (Optional)

If you want advance notice of future deprecations, check for the `Deprecation` header in responses:

```python
response = requests.get("https://api.alphavelocity.com/api/v1/momentum/NVDA")
if response.headers.get("Deprecation") == "true":
    sunset = response.headers.get("Sunset", "unknown")
    link = response.headers.get("Link", "")
    print(f"Warning: endpoint deprecated, sunset {sunset}, migrate to {link}")
```

### Step 3: Adopt V1-Only Features

V1 introduces capabilities not available on legacy endpoints:

- **Pagination** — `page` and `page_size` query parameters
- **Batch operations** — `POST /api/v1/momentum/batch` for concurrent scoring
- **Performance metrics** — `GET /api/v1/metrics/performance`
- **Advanced cache admin** — pattern-based clearing, key listing, cache warmup

### Step 4: Test

Verify your integration works against v1 endpoints before the sunset date.

---

## Timeline

| Date | Event |
|------|-------|
| 2026-01-24 | V1 router introduced |
| 2026-02-11 | Legacy endpoints marked deprecated with headers |
| **2026-06-30** | **Sunset date** — legacy endpoints may be removed |

After the sunset date, legacy endpoints may return `410 Gone` or be removed entirely. Migrate before this date to avoid disruption.

---

## Endpoints Not Yet Migrated

The following legacy endpoints do **not** have v1 replacements yet. They remain stable and do **not** return deprecation headers:

- **Watchlist** — `/watchlist/*`
- **Compare** — `/compare/*`
- **Historical** — `/historical/*`
- **Database** — `/database/*`
- **Category Management** — `/categories/manage/*`
- **Health** — `GET /`
- **Daily Cache** — `/cache/daily/*`

These endpoints will continue to work unchanged until v1 equivalents are created.

---

## V1 Feature Highlights

Features available exclusively in v1:

### Pagination

All list endpoints support offset pagination:

```bash
GET /api/v1/momentum/top?page=2&page_size=10&sort_by=momentum_score&sort_order=desc
```

Response includes metadata:

```json
{
  "items": [...],
  "page": 2,
  "page_size": 10,
  "total_items": 45,
  "total_pages": 5,
  "has_next": true,
  "has_previous": true
}
```

### Batch Operations

Score multiple tickers concurrently (~8x faster than sequential):

```bash
POST /api/v1/momentum/batch
Content-Type: application/json

{"tickers": ["NVDA", "AAPL", "MSFT", "META", "GOOGL"]}
```

### Performance Metrics

Monitor API health and identify slow endpoints:

```bash
GET /api/v1/metrics/performance
GET /api/v1/metrics/slow?threshold_ms=500
GET /api/v1/metrics/endpoints
```

### Advanced Cache Administration

```bash
GET  /api/v1/cache/info          # Detailed cache stats
GET  /api/v1/cache/keys?pattern=price:*   # List keys by pattern
DELETE /api/v1/cache/clear?pattern=momentum:*  # Clear by pattern
POST /api/v1/cache/warmup        # Pre-populate cache
```

### Enhanced Rate Limiting

V1 endpoints have tiered rate limits:

| Tier | Limit | Applies To |
|------|-------|-----------|
| Public | 100/min (200/min authenticated) | Most read endpoints |
| Expensive | 10/min | Custom portfolio analysis |
| Bulk | 5/min | Cache clear, warmup |
| Admin | 5/min | Metrics reset |

---

## Client Examples

### curl

```bash
# Get momentum score
curl https://api.alphavelocity.com/api/v1/momentum/NVDA

# Batch momentum (multiple tickers)
curl -X POST https://api.alphavelocity.com/api/v1/momentum/batch \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["NVDA", "AAPL", "MSFT"]}'

# Paginated top stocks
curl "https://api.alphavelocity.com/api/v1/momentum/top?page=1&page_size=10"

# Portfolio analysis
curl https://api.alphavelocity.com/api/v1/portfolio/analysis
```

### Python (requests)

```python
import requests

BASE = "https://api.alphavelocity.com/api/v1"

# Single ticker
score = requests.get(f"{BASE}/momentum/NVDA").json()
print(f"NVDA momentum: {score['momentum_score']}")

# Batch scoring
batch = requests.post(f"{BASE}/momentum/batch", json={
    "tickers": ["NVDA", "AAPL", "MSFT", "META"]
}).json()
for result in batch["results"]:
    print(f"{result['ticker']}: {result['momentum_score']}")

# Paginated listing
page = requests.get(f"{BASE}/momentum/top", params={
    "page": 1, "page_size": 10, "sort_order": "desc"
}).json()
print(f"Page {page['page']} of {page['total_pages']}")
```

### JavaScript (fetch)

```javascript
const BASE = "https://api.alphavelocity.com/api/v1";

// Single ticker
const score = await fetch(`${BASE}/momentum/NVDA`).then(r => r.json());
console.log(`NVDA momentum: ${score.momentum_score}`);

// Batch scoring
const batch = await fetch(`${BASE}/momentum/batch`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ tickers: ["NVDA", "AAPL", "MSFT"] }),
}).then(r => r.json());

// Paginated top stocks
const page = await fetch(`${BASE}/momentum/top?page=1&page_size=10`)
  .then(r => r.json());
```

---

## Configuration Reference

Operators can customize deprecation behavior via `backend/config/deprecation_config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `SUNSET_DATE` | `"2026-06-30"` | ISO 8601 date for the `Sunset` header. Set to `None` to omit. |
| `_DEPRECATED_ROUTE_DEFINITIONS` | 11 routes | List of `(regex, replacement)` tuples defining which legacy paths are deprecated. |

To change the sunset date:

```python
# backend/config/deprecation_config.py
SUNSET_DATE: str | None = "2026-09-30"  # Extend to September
```

To add a newly deprecated route:

```python
_DEPRECATED_ROUTE_DEFINITIONS: list[tuple[str, str]] = [
    # ... existing entries ...
    (r"^/new-legacy-path$", "/api/v1/new-path"),
]
```

---

## Implementation Files

| File | Purpose |
|------|---------|
| `backend/api/__init__.py` | Mounts v1 router at `/api` prefix |
| `backend/api/v1/__init__.py` | Assembles all v1 sub-routers |
| `backend/api/v1/momentum.py` | Core momentum endpoints |
| `backend/api/v1/momentum_paginated.py` | Paginated momentum endpoints |
| `backend/api/v1/momentum_batch.py` | Batch & concurrent momentum |
| `backend/api/v1/portfolio.py` | Portfolio analysis endpoints |
| `backend/api/v1/portfolio_paginated.py` | Paginated portfolio endpoints |
| `backend/api/v1/categories.py` | Category listing & analysis |
| `backend/api/v1/cache.py` | Basic cache operations |
| `backend/api/v1/cache_admin.py` | Advanced cache administration |
| `backend/api/v1/metrics.py` | Performance metrics |
| `backend/config/deprecation_config.py` | Deprecated route definitions & sunset date |
| `backend/middleware/deprecation_middleware.py` | Adds RFC 8594 headers to deprecated responses |
| `backend/main.py` | Registers middleware and mounts routers |

---

**Status**: API versioning is complete. All consumers should migrate to `/api/v1/` before 2026-06-30.
