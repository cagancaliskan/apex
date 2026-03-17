# API Reference

Complete REST and WebSocket API documentation for the F1 Race Strategy Workbench.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Health Endpoints](#health-endpoints)
4. [Session Endpoints](#session-endpoints)
5. [State Endpoints](#state-endpoints)
6. [Simulation Endpoints](#simulation-endpoints)
7. [Live Race Endpoints](#live-race-endpoints)
8. [Championship Endpoints](#championship-endpoints)
9. [Strategy Explainability Endpoints](#strategy-explainability-endpoints)
10. [Weather Endpoints](#weather-endpoints)
11. [Strategy Endpoints](#strategy-endpoints)
12. [Replay Endpoints](#replay-endpoints)
13. [WebSocket API](#websocket-api)
14. [Error Handling](#error-handling)
15. [Rate Limiting](#rate-limiting)
16. [Examples](#examples)

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
  "version": "2.0.1",
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
  "version": "2.0.1",
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

## Simulation Endpoints

### POST /api/simulation/load/{year}/{round_num}

Load and start a race simulation from FastF1 historical data.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `year` | integer | Race year (2018-2025) |
| `round_num` | integer | Round number in the season |

**Response:** `200 OK`
```json
{
  "status": "ok",
  "year": 2023,
  "round": 22,
  "session_name": "Abu Dhabi Grand Prix"
}
```

### POST /api/simulation/stop

Stop the current simulation.

**Response:** `200 OK`
```json
{
  "status": "ok",
  "message": "Simulation stopped"
}
```

### POST /api/simulation/speed/{speed}

Set simulation playback speed.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `speed` | float | Playback speed multiplier (1, 5, 10, 20, 50) |

**Response:** `200 OK`
```json
{
  "status": "ok",
  "speed": 10.0
}
```

### GET /api/simulation/status

Get current simulation status.

**Response:** `200 OK`
```json
{
  "running": true,
  "year": 2023,
  "round": 22,
  "current_lap": 35,
  "total_laps": 58,
  "speed": 10.0
}
```

---

## Live Race Endpoints

> **New in v2.1** — Real-time F1 session tracking via OpenF1 API.

### POST /api/live/start

Start live race tracking. Automatically detects the current active session if no `session_key` is provided.

**Request Body (optional):**
```json
{
  "session_key": 9999
}
```

**Response:** `200 OK`
```json
{
  "status": "started",
  "session_key": 9999,
  "session_name": "Race"
}
```

**Errors:**
- `400` — No active sessions found
- `409` — Live tracking already running

### POST /api/live/stop

Stop live race tracking.

**Response:** `200 OK`
```json
{
  "status": "stopped"
}
```

### GET /api/live/status

Get current live tracking status.

**Response:** `200 OK`
```json
{
  "running": true,
  "session_key": 9999,
  "current_lap": 42,
  "poll_interval_seconds": 5
}
```

### GET /api/live/active-sessions

List currently active F1 sessions from OpenF1.

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "session_key": 9999,
      "session_name": "Race",
      "session_type": "Race",
      "circuit_short_name": "Bahrain",
      "country_name": "Bahrain"
    }
  ]
}
```

---

## Championship Endpoints

> **New in v2.1** — Multi-race Monte Carlo championship prediction.

### POST /api/championship/simulate

Run a full championship simulation. This is a long-running endpoint (20-60s) that simulates the remaining season using Monte Carlo methods.

**Request Body:**
```json
{
  "year": 2023,
  "start_from_round": 10,
  "n_simulations": 200,
  "include_sprints": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `year` | integer | 2023 | Season year |
| `start_from_round` | integer | 1 | Simulate from this round onwards |
| `n_simulations` | integer | 200 | Number of Monte Carlo iterations (1-1000) |
| `include_sprints` | boolean | true | Include sprint race points |

**Response:** `200 OK`
```json
{
  "year": 2023,
  "start_from_round": 10,
  "total_rounds": 22,
  "completed_rounds": 9,
  "remaining_rounds": 13,
  "n_simulations": 200,
  "elapsed_seconds": 35.2,
  "calendar": [
    {
      "round_number": 1,
      "event_name": "Bahrain Grand Prix",
      "country": "Bahrain",
      "location": "Sakhir",
      "total_laps": 57,
      "is_sprint_weekend": false,
      "completed": true
    }
  ],
  "wdc": [
    {
      "driver_number": 1,
      "name": "Max VERSTAPPEN",
      "team": "Red Bull Racing",
      "team_colour": "3671C6",
      "current_points": 375,
      "simulated_points_mean": 66.2,
      "simulated_points_std": 28.1,
      "total_points_mean": 441.2,
      "total_points_p10": 398,
      "total_points_p90": 488,
      "predicted_position": 1.1,
      "prob_champion": 0.72,
      "prob_top3": 0.98,
      "prob_top10": 1.0
    }
  ],
  "wcc": [
    {
      "team": "Red Bull Racing",
      "team_colour": "3671C6",
      "driver_numbers": [1, 11],
      "current_points": 650,
      "total_points_mean": 812.5,
      "total_points_p10": 740,
      "total_points_p90": 880,
      "predicted_position": 1.05,
      "prob_champion": 0.89
    }
  ]
}
```

### GET /api/championship/calendar/{year}

Get season calendar with race entries. Lightweight endpoint — no simulation.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `year` | integer | Season year (2018-2025) |

**Response:** `200 OK`
```json
{
  "calendar": [
    {
      "round_number": 1,
      "event_name": "Bahrain Grand Prix",
      "country": "Bahrain",
      "location": "Sakhir",
      "total_laps": 57,
      "is_sprint_weekend": false,
      "completed": true
    }
  ]
}
```

### GET /api/championship/standings/{year}/{up_to_round}

Get actual championship standings after a specific round (from FastF1 data).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `year` | integer | Season year |
| `up_to_round` | integer | Include results up to this round |

**Response:** `200 OK`
```json
{
  "drivers": [
    {
      "driver_number": 1,
      "name": "Max VERSTAPPEN",
      "team": "Red Bull Racing",
      "points": 375,
      "positions": [1, 1, 2, 1, 1, 1, 1, 5, 1]
    }
  ]
}
```

---

## Strategy Explainability Endpoints

> **New in v2.1** — Human-readable strategy explanations with sensitivity analysis.

### GET /api/strategy/explain/{driver_number}

Get detailed strategy explanation for a specific driver including factor rankings and sensitivity analysis.

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
  "explanation": "Stay out — tyres in good condition with 15 laps of life remaining.",
  "factors": [
    {
      "name": "tyre_condition",
      "weight": 0.35,
      "value": 0.82,
      "description": "Tyre degradation rate is below average"
    },
    {
      "name": "track_position",
      "weight": 0.25,
      "value": 0.95,
      "description": "Clean air advantage in P1"
    },
    {
      "name": "undercut_threat",
      "weight": 0.20,
      "value": 0.15,
      "description": "Low undercut risk from cars behind"
    }
  ],
  "sensitivity": {
    "tyre_age_+5": { "recommendation": "CONSIDER_PIT", "confidence": 0.62 },
    "safety_car": { "recommendation": "PIT_NOW", "confidence": 0.91 },
    "rain_probability_30pct": { "recommendation": "STAY_OUT", "confidence": 0.70 }
  }
}
```

---

## Weather Endpoints

> **New in v2.1** — Weather data via OpenMeteo API integration.

### GET /api/weather/current/{circuit_key}

Get current weather conditions for a circuit.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `circuit_key` | string | Circuit identifier (e.g., "bahrain", "monza") |

**Response:** `200 OK`
```json
{
  "circuit": "bahrain",
  "track_temp": 42.5,
  "air_temp": 28.3,
  "humidity": 45,
  "wind_speed": 12.5,
  "wind_direction": "NW",
  "rainfall": 0.0,
  "is_raining": false,
  "timestamp": "2024-03-02T15:30:00Z"
}
```

### GET /api/weather/forecast/{circuit_key}

Get weather forecast for the next hours at a circuit.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `circuit_key` | string | Circuit identifier |

**Response:** `200 OK`
```json
{
  "circuit": "bahrain",
  "forecast": [
    {
      "time": "2024-03-02T16:00:00Z",
      "air_temp": 27.8,
      "humidity": 48,
      "wind_speed": 14.0,
      "rain_probability": 0.05,
      "rainfall_mm": 0.0
    },
    {
      "time": "2024-03-02T17:00:00Z",
      "air_temp": 26.5,
      "humidity": 52,
      "wind_speed": 15.2,
      "rain_probability": 0.10,
      "rainfall_mm": 0.0
    }
  ]
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
  "pit_rejoin": {
    "rejoin_lap": 36,
    "rejoin_position": 4,
    "traffic_density": "LOW",
    "gap_to_ahead": 2.5,
    "gap_to_behind": 1.2
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

// With authentication (when RSW_WS_AUTH_REQUIRED=true)
const ws = new WebSocket('ws://localhost:8000/ws?token=<jwt_token>');
```

### Client → Server Messages

**Start Simulation (Replay Mode):**
```json
{
  "type": "start_session",
  "year": 2023,
  "round_num": 22
}
```

**Stop Simulation:**
```json
{
  "type": "stop_session"
}
```

**Set Speed:**
```json
{
  "type": "set_speed",
  "speed": 10.0
}
```

**Start Live Tracking (v2.1):**
```json
{
  "type": "start_live",
  "session_key": 9999
}
```
> If `session_key` is omitted, auto-detects the latest active session.

**Stop Live Tracking (v2.1):**
```json
{
  "type": "stop_live"
}
```

**Keepalive:**
```json
{
  "type": "ping"
}
```

### Server → Client Messages

**State Update** (sent continuously during simulation or live tracking):
```json
{
  "type": "state_update",
  "data": {
    "session_key": 9999,
    "session_name": "Race",
    "current_lap": 35,
    "total_laps": 57,
    "track_status": "GREEN",
    "weather": { "track_temp": 42.5, "is_raining": false },
    "drivers": {
      "1": {
        "driver_number": 1,
        "name_acronym": "VER",
        "position": 1,
        "last_lap_time": 92.456,
        "compound": "MEDIUM",
        "tyre_age": 15,
        "pit_recommendation": "STAY_OUT",
        "pit_confidence": 0.85
      }
    }
  }
}
```

**Session Started:**
```json
{
  "type": "session_started",
  "year": 2023,
  "round": 22
}
```

**Session Stopped:**
```json
{
  "type": "session_stopped"
}
```

**Live Started (v2.1):**
```json
{
  "type": "live_started"
}
```

**Live Stopped (v2.1):**
```json
{
  "type": "live_stopped"
}
```

**Speed Set:**
```json
{
  "type": "speed_set",
  "speed": 10.0
}
```

**Pong (keepalive response):**
```json
{
  "type": "pong"
}
```

**Error:**
```json
{
  "type": "error",
  "message": "Session not found"
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
