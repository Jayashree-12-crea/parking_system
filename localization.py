import math

# ── Parking Spot GPS Coordinates ───────────────────────
PARKING_SPOTS = {
    "P1" : {"lat": 17.4450, "lon": 78.3489},
    "P2" : {"lat": 17.4451, "lon": 78.3490},
    "P3" : {"lat": 17.4452, "lon": 78.3491},
    "P4" : {"lat": 17.4453, "lon": 78.3492},
    "P5" : {"lat": 17.4454, "lon": 78.3493},
    "P6" : {"lat": 17.4455, "lon": 78.3494},
    "P7" : {"lat": 17.4456, "lon": 78.3495},
    "P8" : {"lat": 17.4457, "lon": 78.3496},
    "P9" : {"lat": 17.4458, "lon": 78.3497},
    "P10": {"lat": 17.4459, "lon": 78.3498},
    "P11": {"lat": 17.4460, "lon": 78.3499},
    "P12": {"lat": 17.4461, "lon": 78.3500},
    "P13": {"lat": 17.4462, "lon": 78.3501},
    "P14": {"lat": 17.4463, "lon": 78.3502},
    "P15": {"lat": 17.4464, "lon": 78.3503},
}

# ── User Location (parking lot entry point) ─────────────
USER_LOCATION = {
    "lat": 17.4448,
    "lon": 78.3488
}


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate real-world distance between two GPS points.
    Returns distance in meters using Haversine formula.
    """
    R       = 6371000
    phi1    = math.radians(lat1)
    phi2    = math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) *
         math.sin(dlambda / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def run_localization(vacant_spots):
    """
    Find nearest vacant spot to user.
    Returns full result with distances for proof.
    """
    # ── Terminal Report ──────────────────────────────────
    print("\n╔══════════════════════════════════════════════╗")
    print("║         LOCALIZATION MODULE - PROOF          ║")
    print("╠══════════════════════════════════════════════╣")
    print(f"║  User Entry Point                            ║")
    print(f"║  Lat: {USER_LOCATION['lat']}  "
          f"Lon: {USER_LOCATION['lon']}        ║")
    print("╠══════════════════════════════════════════════╣")
    print(f"║  Vacant Spots Detected: {str(vacant_spots):<22}║")
    print("╠══════════════════════════════════════════════╣")

    if not vacant_spots:
        print("║  ❌ No vacant spots available!               ║")
        print("╚══════════════════════════════════════════════╝")
        return None

    # Calculate distances
    distances = []
    for name in vacant_spots:
        if name not in PARKING_SPOTS:
            continue
        spot = PARKING_SPOTS[name]
        dist = haversine_distance(
            USER_LOCATION["lat"], USER_LOCATION["lon"],
            spot["lat"],          spot["lon"]
        )
        distances.append({
            "name": name,
            "dist": round(dist, 2),
            "lat" : spot["lat"],
            "lon" : spot["lon"]
        })

    # Sort nearest first
    distances.sort(key=lambda x: x["dist"])

    print("║  Spot │ GPS Coordinates          │ Distance   ║")
    print("║  ─────┼──────────────────────────┼─────────── ║")

    for i, s in enumerate(distances):
        tag = "⭐" if i == 0 else "  "
        print(f"║  {tag}{s['name']:<3} │ "
              f"{s['lat']},{s['lon']}  │ "
              f"{s['dist']:>6.1f} m  ║")

    nearest = distances[0]
    print("╠══════════════════════════════════════════════╣")
    print(f"║  ✅ RECOMMENDED : {nearest['name']:<4}  "
          f"({nearest['dist']:.1f}m from entry)       ║")
    print("╚══════════════════════════════════════════════╝")

    return {
        "recommended_spot" : nearest["name"],
        "distance_meters"  : nearest["dist"],
        "coordinates"      : {"lat": nearest["lat"],
                               "lon": nearest["lon"]},
        "all_vacant_sorted": distances
    }


if __name__ == "__main__":
    test_vacant = ["P3", "P6", "P9", "P12"]
    result = run_localization(test_vacant)
    if result:
        print(f"\n  👉 Navigate to : {result['recommended_spot']}")
        print(f"  📍 Coordinates : "
              f"{result['coordinates']['lat']}, "
              f"{result['coordinates']['lon']}")