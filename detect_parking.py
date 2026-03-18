import cv2
import json
import numpy as np
import os
from ultralytics import YOLO

from utils_parking import calculate_iou
from localization import run_localization

# ✅ NEW IMPORTS (ADDED)
from pymongo import MongoClient
from datetime import datetime

# ── Config ────────────────────────────────────────────────
IMAGE_PATH     = "images/parking.jpg"
SPOTS_JSON     = "data/parking_spots.json"
OUTPUT_IMAGE   = "images/parking_result.jpg"
IOU_THRESHOLD  = 0.20
CONF_THRESHOLD = 0.25
# ─────────────────────────────────────────────────────────


def load_model():
    print("🔄 Loading YOLOv8 model...")
    model = YOLO("yolov8s.pt")
    print("✅ Model loaded!\n")
    return model


# ✅ NEW FUNCTION (ADDED)
def save_to_mongodb(results, loc_result):
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client["parking_system"]
        col = db["parking_status"]

        doc = {
            "timestamp": datetime.now(),
            "total_spots": len(results),
            "vacant_count": sum(1 for r in results if not r["occupied"]),
            "occupied_count": sum(1 for r in results if r["occupied"]),
            "recommended_spot": loc_result["recommended_spot"] if loc_result else None,
            "recommended_distance": loc_result["distance_meters"] if loc_result else None,
            "spots": [
                {
                    "name": r["name"],
                    "occupied": r["occupied"],
                    "iou": r["iou"]
                }
                for r in results
            ]
        }

        col.delete_many({})
        col.insert_one(doc)

        print("✅ Saved to MongoDB!")

    except Exception as e:
        print(f"⚠️ MongoDB Error: {e}")


def detect_vehicles(model, image_path):
    results = model(image_path, conf=CONF_THRESHOLD,
                    verbose=False, imgsz=1280)

    vehicle_classes = {2, 5, 7}
    vehicles = []

    for box in results[0].boxes:
        cls = int(box.cls[0])
        if cls in vehicle_classes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            vehicles.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": round(conf, 3),
                "class": cls
            })

    print(f"🚗 Detected {len(vehicles)} vehicle(s) in image")
    return vehicles


def debug_yolo(image_path, vehicles):
    img = cv2.imread(image_path)
    if not vehicles:
        print("  ⚠️  No vehicles detected by YOLO!")
    for v in vehicles:
        x1, y1, x2, y2 = [int(c) for c in v["bbox"]]
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(img, f'car {v["confidence"]:.2f}',
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    cv2.namedWindow("DEBUG - YOLO Detections", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("DEBUG - YOLO Detections", 1000, 700)
    cv2.imshow("DEBUG - YOLO Detections", img)
    print("  📸 Debug window — press any key to continue...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def check_occupancy(spots, vehicles):
    results = []

    for spot in spots:
        polygon = spot["coordinates"]
        occupied = False
        best_iou = 0.0

        for vehicle in vehicles:
            iou = calculate_iou(vehicle["bbox"], polygon)
            if iou >= IOU_THRESHOLD:
                occupied = True
                best_iou = max(best_iou, iou)

        results.append({
            "name": spot["name"],
            "coordinates": polygon,
            "occupied": occupied,
            "iou": round(best_iou, 3)
        })

    return results


def draw_results(image_path, occupancy_results, output_path):
    img = cv2.imread(image_path)

    vacant_count = 0
    occupied_count = 0

    for spot in occupancy_results:
        pts = np.array(spot["coordinates"], np.int32)
        color = (0, 0, 255) if spot["occupied"] else (0, 255, 0)
        status = "OCC" if spot["occupied"] else "VAC"
        label = f'{spot["name"]} {status}'

        overlay = img.copy()
        cv2.fillPoly(overlay, [pts], color)
        img = cv2.addWeighted(overlay, 0.25, img, 0.75, 0)

        cv2.polylines(img, [pts], True, color, 2)

        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        cv2.putText(img, label, (cx - 20, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        if spot["occupied"]:
            occupied_count += 1
        else:
            vacant_count += 1

    summary = (f"  VACANT: {vacant_count}   |   "
               f"OCCUPIED: {occupied_count}   |   "
               f"TOTAL: {len(occupancy_results)}")
    cv2.rectangle(img, (0, 0), (img.shape[1], 40), (0, 0, 0), -1)
    cv2.putText(img, summary, (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

    cv2.imwrite(output_path, img)
    print(f"💾 Result saved → {output_path}")
    return img


def main():
    # ── 1. Check spots file ──────────────────────────────
    if not os.path.exists(SPOTS_JSON):
        print("❌ No parking spots defined yet!")
        print("   Run this first:  python define_spots.py")
        return

    # ── 2. Load spots ────────────────────────────────────
    with open(SPOTS_JSON) as f:
        spots = json.load(f)
    print(f"📍 Loaded {len(spots)} parking spots\n")

    # ── 3. Load model & detect ───────────────────────────
    model = load_model()
    vehicles = detect_vehicles(model, IMAGE_PATH)

    # ── 4. Debug YOLO ────────────────────────────────────
    debug_yolo(IMAGE_PATH, vehicles)

    # ── 5. Check occupancy ───────────────────────────────
    results = check_occupancy(spots, vehicles)

    # ── 6. Draw & save ───────────────────────────────────
    img = draw_results(IMAGE_PATH, results, OUTPUT_IMAGE)

    # ── 7. Terminal summary ──────────────────────────────
    print("\n─── Spot-by-Spot Results ───────────────────")
    for r in results:
        icon = "🔴" if r["occupied"] else "🟢"
        status = "OCCUPIED" if r["occupied"] else "VACANT"
        print(f"  {icon} {r['name']:>4}  →  {status}  (IoU: {r['iou']})")
    print("────────────────────────────────────────────")

    # ✅ NEW: Localization
    vacant_list = [r["name"] for r in results if not r["occupied"]]
    loc_result = run_localization(vacant_list)

    # ✅ NEW: Save to MongoDB
    save_to_mongodb(results, loc_result)

    # ── 8. Show result window ────────────────────────────
    cv2.namedWindow("Parking Detection Result", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Parking Detection Result", 1000, 700)
    cv2.imshow("Parking Detection Result", img)
    print("\nPress any key to close...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()