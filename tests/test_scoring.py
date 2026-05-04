from __future__ import annotations

import pytest

from src.analyzer.scoring import (
    classify_avatar,
    coords_from_maps_url,
    count_stores_by_brand,
    haversine_km,
    load_avatares,
    load_eci_locations,
    load_weights,
    nearest_eci_distance_km,
    normalize_brand_key,
    num_tiendas_for,
    score_distancia_eci,
    score_madurez_digital,
    score_num_tiendas,
    score_poblacion,
    compute_score,
    tramo_for_score,
)

# ─── Geometría ──────────────────────────────────────────────────────────

def test_haversine_madrid_barcelona():
    d = haversine_km(40.4168, -3.7038, 41.3851, 2.1734)
    assert 500 < d < 510


def test_coords_from_maps_url_valid():
    url = "https://www.google.com/maps/place/Foo/@43.21,-8.69,17z/data=abc"
    lat, lon = coords_from_maps_url(url)
    assert lat == pytest.approx(43.21)
    assert lon == pytest.approx(-8.69)


def test_coords_from_maps_url_missing():
    assert coords_from_maps_url("https://example.com/foo") == (None, None)
    assert coords_from_maps_url("") == (None, None)


def test_coords_from_maps_url_data_format():
    """Formato real de Google Maps tras click en place: data=!...!3dLAT!4dLON!..."""
    url = "https://www.google.com/maps/place/Foo/data=!4m7!3m6!1s0x123!8m2!3d42.234976!4d-8.716834!16s/abc"
    lat, lon = coords_from_maps_url(url)
    assert lat == pytest.approx(42.234976)
    assert lon == pytest.approx(-8.716834)


def test_nearest_eci_picks_closest():
    eci = [
        {"ciudad": "Vigo", "lat": 42.2333, "lon": -8.7163},
        {"ciudad": "A Coruña", "lat": 43.3499, "lon": -8.4123},
    ]
    # Carballo (~27km de A Coruña por haversine, ~110km de Vigo)
    d, name = nearest_eci_distance_km(43.21, -8.69, eci)
    assert name == "A Coruña"
    assert 20 < d < 35


# ─── Configs reales ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def real_weights():
    return load_weights()


@pytest.fixture(scope="module")
def real_avatars():
    return load_avatares()


@pytest.fixture(scope="module")
def real_eci():
    return load_eci_locations()


def test_real_configs_load_smoke(real_weights, real_avatars, real_eci):
    assert "criterios" in real_weights
    assert len(real_avatars) >= 3
    assert len(real_eci) >= 30


# ─── Scoring por criterio (con configs reales) ──────────────────────────

def test_score_distancia_eci_optimo(real_weights):
    pts, etiqueta = score_distancia_eci(60, real_weights)
    assert pts == 30
    assert "óptimo" in etiqueta


def test_score_distancia_eci_sombra(real_weights):
    pts, _ = score_distancia_eci(15, real_weights)
    assert pts == 5


def test_score_distancia_eci_aislado(real_weights):
    pts, _ = score_distancia_eci(150, real_weights)
    assert pts == 12


def test_score_poblacion_ideal(real_weights):
    pts, etiqueta = score_poblacion(25000, real_weights)
    assert pts == 20
    assert "ideal" in etiqueta


def test_score_poblacion_rural(real_weights):
    pts, _ = score_poblacion(3000, real_weights)
    assert pts == 5


def test_score_poblacion_urbano(real_weights):
    pts, _ = score_poblacion(300000, real_weights)
    assert pts == 5


def test_score_num_tiendas(real_weights):
    assert score_num_tiendas(4, real_weights)[0] == 30
    assert score_num_tiendas(2, real_weights)[0] == 18
    assert score_num_tiendas(1, real_weights)[0] == 5
    assert score_num_tiendas(10, real_weights)[0] == 12


def test_score_madurez(real_weights):
    assert score_madurez_digital("ecommerce_funcional", real_weights)[0] == 20
    assert score_madurez_digital("solo_redes_sociales", real_weights)[0] == 10
    assert score_madurez_digital("sin_presencia", real_weights)[0] == 0


def test_tramo_for_score(real_weights):
    assert tramo_for_score(80, real_weights)[0] == "P1"
    assert tramo_for_score(60, real_weights)[0] == "P2"
    assert tramo_for_score(40, real_weights)[0] == "P3"
    assert tramo_for_score(10, real_weights)[0] == "P4"


# ─── Avatar matching ────────────────────────────────────────────────────

def test_classify_avatar_claro_avatar1(real_avatars):
    ctx = {
        "poblacion": 25000,
        "distancia_eci_km": 60,
        "num_tiendas": 4,
        "ecommerce": True,
    }
    label, av_id, level = classify_avatar(ctx, real_avatars)
    assert av_id == 1
    assert level == "claro"
    assert "Señorío" in label


def test_classify_avatar_partial(real_avatars):
    # Pob ✓, dist ✗, tiendas ✓, ecommerce ✗ → 2/4 → parcial
    ctx = {
        "poblacion": 25000,
        "distancia_eci_km": 5,
        "num_tiendas": 4,
        "ecommerce": False,
    }
    label, av_id, level = classify_avatar(ctx, real_avatars)
    assert level == "parcial"
    assert "(parcial)" in label


