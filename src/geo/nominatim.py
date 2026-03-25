from __future__ import annotations

import asyncio
import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

LOGGER = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "GoogleMapsScraper/1.0 (educational project)"


@dataclass
class CityGeodata:
    display_name: str
    # (min_lat, max_lat, min_lon, max_lon)
    bbox: tuple
    polygon_geojson: Optional[dict]


async def fetch_city_geodata(city: str) -> CityGeodata:
    """Consulta Nominatim para obtener el bounding box y polígono GeoJSON de una ciudad."""
    params = urllib.parse.urlencode({
        "q": city,
        "format": "json",
        "polygon_geojson": "1",
        "limit": "1",
        "addressdetails": "0",
    })
    url = f"{NOMINATIM_URL}?{params}"
    LOGGER.debug("Nominatim: GET %s", url)

    def _fetch() -> list:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "es"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    loop = asyncio.get_event_loop()
    data: list = await loop.run_in_executor(None, _fetch)

    if not data:
        raise ValueError(
            f"Nominatim no encontró resultados para '{city}'. "
            "Prueba con un nombre más específico (ej: 'Madrid, España')."
        )

    result = data[0]
    bb = result["boundingbox"]  # [south, north, west, east] — todos strings
    bbox = (float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3]))

    geojson = result.get("geojson")
    LOGGER.info(
        "Nominatim → %s | bbox lat=[%.4f,%.4f] lon=[%.4f,%.4f]",
        result.get("display_name", city),
        bbox[0], bbox[1], bbox[2], bbox[3],
    )
    return CityGeodata(
        display_name=result.get("display_name", city),
        bbox=bbox,
        polygon_geojson=geojson,
    )
