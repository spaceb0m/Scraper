from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

LOGGER = logging.getLogger(__name__)


@dataclass
class Sector:
    lat: float
    lon: float
    zoom: int
    cell_deg: float = 0.01  # tamaño de la celda en grados; usado para subdivisión adaptativa


def build_sector_grid(
    bbox: tuple,
    cell_deg: float = 0.01,
    zoom: int = 14,
) -> list:
    """Divide el bounding box en una cuadrícula de sectores."""
    min_lat, max_lat, min_lon, max_lon = bbox
    sectors = []
    lat = min_lat + cell_deg / 2
    while lat <= max_lat:
        lon = min_lon + cell_deg / 2
        while lon <= max_lon:
            sectors.append(Sector(lat=round(lat, 6), lon=round(lon, 6), zoom=zoom, cell_deg=cell_deg))
            lon += cell_deg
        lat += cell_deg
    return sectors


def filter_by_polygon(sectors: list, geojson: Optional[dict]) -> list:
    """Filtra sectores cuyo centro queda fuera del polígono de la zona."""
    if not geojson:
        LOGGER.warning("Sin polígono GeoJSON — usando todos los sectores del bbox")
        return sectors
    try:
        from shapely.geometry import Point, shape  # type: ignore
        polygon = shape(geojson)
        filtered = [s for s in sectors if polygon.contains(Point(s.lon, s.lat))]
        LOGGER.info(
            "GeoFilter: %d/%d sectores dentro del polígono",
            len(filtered), len(sectors),
        )
        return filtered
    except ImportError:
        LOGGER.warning("shapely no instalado — sin filtro geográfico")
        return sectors
