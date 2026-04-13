import cv2
import numpy as np
from ultralytics import YOLO
from shapely.geometry import Polygon

# 1. Load Model
# If accuracy is still low, change "yolov8n.pt" to "yolov8m.pt"
model = YOLO("yolov8n.pt")

# 2. Load Image
IMAGE_PATH  = "images/parking.jpg"

if image is None:
    print(f"Error: Could not load {image_path}")
    exit()

clone = image.copy()
roi_points = []
parking_slots = []

# ---------------- ROI SELECTION ---------------- #

def mouse_click(event, x, y, flags, param):
    global roi_points, parking_slots, image
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points.append((x, y))
        cv2.circle(image, (x, y), 5, (0, 0, 255), -1)
        if len(roi_points) == 4:
            parking_slots.append(roi_points.copy())
            pts = np.array(roi_points, np.int32)
            cv2.polylines(image, [pts], True, (0, 255, 0), 2)
            roi_points.clear()

cv2.namedWindow("Select Parking Slots")
cv2.setMouseCallback("Select Parking Slots", mouse_click)

print("1. Click 4 corners for each parking slot.")
print("2. Press 'ESC' when all slots are drawn.")

while True:
    cv2.imshow("Select Parking Slots", image)
    if cv2.waitKey(1) == 27: # ESC key
        break
cv2.destroyAllWindows()

# ---------------- VEHICLE DETECTION ---------------- #

results = model(clone)[0]
# We store the full box coordinates now
vehicle_boxes = []

# Standard classes + your specific hallucinations (cell phone)
vehicle_classes = ["car", "truck", "bus", "motorcycle", "cell phone"]

for box in results.boxes:
    cls_id = int(box.cls[0])
    label = model.names[cls_id]
    conf = float(box.conf[0])

    if label in vehicle_classes and conf > 0.2:
        coords = map(int, box.xyxy[0])
        vehicle_boxes.append(list(coords))
        
        # Draw detection for visual debugging
        x1, y1, x2, y2 = vehicle_boxes[-1]
        cv2.rectangle(clone, (x1, y1), (x2, y2), (255, 255, 0), 1)
        cv2.putText(clone, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,0), 1)

# ---------------- SLOT CHECKING (IoU LOGIC) ---------------- #

total_slots = len(parking_slots)
occupied_count = 0

for slot in parking_slots:
    # Create polygon for the drawn parking slot
    slot_poly = Polygon(slot)
    is_occupied = False
    
    for (vx1, vy1, vx2, vy2) in vehicle_boxes:
        # Create polygon for the car bounding box
        car_poly = Polygon([(vx1, vy1), (vx2, vy1), (vx2, vy2), (vx1, vy2)])
        
        if slot_poly.intersects(car_poly):
            intersection_area = slot_poly.intersection(car_poly).area
            # Check if intersection is at least 15% of the slot's area
            if (intersection_area / slot_poly.area) > 0.15:
                is_occupied = True
                break
                
    if is_occupied:
        color = (0, 0, 255) # Red
        occupied_count += 1
        # Fill the slot with semi-transparent red
        overlay = clone.copy()
        cv2.fillPoly(overlay, [np.array(slot, np.int32)], (0, 0, 150))
        cv2.addWeighted(overlay, 0.4, clone, 0.6, 0, clone)
    else:
        color = (0, 255, 0) # Green
        
    cv2.polylines(clone, [np.array(slot, np.int32)], True, color, 2)

vacant_count = total_slots - occupied_count

# ---------------- DISPLAY RESULT ---------------- #

# Text Overlay
cv2.rectangle(clone, (10, 10), (280, 140), (0, 0, 0), -1)
cv2.putText(clone, f"Total Slots: {total_slots}", (20, 40), 1, 1.5, (255,255,255), 2)
cv2.putText(clone, f"Occupied: {occupied_count}", (20, 80), 1, 1.5, (0,0,255), 2)
cv2.putText(clone, f"Vacant: {vacant_count}", (20, 120), 1, 1.5, (0,255,0), 2)

cv2.imshow("Final Detection", clone)
cv2.waitKey(0)
cv2.destroyAllWindows()