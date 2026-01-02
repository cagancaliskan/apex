# Troubleshooting Guide

Solutions for common issues with the F1 Race Strategy Workbench.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Runtime Errors](#runtime-errors)
3. [API Errors](#api-errors)
4. [WebSocket Issues](#websocket-issues)
5. [Performance Issues](#performance-issues)
6. [Data Issues](#data-issues)
7. [Authentication Issues](#authentication-issues)
8. [Docker Issues](#docker-issues)

---

## Installation Issues

### Python Version Mismatch

**Error:**
```
ERROR: Package requires Python >=3.11
```

**Solution:**
```bash
# Check your Python version
python --version

# Install Python 3.11+ if needed
# macOS
brew install python@3.11

# Ubuntu
sudo apt install python3.11

# Create venv with specific version
python3.11 -m venv .venv
```

---

### Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'rsw'
```

**Solution:**
```bash
# Ensure PYTHONPATH includes src/
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Or install in development mode
pip install -e .
```

---

### Dependency Conflicts

**Error:**
```
ERROR: Cannot install X because requirements conflict
```

**Solution:**
```bash
# Create fresh virtual environment
rm -rf .venv
python -m venv .venv
source .venv/bin/activate

# Install with no cache
pip install --no-cache-dir -r requirements.txt
```

---

### pydantic-settings Missing

**Error:**
```
ModuleNotFoundError: No module named 'pydantic_settings'
```

**Solution:**
```bash
pip install pydantic-settings
```

---

### structlog Missing

**Error:**
```
ModuleNotFoundError: No module named 'structlog'
```

**Solution:**
```bash
pip install structlog
```

---

## Runtime Errors

### Port Already in Use

**Error:**
```
ERROR: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
python run.py --port 8001
```

---

### Import Error on Startup

**Error:**
```
ImportError: cannot import name 'X' from 'rsw.module'
```

**Solution:**
```bash
# Check for circular imports
python -c "from rsw.main import app"

# Verify all __init__.py exports
cat src/rsw/models/degradation/__init__.py
```

---

### Async Event Loop Error

**Error:**
```
RuntimeError: There is no current event loop in thread 'Thread-1'
```

**Solution:**
This typically occurs in tests. Ensure proper async context:

```python
import asyncio

# Use asyncio.run() for top-level calls
asyncio.run(async_function())

# Or in pytest, use the decorator
@pytest.mark.asyncio
async def test_something():
    ...
```

---

### Configuration Not Found

**Error:**
```
FileNotFoundError: Configuration file not found
```

**Solution:**
```bash
# Create .env file
cat > .env << EOF
RSW_ENV=development
RSW_PORT=8000
EOF

# Or set environment variables
export RSW_ENV=development
```

---

## API Errors

### 401 Authentication Required

**Error:**
```json
{"error": {"code": "AUTHENTICATION_REQUIRED"}}
```

**Solution:**
```bash
# Disable auth for development
export RSW_AUTH_ENABLED=false

# Or provide valid token
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/sessions
```

---

### 404 Session Not Found

**Error:**
```json
{"error": {"code": "SESSION_NOT_FOUND"}}
```

**Solution:**
- Verify session_key exists
- Check year range (2023+ only)
- Session may be from future (not yet available)

```bash
# List available sessions
curl http://localhost:8000/api/sessions?year=2024
```

---

### 422 Validation Error

**Error:**
```json
{"detail": [{"loc": ["query", "year"], "msg": "value is not a valid integer"}]}
```

**Solution:**
- Check parameter types
- Ensure required parameters are provided
- Verify parameter format

```bash
# Correct format
curl "http://localhost:8000/api/sessions?year=2024"

# Wrong format (will fail)
curl "http://localhost:8000/api/sessions?year=twenty"
```

---

### 429 Rate Limit Exceeded

**Error:**
```json
{"error": {"code": "RATE_LIMIT_EXCEEDED"}}
```

**Solution:**
- Wait for rate limit reset (check `Retry-After` header)
- Reduce request frequency
- Use caching for repeated requests

```bash
# Check rate limit headers
curl -I http://localhost:8000/api/sessions
```

---

### 500 Internal Server Error

**Error:**
```json
{"error": {"code": "INTERNAL_ERROR"}}
```

**Solution:**
```bash
# Check server logs
docker-compose logs app

# Or local logs
cat logs/rsw.log

# Enable debug mode for more info
export RSW_DEBUG=true
```

---

## WebSocket Issues

### Connection Refused

**Error:**
```
WebSocket connection to 'ws://localhost:8000/ws' failed
```

**Solution:**
- Verify server is running
- Check WebSocket endpoint URL
- Ensure CORS allows your origin

```javascript
// Correct WebSocket URL
const ws = new WebSocket('ws://localhost:8000/ws');

// For HTTPS, use WSS
const ws = new WebSocket('wss://api.example.com/ws');
```

---

### Connection Drops

**Error:**
```
WebSocket connection closed unexpectedly
```

**Solution:**
- Implement reconnection logic
- Check for proxy timeouts
- Increase ping/pong interval

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onclose = () => {
  console.log('Connection closed, reconnecting...');
  setTimeout(() => connect(), 5000);
};
```

---

### No Messages Received

**Error:**
No data received after connecting.

**Solution:**
- Verify subscription was sent
- Check channel names are correct
- Ensure session is active

```javascript
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['state', 'strategy']
  }));
};
```

---

## Performance Issues

### Slow API Responses

**Cause:** Database queries or external API calls.

**Solution:**
```bash
# Enable Redis caching
export REDIS_URL=redis://localhost:6379/0

# Increase workers
uvicorn rsw.main:app --workers 4
```

---

### High Memory Usage

**Cause:** Large state objects or memory leaks.

**Solution:**
```bash
# Monitor memory
docker stats

# Reduce cache size in config
export RSW_CACHE_TTL=300

# Restart service periodically
docker-compose restart app
```

---

### Slow WebSocket Updates

**Cause:** Processing bottleneck or network latency.

**Solution:**
- Reduce update frequency
- Compress WebSocket messages
- Use message batching

---

## Data Issues

### Empty Session List

**Cause:** OpenF1 API not responding or wrong parameters.

**Solution:**
```bash
# Test OpenF1 directly
curl https://api.openf1.org/v1/sessions?year=2024

# Check API status
curl http://localhost:8000/health
```

---

### Stale Data

**Cause:** Cache not refreshing.

**Solution:**
```bash
# Clear Redis cache
redis-cli FLUSHDB

# Reduce cache TTL
export RSW_CACHE_TTL=60
```

---

### Missing Driver Data

**Cause:** Session not fully loaded or data unavailable.

**Solution:**
- Wait for session to fully load
- Check if session is a practice (less data)
- Verify driver number is correct

---

### Degradation Shows N/A

**Cause:** Insufficient data for calculation.

**Solution:**
- Need at least 5 clean laps
- Driver may have just pitted
- Session just started

---

## Authentication Issues

### Invalid Token

**Error:**
```json
{"error": {"code": "INVALID_TOKEN"}}
```

**Solution:**
- Token may be expired (get new token)
- Token may be malformed
- Wrong JWT secret configured

---

### JWT Secret Not Set

**Error:**
```
JWT_SECRET environment variable not set
```

**Solution:**
```bash
# Generate secure secret
openssl rand -hex 32

# Set in environment
export JWT_SECRET="your-generated-secret"
```

---

## Docker Issues

### Container Won't Start

**Error:**
```
Container exited with code 1
```

**Solution:**
```bash
# Check logs
docker-compose logs app

# Rebuild image
docker-compose build --no-cache app

# Remove old containers
docker-compose down -v
docker-compose up
```

---

### Database Connection Failed

**Error:**
```
could not connect to server: Connection refused
```

**Solution:**
```bash
# Ensure database is running
docker-compose ps

# Wait for database to be ready
docker-compose up -d db
sleep 10
docker-compose up app
```

---

### Volume Permission Denied

**Error:**
```
Permission denied: '/data'
```

**Solution:**
```bash
# Fix permissions
sudo chown -R $(id -u):$(id -g) ./data

# Or in docker-compose.yml
volumes:
  - ./data:/data:rw
```

---

## Getting More Help

### Collect Debug Information

```bash
# System info
python --version
pip list
uname -a

# Application logs
cat logs/rsw.log | tail -100

# Docker logs
docker-compose logs --tail=100
```

### Report an Issue

Include in your bug report:
1. Python version
2. Operating system
3. Error message (full traceback)
4. Steps to reproduce
5. Configuration (without secrets)

File issues at: https://github.com/your-org/rsw/issues

---

## Quick Fixes Checklist

- [ ] Virtual environment activated?
- [ ] PYTHONPATH includes `src/`?
- [ ] Dependencies installed?
- [ ] Environment variables set?
- [ ] Correct Python version (3.11+)?
- [ ] Port not in use?
- [ ] Network connectivity?
- [ ] Database running (if required)?

---
**Next:** [[Contributing]]
