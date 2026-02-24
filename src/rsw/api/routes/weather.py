"""
Weather API Routes.

Provides real-time weather data for F1 circuits using OpenMeteo API.
New in v3.0.1
"""

from fastapi import APIRouter, HTTPException

from rsw.ingest.weather_client import WeatherClient, CIRCUIT_COORDINATES

router = APIRouter(prefix="/weather", tags=["weather"])

# Singleton client instance
_client = WeatherClient()


@router.get("/current/{circuit_key}")
async def get_current_weather(circuit_key: str):
    """
    Get current weather for a circuit.

    Args:
        circuit_key: Circuit identifier (e.g., "bahrain", "silverstone")

    Returns:
        Current weather data including temperature, humidity, wind, precipitation
    """
    if circuit_key.lower() not in CIRCUIT_COORDINATES:
        raise HTTPException(
            status_code=404,
            detail=f"Circuit '{circuit_key}' not found. Available: {list(CIRCUIT_COORDINATES.keys())}"
        )

    weather = await _client.get_current(circuit_key)

    if not weather:
        raise HTTPException(
            status_code=503,
            detail="Weather service temporarily unavailable"
        )

    return {
        "circuit": circuit_key,
        "timestamp": weather.timestamp.isoformat(),
        "temperature": weather.temperature,
        "humidity": weather.humidity,
        "precipitation": weather.precipitation,
        "precipitation_probability": weather.precipitation_probability,
        "wind_speed": weather.wind_speed,
        "cloud_cover": weather.cloud_cover,
        "rain_risk": weather.rain_risk,
        "is_wet": weather.is_wet,
    }


@router.get("/forecast/{circuit_key}")
async def get_weather_forecast(circuit_key: str, hours: int = 3):
    """
    Get weather forecast for a circuit.

    Args:
        circuit_key: Circuit identifier
        hours: Hours ahead to forecast (default 3)

    Returns:
        Forecast data with max rain probability
    """
    if circuit_key.lower() not in CIRCUIT_COORDINATES:
        raise HTTPException(
            status_code=404,
            detail=f"Circuit '{circuit_key}' not found"
        )

    forecast = await _client.get_forecast(circuit_key, hours=hours)

    if not forecast:
        raise HTTPException(
            status_code=503,
            detail="Weather service temporarily unavailable"
        )

    return {
        "circuit": circuit_key,
        "hours": hours,
        "max_rain_probability": forecast.max_rain_probability,
        "is_rain_expected": forecast.is_rain_expected,
        "data_points": [
            {
                "timestamp": dp.timestamp.isoformat(),
                "temperature": dp.temperature,
                "humidity": dp.humidity,
                "precipitation": dp.precipitation,
                "precipitation_probability": dp.precipitation_probability,
                "wind_speed": dp.wind_speed,
                "rain_risk": dp.rain_risk,
            }
            for dp in forecast.data_points
        ],
    }


@router.get("/circuits")
async def list_circuits():
    """List all available circuits with coordinates."""
    return {
        "circuits": [
            {"key": key, "latitude": coords[0], "longitude": coords[1]}
            for key, coords in CIRCUIT_COORDINATES.items()
        ]
    }
