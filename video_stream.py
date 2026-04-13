import cv2
import json
import numpy as np
import threading
from ultralytics import YOLO
from utils_parking import calculate_iou
from haversine_utils import haversine, load_spot_gps, nearest_vacant_spot
from pymongo import MongoClient
from datetime import datetime

# ══════════════════════════════════════════════════════════
#  ✅ CHANGE THIS to your phone's IP address
# ══════════════════════════════════════════════════════════
PHONE_STREAM_URL = "http://10.138.4.71:8080/video"     # ← CHANGE THIS IP

# ══════════════════════════════════════════════════════════
#  ✅ CHANGE THIS to your parking lot entrance GPS coords
#     (stand at the entrance gate, open Google Maps,
#      long-press your location → copy the coordinates)
# ══════════════════════════════════════════════════════════
USER_ENTRY_LAT = 52.01220   # ← CHANGE THIS
USER_ENTRY_LNG = 4.35660    # ← CHANGE THIS

SPOTS_JSON       = "data/parking_spots.json"
SPOT_GPS_JSON    = "data/spot_gps.json"
IOU_THRESHOLD    = 0.20
CONF_THRESHOLD   = 0.25
VEHICLE_CLASSES  = {2, 5, 7}   # YOLO: car=2, bus=5, truck=7
DB_SAVE_EVERY_N  = 30          # Save to MongoDB every 30 frames
# ─────────────────────────────────────────────────────────

# Shared state (thread-safe) — written by stream thread, read by Flask
latest_frame  = None
latest_status = {
    "total": 0, "vacant": 0, "occupied": 0,
    "spots": [], "nearest": None
}
_lock = threading.Lock()

# Load GPS map once at startup (graceful if file missing)
try:
    _spot_gps_map = load_spot_gps(SPOT_GPS_JSON)
    print(f"📍  GPS map loaded: {len(_spot_gps_map)} spots")
except FileNotFoundError:
    _spot_gps_map = {}
    print(f"⚠️  {SPOT_GPS_JSON} not found — nearest-spot feature disabled.")
    print(f"    Create data/spot_gps.json with lat/lng for each spot name.")


def load_spots():
    with open(SPOTS_JSON) as f:
        return json.load(f)


def save_to_mongodb(results):
    try:
        client = MongoClient("mongodb://localhost:27017/")
        col = client["parking_system"]["parking_status"]
        doc = {
            "timestamp":      datetime.now(),
            "total_spots":    len(results),
            "vacant_count":   sum(1 for r in results if not r["occupied"]),
            "occupied_count": sum(1 for r in results if r["occupied"]),
            "spots": [{"name": r["name"], "occupied": r["occupied"]} for r in results]
        }
        col.delete_many({})
        col.insert_one(doc)
    except Exception as e:
        print(f"⚠️  MongoDB Error: {e}")


def detect_and_annotate(frame, model, spots):
    """
    Run YOLO on one frame, check spot occupancy, draw coloured overlays.
    Nearest vacant spot gets a distinct CYAN highlight + distance label.
    """
    yolo_results = model(frame, conf=CONF_THRESHOLD, verbose=False, imgsz=640)

    vehicles = []
    for box in yolo_results[0].boxes:
        if int(box.cls[0]) in VEHICLE_CLASSES:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            vehicles.append({"bbox": [x1, y1, x2, y2]})

    occupancy      = []
    vacant_count   = 0
    occupied_count = 0

    for spot in spots:
        polygon  = spot["coordinates"]
        occupied = any(
            calculate_iou(v["bbox"], polygon) >= IOU_THRESHOLD
            for v in vehicles
        )
        occupancy.append({
            "name":        spot["name"],
            "coordinates": polygon,
            "occupied":    occupied
        })
        if occupied:
            occupied_count += 1
        else:
            vacant_count += 1

    # ── Find nearest vacant spot ─────────────────────────
    nearest = nearest_vacant_spot(
        USER_ENTRY_LAT, USER_ENTRY_LNG,
        occupancy, _spot_gps_map
    )
    nearest_name = nearest["name"] if nearest else None

    # ── Draw overlays ─────────────────────────────────────
    for spot_data in occupancy:
        pts  = np.array(spot_data["coordinates"], np.int32)
        name = spot_data["name"]

        if name == nearest_name:
            # Cyan highlight for nearest vacant spot
            color = (255, 255, 0)   # cyan in BGR
        elif spot_data["occupied"]:
            color = (0, 0, 255)     # red
        else:
            color = (0, 255, 0)     # green

        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], color)
        frame = cv2.addWeighted(overlay, 0.30, frame, 0.70, 0)
        cv2.polylines(frame, [pts], True, color, 2)

        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))

        if name == nearest_name and nearest:
            label = f'{name} NEAREST {nearest["distance_m"]}m'
            cv2.putText(frame, label, (cx - 40, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 3)    # black outline
            cv2.putText(frame, label, (cx - 40, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 0), 2) # cyan text
        else:
            label = f'{name} {"OCC" if spot_data["occupied"] else "VAC"}'
            cv2.putText(frame, label, (cx - 20, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # ── Summary banner ────────────────────────────────────
    summary = f"  VACANT: {vacant_count} | OCCUPIED: {occupied_count} | TOTAL: {len(occupancy)}"
    if nearest:
        summary += f"  |  NEAREST: {nearest_name} ({nearest['distance_m']}m)"
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), (0, 0, 0), -1)
    cv2.putText(frame, summary, (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    return frame, occupancy, vacant_count, occupied_count, nearest


def generate_frames():
    """Generator called by Flask /video_feed — yields JPEG frames."""
    global latest_frame, latest_status

    print("🔄  Loading YOLOv8 model …")
    model = YOLO("yolov8s.pt")
    spots = load_spots()
    print(f"✅  Model ready | 📍 {len(spots)} parking spots loaded")
    print(f"📱  Connecting to phone: {PHONE_STREAM_URL}")

    cap = cv2.VideoCapture(PHONE_STREAM_URL)

    if not cap.isOpened():
        print("❌  Cannot connect to phone camera!")
        print("    Checklist:")
        print("    1️⃣  Phone and laptop on the SAME WiFi network")
        print("    2️⃣  IP Webcam app is running and 'Start server' pressed")
        print(f"   3️⃣  URL is correct → {PHONE_STREAM_URL}")
        return

    print("✅  Connected to phone camera — streaming started!")
    frame_count = 0

    while True:
        success, frame = cap.read()
        if not success:
            print("⚠️  Frame read failed — reconnecting …")
            cap.release()
            cap = cv2.VideoCapture(PHONE_STREAM_URL)
            continue

        frame_count += 1

        annotated, occupancy, vacant, occupied, nearest = detect_and_annotate(
            frame, model, spots
        )

        # Update shared state (thread-safe)
        with _lock:
            latest_frame  = annotated.copy()
            latest_status = {
                "total":    len(occupancy),
                "vacant":   vacant,
                "occupied": occupied,
                "spots":    [{"name": s["name"], "occupied": s["occupied"]}
                             for s in occupancy],
                "nearest":  nearest,   # ← new field
            }

        # Save to MongoDB every N frames
        if frame_count % DB_SAVE_EVERY_N == 0:
            save_to_mongodb(occupancy)

        # Encode frame as JPEG for streaming
        ret, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    cap.release()


def get_latest_status():
    with _lock:
        return latest_status.copy()