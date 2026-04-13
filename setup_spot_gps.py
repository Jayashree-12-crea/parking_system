"""
setup_spot_gps.py  —  One-time helper to build data/spot_gps.json

Run AFTER define_spots.py (so parking_spots.json already exists).

It reads the spot names from parking_spots.json and prompts you to
type in the GPS coordinates for each one.

HOW TO GET GPS COORDS FOR EACH SPOT:
  Option A — Google Maps on your phone:
    1. Stand at the centre of the parking spot.
    2. Open Google Maps → long-press your location.
    3. Copy the coordinates shown at the top (e.g. 52.01234, 4.35678).

  Option B — IP Webcam geolocation (if your phone returns GPS):
    http://<phone-ip>:8080/sensors.json  → look for "gps" key.

  Option C — Google Maps desktop:
    1. Open satellite view of your parking lot.
    2. Right-click the centre of each spot → "What's here?".
    3. Copy the lat/lng from the popup.

Usage:
    python setup_spot_gps.py
"""

import json
import os

SPOTS_JSON   = "data/parking_spots.json"
GPS_OUT_JSON = "data/spot_gps.json"


def main():
    if not os.path.exists(SPOTS_JSON):
        print(f"❌  {SPOTS_JSON} not found.")
        print("    Run define_spots.py first to define your parking spots.")
        return

    with open(SPOTS_JSON) as f:
        spots = json.load(f)

    print(f"\n📍  Found {len(spots)} spots in {SPOTS_JSON}")
    print("    For each spot, enter the GPS coordinates of its centre.\n")

    # Load existing file so you can re-run without re-entering everything
    existing = {}
    if os.path.exists(GPS_OUT_JSON):
        with open(GPS_OUT_JSON) as f:
            for entry in json.load(f):
                existing[entry["name"]] = entry
        print(f"    (Existing {GPS_OUT_JSON} found — press ENTER to keep current value)\n")

    output = []
    for spot in spots:
        name = spot["name"]
        prev = existing.get(name)
        hint = f"  [{prev['lat']}, {prev['lng']}]" if prev else ""

        while True:
            raw = input(f"  {name}{hint}  →  lat, lng: ").strip()

            if raw == "" and prev:
                output.append(prev)
                print(f"    ✅  Kept {name}: {prev['lat']}, {prev['lng']}")
                break

            try:
                parts = raw.replace(",", " ").split()
                lat, lng = float(parts[0]), float(parts[1])
                output.append({"name": name, "lat": lat, "lng": lng})
                print(f"    ✅  Saved {name}: {lat}, {lng}")
                break
            except (ValueError, IndexError):
                print("    ⚠️  Invalid format. Enter as:  52.01234  4.35678")

    os.makedirs("data", exist_ok=True)
    with open(GPS_OUT_JSON, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅  Saved {len(output)} GPS entries → {GPS_OUT_JSON}")
    print("    You can now run:  python app.py\n")


if __name__ == "__main__":
    main()