def test_classify_avatar_no_match(real_avatars):
    ctx = {
        "poblacion": 500,
        "distancia_eci_km": 200,
        "num_tiendas": 50,
        "ecommerce": False,
    }
    label, av_id, level = classify_avatar(ctx, real_avatars)
    assert level == "ninguno"
    assert av_id is None
    assert label == "—"


# ─── Conteo de tiendas ──────────────────────────────────────────────────

def test_normalize_brand_key():
    assert normalize_brand_key("Lolitamoda - Vigo (centro)") == "lolitamoda vigo"
    assert normalize_brand_key("Zapaterías 54") == "zapaterías"


def test_count_stores_groups_by_brand_signature():
    rows = [
        {"nombre": "Lolitamoda Noia"},
        {"nombre": "Lolitamoda Boiro"},
        {"nombre": "Lolitamoda Ribeira"},
        {"nombre": "Casais Noia"},
        {"nombre": "Casais Ribeira"},
        {"nombre": "Único Concept Store"},
    ]
    counts = count_stores_by_brand(rows)
    assert counts["lolitamoda"] == 3
    assert counts["casais"] == 2
    assert counts["único"] == 1


def test_num_tiendas_for_returns_count():
    rows = [{"nombre": "Lolitamoda A"}, {"nombre": "Lolitamoda B"}, {"nombre": "Lolitamoda C"}]
    counts = count_stores_by_brand(rows)
    assert num_tiendas_for("Lolitamoda Otro Local", counts) == 3


def test_num_tiendas_for_unknown_returns_one():
    assert num_tiendas_for("Marca Desconocida XYZ", {}) == 1


# ─── Cálculo completo ───────────────────────────────────────────────────

def test_compute_score_microcadena_galicia(real_weights, real_avatars, real_eci):
    """Negocio en Carballo (~27km de ECI A Coruña, pob 31k), 4 tiendas, ecommerce funcional."""
    ctx = {
        "lat": 43.21, "lon": -8.69,
        "poblacion": 31000,
        "num_tiendas": 4,
        "madurez": "ecommerce_funcional",
    }
    result = compute_score(ctx, eci_locations=real_eci, avatares=real_avatars, weights=real_weights)
    # Distancia ~27km → sombra ECI = 5pts. Pob 31k → ideal = 20. Tiendas 4 → 30.
    # Madurez ecommerce → 20. Total = 5 + 20 + 30 + 20 = 75 → P1 (avatar NO suma).
    assert result["puntuacion_total"] == 75
    assert result["prioridad"] == "P1"
    # Avatar 1 (Señorío Comarcal): pob ✓ dist ✗ tiendas ✓ ecommerce ✓ = 3/4 → parcial.
    assert result["avatar_nivel"] == "parcial"
    assert "Señorío" in result["avatar"]


def test_compute_score_p1_full_match(real_weights, real_avatars, real_eci):
    """Caso ideal Avatar 1: 60km de ECI, pob 25k, 4 tiendas, ecommerce → 30+20+30+20 = 100."""
    # Punto a ~60km al norte de Madrid (Castellana 40.447, -3.690): lat ~40.985
    ctx = {
        "lat": 40.985, "lon": -3.690,
        "poblacion": 25000,
        "num_tiendas": 4,
        "madurez": "ecommerce_funcional",
    }
    result = compute_score(ctx, eci_locations=real_eci, avatares=real_avatars, weights=real_weights)
    assert result["puntuacion_total"] == 100
    assert result["prioridad"] == "P1"
    assert result["avatar_nivel"] == "claro"


def test_compute_score_avatar_does_not_add_points(real_weights, real_avatars, real_eci):
    """El avatar NO debe sumar al total — comparar igual contexto con/sin avatares."""
    ctx_a = {"lat": 40.985, "lon": -3.690, "poblacion": 25000, "num_tiendas": 4, "madurez": "ecommerce_funcional"}
    ctx_b = {"lat": 40.985, "lon": -3.690, "poblacion": 25000, "num_tiendas": 4, "madurez": "ecommerce_funcional"}
    r1 = compute_score(ctx_a, eci_locations=real_eci, avatares=real_avatars, weights=real_weights)
    r2 = compute_score(ctx_b, eci_locations=real_eci, avatares=[], weights=real_weights)
    assert r1["puntuacion_total"] == r2["puntuacion_total"]


def test_compute_score_no_coords(real_weights, real_avatars, real_eci):
    """Sin lat/lon → distancia=0pts."""
    ctx = {
        "lat": None, "lon": None,
        "poblacion": 25000,
        "num_tiendas": 4,
        "madurez": "ecommerce_funcional",
    }
    result = compute_score(ctx, eci_locations=real_eci, avatares=real_avatars, weights=real_weights)
    assert result["breakdown"]["distancia_eci"]["puntos"] == 0
    assert "sin coordenadas" in result["justificacion"]
