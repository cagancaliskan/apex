"""
Weather API Client.

Integrates with OpenMeteo free weather API for race weather data.
No API key required.

Design: KISS - Simple HTTP client with caching.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx


# F1 Circuit coordinates
CIRCUIT_COORDINATES: dict[str, tuple[float, float]] = {
    "bahrain": (26.0325, 50.5106),
    "jeddah": (21.6319, 39.1044),
    "albert_park": (-37.8497, 144.9680),
    "suzuka": (34.8431, 136.5411),
    "shanghai": (31.3389, 121.2198),
    "miami": (25.9581, -80.2389),
    "imola": (44.3439, 11.7167),
    "monaco": (43.7347, 7.4206),
    "montreal": (45.5017, -73.5673),
    "barcelona": (41.5700, 2.2611),
    "spielberg": (47.2197, 14.7647),
    "silverstone": (52.0786, -1.0169),
    "hungaroring": (47.5789, 19.2486),
    "spa": (50.4372, 5.9714),
    "zandvoort": (52.3889, 4.5408),
    "monza": (45.6206, 9.2811),
    "baku": (40.3725, 49.8533),
    "singapore": (1.2914, 103.8644),
    "cota": (30.1328, -97.6411),
    "mexico": (19.4042, -99.0907),
    "interlagos": (-23.7014, -46.6969),
    "las_vegas": (36.1146, -115.1728),
    "lusail": (25.4899, 51.4542),
    "yas_marina": (24.4672, 54.6031),
}


@dataclass
class WeatherData:
    """Weather data at a point in time."""

    timestamp: datetime
    temperature: float  # Celsius
    humidity: float  # Percentage
    precipitation: float  # mm
    precipitation_probability: float  # 0-100
    wind_speed: float  # km/h
    cloud_cover: float  # Percentage

    @property
    def rain_risk(self) -> str:
        """Human-readable rain risk level."""
        if self.precipitation_probability >= 70:
            return "HIGH"
        elif self.precipitation_probability >= 40:
            return "MEDIUM"
        elif self.precipitation_probability >= 20:
            return "LOW"
        return "NONE"

    @property
    def is_wet(self) -> bool:
        """Current conditions are wet."""
        return self.precipitation > 0.1


@dataclass
class WeatherForecast:
    """Weather forecast for a time range."""

    circuit_key: str
    data_points: list[WeatherData]

    @property
    def max_rain_probability(self) -> float:
        """Maximum rain probability in forecast."""
        if not self.data_points:
            return 0.0
        return max(d.precipitation_probability for d in self.data_points)

    @property
    def is_rain_expected(self) -> bool:
        """Rain is likely during this period."""
        return self.max_rain_probability >= 50


class WeatherClient:
    """
    Client for OpenMeteo weather API.

    Free API, no key required.
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._cache: dict[str, tuple[datetime, WeatherForecast]] = {}
        self._cache_ttl = 300  # 5 minutes

    def _get_coords(self, circuit_key: str) -> tuple[float, float] | None:
        """Get coordinates for a circuit."""
        return CIRCUIT_COORDINATES.get(circuit_key.lower())

    async def get_current(self, circuit_key: str) -> WeatherData | None:
        """
        Get current weather for a circuit.

        Args:
            circuit_key: Circuit identifier (e.g., "bahrain")

        Returns:
            WeatherData or None if unavailable
        """
        coords = self._get_coords(circuit_key)
        if not coords:
            return None

        lat, lon = coords

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,cloud_cover",
            "timezone": "auto",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            current = data.get("current", {})

            return WeatherData(
                timestamp=datetime.now(),
                temperature=current.get("temperature_2m", 25.0),
                humidity=current.get("relative_humidity_2m", 50.0),
                precipitation=current.get("precipitation", 0.0),
                precipitation_probability=0.0,  # Current doesn't have probability
                wind_speed=current.get("wind_speed_10m", 10.0),
                cloud_cover=current.get("cloud_cover", 0.0),
            )

        except (httpx.HTTPError, KeyError, TypeError):
            return None

    async def get_forecast(
        self,
        circuit_key: str,
        hours: int = 3,
    ) -> WeatherForecast | None:
        """
        Get weather forecast for a circuit.

        Args:
            circuit_key: Circuit identifier
            hours: Hours ahead to forecast

        Returns:
            WeatherForecast or None if unavailable
        """
        # Check cache
        cache_key = f"{circuit_key}_{hours}"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if (datetime.now() - cached_time).seconds < self._cache_ttl:
                return cached_data

        coords = self._get_coords(circuit_key)
        if not coords:
            return None

        lat, lon = coords

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,wind_speed_10m,cloud_cover",
            "forecast_hours": hours,
            "timezone": "auto",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            humidity = hourly.get("relative_humidity_2m", [])
            precip = hourly.get("precipitation", [])
            precip_prob = hourly.get("precipitation_probability", [])
            wind = hourly.get("wind_speed_10m", [])
            cloud = hourly.get("cloud_cover", [])

            data_points = []
            for i in range(min(len(times), hours)):
                data_points.append(
                    WeatherData(
                        timestamp=datetime.fromisoformat(times[i]) if i < len(times) else datetime.now(),
                        temperature=temps[i] if i < len(temps) else 25.0,
                        humidity=humidity[i] if i < len(humidity) else 50.0,
                        precipitation=precip[i] if i < len(precip) else 0.0,
                        precipitation_probability=precip_prob[i] if i < len(precip_prob) else 0.0,
                        wind_speed=wind[i] if i < len(wind) else 10.0,
                        cloud_cover=cloud[i] if i < len(cloud) else 0.0,
                    )
                )

            forecast = WeatherForecast(
                circuit_key=circuit_key,
                data_points=data_points,
            )

            # Cache result
            self._cache[cache_key] = (datetime.now(), forecast)

            return forecast

        except (httpx.HTTPError, KeyError, TypeError):
            return None


# Synchronous wrapper for non-async contexts
def get_weather_sync(circuit_key: str) -> WeatherData | None:
    """Synchronous wrapper for current weather."""
    try:
        return asyncio.run(WeatherClient().get_current(circuit_key))
    except Exception:
        return None
