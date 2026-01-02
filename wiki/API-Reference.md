# API Reference

Complete REST and WebSocket API documentation for the F1 Race Strategy Workbench.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Health Endpoints](#health-endpoints)
4. [Session Endpoints](#session-endpoints)
5. [State Endpoints](#state-endpoints)
6. [Strategy Endpoints](#strategy-endpoints)
7. [Replay Endpoints](#replay-endpoints)
8. [WebSocket API](#websocket-api)
9. [Error Handling](#error-handling)
10. [Rate Limiting](#rate-limiting)
11. [Examples](#examples)

---

## Overview

### Base URL

```
Production: https://api.racestrategy.dev/v1
Development: http://localhost:8000
```

### Response Format

All responses are JSON with the following structure:

**Success:**
```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2024-01-15T14:30:00Z",
    "request_id": "req_123abc"
  }
}
```

**Error:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Session not found",
    "details": { ... }
  }
}
```

### Content Type

```
Content-Type: application/json
Accept: application/json
```

---

## Authentication

### JWT Bearer Token

```http
Authorization: Bearer <token>
```

**Obtain a token:**
```http
POST /auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### API Key

```http
X-API-Key: your-api-key-here
```

### Development Mode

Authentication can be disabled in development:
```env
RSW_AUTH_ENABLED=false
```

---

## Health Endpoints

### GET /health

Comprehensive health check with dependency status.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2024-01-15T14:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 5.2
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1.1
    },
    "openf1": {
      "status": "healthy",
      "latency_ms": 120.5
    }
  }
}
```

### GET /health/live

Kubernetes liveness probe.

**Response:** `200 OK`
```json
{
  "status": "alive"
}
```

### GET /health/ready

Kubernetes readiness probe.

**Response:** `200 OK` or `503 Service Unavailable`
```json
{
  "status": "ready"
}
```

### GET /version

Application version information.

**Response:** `200 OK`
```json
{
  "version": "1.0.0",
  "environment": "production",
  "python": "3.11"
}
```

---

## Session Endpoints

### GET /api/sessions

List available race sessions.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `year` | integer | Filter by year (e.g., 2024) |
| `country` | string | Filter by country name |
| `session_name` | string | Filter by session type (Race, Qualifying) |
| `limit` | integer | Maximum results (default: 50) |
| `offset` | integer | Pagination offset |

**Example:**
```http
GET /api/sessions?year=2024&session_name=Race
```

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "session_key": 9999,
      "meeting_key": 1234,
      "session_name": "Race",
      "session_type": "Race",
      "circuit_short_name": "Bahrain",
      "country_name": "Bahrain",
      "date_start": "2024-03-02T15:00:00Z",
      "year": 2024
    }
  ],
  "total": 24,
  "limit": 50,
  "offset": 0
}
```

### GET /api/sessions/{session_key}

Get details for a specific session.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_key` | integer | Unique session identifier |

**Response:** `200 OK`
```json
{
  "session_key": 9999,
  "meeting_key": 1234,
  "session_name": "Race",
  "circuit_short_name": "Bahrain",
  "country_name": "Bahrain",
  "date_start": "2024-03-02T15:00:00Z",
  "total_laps": 57,
  "drivers": [
    {
      "driver_number": 1,
      "name_acronym": "VER",
      "full_name": "Max VERSTAPPEN",
      "team_name": "Red Bull Racing",
      "team_colour": "3671C6"
    }
  ]
}
```

---

## State Endpoints

### GET /api/state

Get current race state.

**Response:** `200 OK`
```json
{
  "session_key": 9999,
  "session_name": "Race",
  "current_lap": 35,
  "total_laps": 57,
  "flags": ["GREEN"],
  "safety_car": false,
  "virtual_safety_car": false,
  "timestamp": "2024-03-02T15:45:00Z",
  "drivers": {
    "1": {
      "driver_number": 1,
      "name_acronym": "VER",
      "position": 1,
      "current_lap": 35,
      "last_lap_time": 92.456,
      "best_lap_time": 91.234,
      "gap_to_leader": 0.0,
      "gap_to_ahead": null,
      "compound": "MEDIUM",
      "tyre_age": 15,
      "stint_number": 2
    }
  }
}
```

### GET /api/state/drivers

Get all driver states.

**Response:** `200 OK`
```json
{
  "drivers": [
    {
      "driver_number": 1,
      "name_acronym": "VER",
      "full_name": "Max VERSTAPPEN",
      "team_name": "Red Bull Racing",
      "position": 1,
      "gap_to_leader": 0.0,
      "last_lap_time": 92.456,
      "compound": "MEDIUM",
      "tyre_age": 15
    }
  ]
}
```

### GET /api/state/drivers/{driver_number}

Get specific driver state.

**Response:** `200 OK`
```json
{
  "driver_number": 1,
  "name_acronym": "VER",
  "full_name": "Max VERSTAPPEN",
  "team_name": "Red Bull Racing",
  "position": 1,
  "current_lap": 35,
  "last_lap_time": 92.456,
  "best_lap_time": 91.234,
  "sector_1": 28.123,
  "sector_2": 35.456,
  "sector_3": 28.877,
  "gap_to_leader": 0.0,
  "gap_to_ahead": null,
  "compound": "MEDIUM",
  "tyre_age": 15,
  "stint_number": 2,
  "lap_in_stint": 15,
  "is_pit_out_lap": false
}
```

---

## Strategy Endpoints

### GET /api/strategy/{driver_number}

Get strategy recommendation for a driver.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `driver_number` | integer | Driver number (1-99) |

**Response:** `200 OK`
```json
{
  "driver_number": 1,
  "recommendation": "STAY_OUT",
  "confidence": 0.85,
  "pit_window": {
    "min_lap": 38,
    "max_lap": 45,
    "ideal_lap": 42,
    "confidence": 0.82
  },
  "degradation": {
    "deg_slope": 0.065,
    "base_pace": 91.5,
    "cliff_risk": 0.25
  },
  "predictions": {
    "next_5_laps": [92.5, 92.6, 92.65, 92.7, 92.8]
  },
  "threats": {
    "undercut_viable": false,
    "overcut_viable": true
  },
  "explanation": "Stay out - tyres in good condition. Pit window opens lap 38."
}
```

### GET /api/strategy/{driver_number}/simulation

Run Monte Carlo simulation for pit scenarios.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `pit_lap` | integer | Simulate pitting on this lap |
| `n_simulations` | integer | Number of simulations (default: 500) |

**Response:** `200 OK`
```json
{
  "driver_number": 1,
  "pit_lap": 42,
  "n_simulations": 500,
  "outcomes": {
    "position_probabilities": {
      "1": 0.65,
      "2": 0.25,
      "3": 0.08,
      "4": 0.02
    },
    "expected_position": 1.47,
    "position_std": 0.72,
    "expected_points": 23.5,
    "prob_win": 0.65,
    "prob_podium": 0.98,
    "prob_points": 1.0,
    "best_case": 1,
    "worst_case": 4
  }
}
```

### GET /api/strategy/comparison

Compare strategies for all drivers.

**Response:** `200 OK`
```json
{
  "strategies": [
    {
      "driver_number": 1,
      "recommendation": "STAY_OUT",
      "confidence": 0.85,
      "ideal_pit_lap": 42
    },
    {
      "driver_number": 11,
      "recommendation": "PIT_NOW",
      "confidence": 0.78,
      "ideal_pit_lap": 35
    }
  ]
}
```

---

## Replay Endpoints

### GET /api/replay/sessions

List cached sessions available for replay.

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "session_key": 9999,
      "session_name": "Bahrain Grand Prix - Race",
      "date": "2024-03-02",
      "total_laps": 57,
      "cached_at": "2024-03-03T10:00:00Z"
    }
  ]
}
```

### POST /api/replay/{session_key}/start

Start replay of a session.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_key` | integer | Session to replay |

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `speed` | float | Playback speed (default: 1.0) |
| `start_lap` | integer | Start from this lap (default: 1) |

**Response:** `200 OK`
```json
{
  "status": "started",
  "session_key": 9999,
  "speed": 1.0,
  "current_lap": 1,
  "total_laps": 57
}
```

### POST /api/replay/control

Control active replay.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | string | `play`, `pause`, `stop`, `speed` |
| `speed` | float | New playback speed (with action=speed) |

**Response:** `200 OK`
```json
{
  "status": "paused",
  "current_lap": 25
}
```

### DELETE /api/replay

Stop and reset current replay.

**Response:** `200 OK`
```json
{
  "status": "stopped"
}
```

---

## WebSocket API

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

### Authentication

Send after connection:
```json
{
  "type": "auth",
  "token": "Bearer <jwt_token>"
}
```

### Subscribe to Updates

```json
{
  "type": "subscribe",
  "channels": ["state", "strategy", "messages"]
}
```

### Message Types

**State Update:**
```json
{
  "type": "state_update",
  "data": {
    "current_lap": 35,
    "drivers": { ... },
    "timestamp": "2024-03-02T15:45:00Z"
  }
}
```

**Strategy Update:**
```json
{
  "type": "strategy_update",
  "data": {
    "driver_number": 1,
    "recommendation": "CONSIDER_PIT",
    "reason": "Cliff risk increasing"
  }
}
```

**Race Control Message:**
```json
{
  "type": "race_control",
  "data": {
    "category": "Flag",
    "flag": "YELLOW",
    "message": "Yellow flag in sector 2",
    "lap_number": 35
  }
}
```

**Pit Stop:**
```json
{
  "type": "pit_stop",
  "data": {
    "driver_number": 1,
    "lap_number": 35,
    "pit_duration": 22.5
  }
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request - Invalid parameters |
| `401` | Unauthorized - Missing/invalid auth |
| `403` | Forbidden - Insufficient permissions |
| `404` | Not Found - Resource doesn't exist |
| `422` | Unprocessable Entity - Validation error |
| `429` | Too Many Requests - Rate limited |
| `500` | Internal Server Error |
| `503` | Service Unavailable |

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid driver number",
    "details": {
      "field": "driver_number",
      "value": 999,
      "constraint": "must be between 1 and 99"
    }
  }
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_REQUIRED` | No auth token provided |
| `INVALID_TOKEN` | Token expired or invalid |
| `PERMISSION_DENIED` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `VALIDATION_ERROR` | Input validation failed |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `SESSION_NOT_FOUND` | Session key invalid |
| `DRIVER_NOT_FOUND` | Driver number invalid |
| `INSUFFICIENT_DATA` | Not enough data for calculation |

---

## Rate Limiting

### Limits

| Tier | Requests/min | Burst |
|------|--------------|-------|
| Free | 60 | 10 |
| Basic | 300 | 50 |
| Pro | 1000 | 100 |
| Enterprise | Unlimited | - |

### Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705329600
```

### Rate Limit Response

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Retry after 30 seconds."
  }
}
```

---

## Examples

### cURL

```bash
# Get sessions
curl -X GET "http://localhost:8000/api/sessions?year=2024" \
  -H "Accept: application/json"

# Get strategy with auth
curl -X GET "http://localhost:8000/api/strategy/1" \
  -H "Authorization: Bearer <token>" \
  -H "Accept: application/json"

# Start replay
curl -X POST "http://localhost:8000/api/replay/9999/start?speed=2.0" \
  -H "Authorization: Bearer <token>"
```

### Python

```python
import httpx

async def get_strategy(driver_number: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/strategy/{driver_number}",
            headers={"Authorization": "Bearer <token>"}
        )
        return response.json()
```

### JavaScript

```javascript
// REST API
const response = await fetch('/api/sessions?year=2024');
const { sessions } = await response.json();

// WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Update:', message);
};
```

---

## OpenAPI Specification

Interactive API documentation is available at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## Next Steps

- [Python SDK](SDK.md) — Programmatic API access
- [WebSocket Guide](DEVELOPMENT.md#websocket) — Real-time integration
- [Troubleshooting](TROUBLESHOOTING.md) — Common API issues

---
**Next:** [[Python-SDK]]
