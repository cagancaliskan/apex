# Python SDK Documentation

Complete guide to programmatically accessing the F1 Race Strategy Workbench API.

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Client Reference](#client-reference)
4. [Sessions](#sessions)
5. [Race State](#race-state)
6. [Strategy](#strategy)
7. [WebSocket](#websocket)
8. [Error Handling](#error-handling)
9. [Advanced Usage](#advanced-usage)

---

## Installation

### From PyPI (Coming Soon)

```bash
pip install rsw-client
```

### From Source

```bash
pip install httpx websockets
```

---

## Quick Start

```python
import asyncio
from rsw_client import RSWClient

async def main():
    # Create client
    client = RSWClient(base_url="http://localhost:8000")
    
    # Get sessions
    sessions = await client.get_sessions(year=2024)
    print(f"Found {len(sessions)} sessions")
    
    # Get strategy for a driver
    strategy = await client.get_strategy(driver_number=1)
    print(f"Recommendation: {strategy.recommendation}")
    print(f"Pit window: Lap {strategy.pit_window.ideal_lap}")
    
    await client.close()

asyncio.run(main())
```

---

## Client Reference

### RSWClient

```python
from rsw_client import RSWClient

client = RSWClient(
    base_url="http://localhost:8000",
    api_key="your-api-key",           # Optional
    timeout=30.0,                      # Request timeout
    max_retries=3,                     # Retry count
)
```

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | str | Required | API base URL |
| `api_key` | str | None | API key for authentication |
| `jwt_token` | str | None | JWT token for authentication |
| `timeout` | float | 30.0 | Request timeout in seconds |
| `max_retries` | int | 3 | Maximum retry attempts |

### Context Manager

```python
async with RSWClient(base_url="http://localhost:8000") as client:
    sessions = await client.get_sessions()
```

---

## Sessions

### List Sessions

```python
# All sessions
sessions = await client.get_sessions()

# Filter by year
sessions = await client.get_sessions(year=2024)

# Filter by country
sessions = await client.get_sessions(country="Monaco")

# Filter by session type
sessions = await client.get_sessions(session_name="Race")

# Combine filters
sessions = await client.get_sessions(
    year=2024,
    country="Bahrain",
    session_name="Race"
)
```

### Session Object

```python
session = sessions[0]

print(session.session_key)        # 9999
print(session.session_name)       # "Race"
print(session.circuit_short_name) # "Bahrain"
print(session.country_name)       # "Bahrain"
print(session.date_start)         # datetime object
print(session.total_laps)         # 57
```

### Get Single Session

```python
session = await client.get_session(session_key=9999)

# Access drivers
for driver in session.drivers:
    print(f"{driver.name_acronym} - {driver.team_name}")
```

---

## Race State

### Get Current State

```python
state = await client.get_state()

print(f"Lap: {state.current_lap}/{state.total_laps}")
print(f"Safety Car: {state.safety_car}")
print(f"Flags: {state.flags}")
```

### Driver State

```python
# All drivers
for driver_num, driver in state.drivers.items():
    print(f"P{driver.position}: #{driver.driver_number} {driver.name_acronym}")
    print(f"  Gap: {driver.gap_to_leader}s")
    print(f"  Tyre: {driver.compound} ({driver.tyre_age} laps)")

# Specific driver
driver = await client.get_driver(driver_number=1)
print(f"{driver.full_name}: P{driver.position}")
```

### Driver Object Properties

| Property | Type | Description |
|----------|------|-------------|
| `driver_number` | int | Car number |
| `name_acronym` | str | Three-letter code |
| `full_name` | str | Full name |
| `team_name` | str | Team name |
| `position` | int | Current position |
| `current_lap` | int | Driver's lap count |
| `last_lap_time` | float | Last lap time |
| `best_lap_time` | float | Best lap time |
| `gap_to_leader` | float | Gap to P1 |
| `gap_to_ahead` | float | Gap to car ahead |
| `compound` | str | Tyre compound |
| `tyre_age` | int | Tyre age in laps |
| `stint_number` | int | Current stint |

---

## Strategy

### Get Strategy Recommendation

```python
strategy = await client.get_strategy(driver_number=1)

print(f"Recommendation: {strategy.recommendation}")
# "STAY_OUT", "PIT_NOW", "CONSIDER_PIT", "EXTEND_STINT"

print(f"Confidence: {strategy.confidence:.0%}")
print(f"Explanation: {strategy.explanation}")
```

### Pit Window

```python
window = strategy.pit_window

print(f"Pit window: Lap {window.min_lap} - {window.max_lap}")
print(f"Ideal lap: {window.ideal_lap}")
print(f"Window confidence: {window.confidence:.0%}")
```

### Degradation Model

```python
deg = strategy.degradation

print(f"Degradation rate: {deg.deg_slope:.3f} s/lap")
print(f"Base pace: {deg.base_pace:.3f}s")
print(f"Cliff risk: {deg.cliff_risk:.0%}")
```

### Predictions

```python
predictions = strategy.predictions

print("Next 5 laps predicted times:")
for i, time in enumerate(predictions.next_5_laps, 1):
    print(f"  Lap +{i}: {time:.3f}s")
```

### Monte Carlo Simulation

```python
simulation = await client.simulate_strategy(
    driver_number=1,
    pit_lap=42,
    n_simulations=500
)

print(f"Expected position: {simulation.expected_position:.1f}")
print(f"Probability of win: {simulation.prob_win:.0%}")
print(f"Probability of podium: {simulation.prob_podium:.0%}")
print(f"Best case: P{simulation.best_case}")
print(f"Worst case: P{simulation.worst_case}")

# Position probabilities
for position, prob in simulation.position_probabilities.items():
    print(f"  P{position}: {prob:.0%}")
```

---

## WebSocket

### Subscribe to Updates

```python
from rsw_client import RSWWebSocket

async def handle_updates():
    async with RSWWebSocket(base_url="ws://localhost:8000") as ws:
        # Subscribe to channels
        await ws.subscribe(["state", "strategy", "messages"])
        
        # Handle messages
        async for message in ws.messages():
            if message.type == "state_update":
                print(f"Lap {message.data.current_lap}")
            elif message.type == "strategy_update":
                print(f"Strategy: {message.data.recommendation}")
            elif message.type == "race_control":
                print(f"RC: {message.data.message}")
```

### Message Types

| Type | Description |
|------|-------------|
| `state_update` | Full state update |
| `driver_update` | Single driver update |
| `strategy_update` | Strategy recommendation |
| `race_control` | Race control message |
| `pit_stop` | Pit stop notification |
| `flag_change` | Flag status change |

### Reconnection

```python
async with RSWWebSocket(
    base_url="ws://localhost:8000",
    auto_reconnect=True,
    reconnect_delay=5.0,
    max_reconnect_attempts=10
) as ws:
    async for message in ws.messages():
        process(message)
```

---

## Error Handling

### Exception Classes

```python
from rsw_client.exceptions import (
    RSWError,           # Base exception
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    ServerError,
)
```

### Handling Errors

```python
from rsw_client.exceptions import NotFoundError, RateLimitError

try:
    strategy = await client.get_strategy(driver_number=99)
except NotFoundError:
    print("Driver not found")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except RSWError as e:
    print(f"API error: {e.code} - {e.message}")
```

### Retry Logic

```python
import asyncio
from rsw_client.exceptions import RateLimitError

async def get_with_retry(client, driver_number, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await client.get_strategy(driver_number)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(e.retry_after)
            else:
                raise
```

---

## Advanced Usage

### Custom HTTP Client

```python
import httpx

# Use custom httpx client
http_client = httpx.AsyncClient(
    timeout=60.0,
    limits=httpx.Limits(max_connections=100),
)

client = RSWClient(
    base_url="http://localhost:8000",
    http_client=http_client,
)
```

### Batch Requests

```python
async def get_all_strategies(client, driver_numbers):
    tasks = [
        client.get_strategy(driver_number=num)
        for num in driver_numbers
    ]
    return await asyncio.gather(*tasks)

strategies = await get_all_strategies(client, [1, 11, 44, 63])
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_session_sync(session_key: int):
    return asyncio.run(client.get_session(session_key))
```

### Data Export

```python
import pandas as pd

# Export to DataFrame
state = await client.get_state()

data = [
    {
        "number": d.driver_number,
        "position": d.position,
        "gap": d.gap_to_leader,
        "last_lap": d.last_lap_time,
        "tyre": d.compound,
        "age": d.tyre_age,
    }
    for d in state.drivers.values()
]

df = pd.DataFrame(data)
df.to_csv("race_state.csv", index=False)
```

---

## Complete Example

```python
"""
Full example: Monitor race and log strategy changes.
"""
import asyncio
from rsw_client import RSWClient, RSWWebSocket


async def main():
    client = RSWClient(base_url="http://localhost:8000")
    
    try:
        # Get initial state
        state = await client.get_state()
        print(f"Monitoring: {state.session_name}")
        print(f"Lap {state.current_lap}/{state.total_laps}")
        
        # Connect to WebSocket
        async with RSWWebSocket(base_url="ws://localhost:8000") as ws:
            await ws.subscribe(["state", "strategy"])
            
            async for message in ws.messages():
                if message.type == "state_update":
                    lap = message.data.current_lap
                    print(f"\n=== Lap {lap} ===")
                    
                elif message.type == "strategy_update":
                    driver = message.data.driver_number
                    rec = message.data.recommendation
                    print(f"Driver {driver}: {rec}")
                    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## API Reference

### Methods Summary

| Method | Description |
|--------|-------------|
| `get_sessions()` | List available sessions |
| `get_session(key)` | Get single session |
| `get_state()` | Get current race state |
| `get_driver(number)` | Get single driver state |
| `get_strategy(number)` | Get strategy recommendation |
| `simulate_strategy(...)` | Run Monte Carlo simulation |
| `start_replay(key)` | Start session replay |
| `control_replay(action)` | Control replay playback |
| `close()` | Close client connections |

---

## Next Steps

- [API Reference](API.md) — Full REST API documentation
- [WebSocket Guide](API.md#websocket-api) — Real-time integration
- [Examples Repository](https://github.com/your-org/rsw-examples) — More examples

---
**Next:** [[Deployment]]
