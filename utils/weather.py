"""
weather.py
----------
Fetches 7-day weather forecast from OpenWeatherMap One Call API 3.0.
Free tier: 1000 calls/day — sufficient for hackathon demos.

Sign up: https://openweathermap.org/api
Key goes in .streamlit/secrets.toml as OPENWEATHER_KEY = "..."
"""

import requests
import streamlit as st
from datetime import datetime, timedelta
import random

# Weather icon mapping (OWM icon code → emoji)
OWM_ICONS = {
    "01": "☀️",   # clear sky
    "02": "🌤️",   # few clouds
    "03": "⛅",   # scattered clouds
    "04": "☁️",   # broken / overcast clouds
    "09": "🌧️",   # shower rain
    "10": "🌦️",   # rain
    "11": "⛈️",   # thunderstorm
    "13": "❄️",   # snow
    "50": "🌫️",   # mist
}


def _icon_emoji(icon_code: str) -> str:
    prefix = icon_code[:2] if icon_code else "01"
    return OWM_ICONS.get(prefix, "🌡️")


def _fallback_forecast(lat: float, lon: float, scene_date: str = "Latest Available (Live)") -> dict:
    """
    Deterministic synthetic forecast when no API key is provided.
    Seeded from coordinates and scene_date so selecting different months gives month-accurate weather.
    """
    seed_str = f"{lat:.4f}_{lon:.4f}_{scene_date}"
    rng = random.Random(int(abs(hash(seed_str))))
    daily = []
    today = datetime.now()
    
    date_lower = scene_date.lower()
    # Seasonal climate parameters based on month
    if any(m in date_lower for m in ["july", "august", "september", "october"]):
        temp_min, temp_max = 26.0, 31.0
        rain_min, rain_max = 12.0, 45.0  # Monsoon rain
        icons_pool = ["🌧️", "🌦️", "⛈️", "☁️"]
    elif any(m in date_lower for m in ["march", "april", "may"]):
        temp_min, temp_max = 34.0, 42.0
        rain_min, rain_max = 0.0, 3.0    # Hot dry summer
        icons_pool = ["☀️", "🌤️", "☀️"]
    else:
        temp_min, temp_max = 24.0, 32.0
        rain_min, rain_max = 1.0, 15.0   # Winter / Rabi season
        icons_pool = ["☀️", "🌤️", "⛅"]

    for i in range(7):
        d     = today + timedelta(days=i)
        rain  = rng.uniform(rain_min, rain_max)
        temp  = rng.uniform(temp_min, temp_max)
        humid = rng.uniform(45, 85)
        daily.append({
            "date":  d.strftime("%b %d"),
            "temp":  round(temp, 1),
            "rain":  round(rain, 1),
            "humid": round(humid, 1),
            "icon":  rng.choice(icons_pool),
        })
    total_rain = sum(d["rain"] for d in daily[:2])
    return {
        "daily":          daily,
        "rain_next_48h":  round(total_rain, 1),
        "avg_temp":       round(sum(d["temp"] for d in daily) / 7, 1),
        "source":         f"Seasonal Climate Model ({scene_date})" if scene_date != "Latest Available (Live)" else "Synthetic fallback",
    }


def get_weather_forecast(lat: float, lon: float, scene_date: str = "Latest Available (Live)") -> dict:
    """
    Returns 7-day daily forecast dict.

    Falls back to synthetic data if OPENWEATHER_KEY is absent.
    """
    api_key = st.secrets.get("OPENWEATHER_KEY", "")

    if not api_key:
        return _fallback_forecast(lat, lon, scene_date)

    try:
        # One Call API 3.0
        url = (
            f"https://api.openweathermap.org/data/3.0/onecall"
            f"?lat={lat}&lon={lon}"
            f"&exclude=current,minutely,hourly,alerts"
            f"&units=metric"
            f"&appid={api_key}"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        daily = []
        for day in data.get("daily", [])[:7]:
            dt   = datetime.fromtimestamp(day["dt"])
            rain = day.get("rain", 0)
            daily.append({
                "date":  dt.strftime("%b %d"),
                "temp":  round(day["temp"]["day"], 1),
                "rain":  round(rain, 1),
                "humid": day.get("humidity", 60),
                "icon":  _icon_emoji(day["weather"][0]["icon"]),
            })

        rain_48h = sum(d["rain"] for d in daily[:2])
        return {
            "daily":         daily,
            "rain_next_48h": round(rain_48h, 1),
            "avg_temp":      round(sum(d["temp"] for d in daily) / max(len(daily), 1), 1),
            "source":        "OpenWeatherMap One Call 3.0",
        }

    except Exception as e:
        st.warning(f"⚠️ Weather API error: {e}. Using fallback data.")
        return _fallback_forecast(lat, lon)
