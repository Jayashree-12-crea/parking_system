"""
haversine_utils.py  —  Nearest vacant parking spot from a fixed user entry point.

Exports:
    haversine(lat1, lon1, lat2, lon2) -> float   distance in metres
    nearest_vacant_spot(user_lat, user_lon, occupancy_list, spot_gps_map) -> dict | None
    load_spot_gps(path) -> dict   {spot_name: {"lat": ..., "lng": ...}}
"""

import math
import json


# ── Haversine formula ────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Return the great-circle distance in metres between two GPS points.
    At parking-lot scale (~100 m) this is equivalent to Euclidean distance,
    but stays correct if you ever expand to multi-lot scenarios.
    """
    R = 6_371_000  # Earth radius in metres

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi       = math.radians(lat2 - lat1)
    dlambda    = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)

    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Loader ───────────────────────────────────────────────────────────────────

def load_spot_gps(path: str = "data/spot_gps.json") -> dict:
    """
    Load spot_gps.json and return a dict keyed by spot name.

    Expected JSON format:
        [
          {"name": "S1", "lat": 52.01234, "lng": 4.35678},
          {"name": "S2", "lat": 52.01230, "lng": 4.35685},
          ...
        ]

    Returns:
        {"S1": {"lat": 52.01234, "lng": 4.35678}, ...}
    """
    with open(path) as f:
        data = json.load(f)
    return {entry["name"]: {"lat": entry["lat"], "lng": entry["lng"]}
            for entry in data}


# ── Main function ─────────────────────────────────────────────────────────────

def nearest_vacant_spot(
    user_lat: float,
    user_lon: float,
    occupancy_list: list,
    spot_gps_map: dict,
) -> dict | None:
    """
    Find the nearest VACANT spot to the user entry point.

    Args:
        user_lat      : fixed entry-point latitude
        user_lon      : fixed entry-point longitude
        occupancy_list: list of dicts from detect_and_annotate()
                        e.g. [{"name": "S1", "occupied": True, "coordinates": [...]}, ...]
        spot_gps_map  : dict from load_spot_gps()
                        e.g. {"S1": {"lat": ..., "lng": ...}, ...}

    Returns:
        {
            "name":        "S3",
            "distance_m":  14.2,          # metres, rounded to 1 dp
            "coordinates": [[x,y], ...],  # pixel polygon (for frame annotation)
            "lat":         52.01232,
            "lng":         4.35681,
        }
        or None if no vacant spots exist or no GPS data is loaded.
    """
    best      = None
    best_dist = float("inf")

    for spot in occupancy_list:
        if spot.get("occupied"):
            continue  # skip occupied spots

        name = spot["name"]
        gps  = spot_gps_map.get(name)
        if not gps:
            continue  # skip spots with no GPS mapping

        dist = haversine(user_lat, user_lon, gps["lat"], gps["lng"])

        if dist < best_dist:
            best_dist = dist
            best      = {
                "name":        name,
                "distance_m":  round(dist, 1),
                "coordinates": spot.get("coordinates", []),
                "lat":         gps["lat"],
                "lng":         gps["lng"],
            }

    return best