import cv2
import json
import numpy as np
import os

# ── Config ────────────────────────────────────────────────
IMAGE_PATH  = "images/parking.jpg"
OUTPUT_JSON = "data/parking_spots.json"
# ─────────────────────────────────────────────────────────

spots           = []
current_polygon = []
img_display     = None
img_original    = None
spot_counter    = 1


def redraw():
    """Redraw all saved spots + current in-progress polygon."""
    global img_display
    img_display = img_original.copy()

    # Draw all saved spots in green
    for spot in spots:
        pts = np.array(spot["coordinates"], np.int32)
        cv2.polylines(img_display, [pts], True, (0, 255, 0), 2)
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        cv2.putText(img_display, spot["name"], (cx - 15, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

    # Draw current polygon points in red (in progress)
    for pt in current_polygon:
        cv2.circle(img_display, tuple(pt), 5, (0, 0, 255), -1)
    if len(current_polygon) > 1:
        cv2.polylines(img_display,
                      [np.array(current_polygon, np.int32)],
                      False, (0, 0, 255), 2)

    # Instructions overlay at bottom
    h = img_display.shape[0]
    cv2.rectangle(img_display, (0, h - 30), (img_display.shape[1], h), (0, 0, 0), -1)
    cv2.putText(img_display,
                "Click corners | ENTER=save spot | U=undo | R=reset | Q=quit",
                (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        current_polygon.append([x, y])
        redraw()


def main():
    global img_display, img_original, spot_counter

    # Check image exists
    if not os.path.exists(IMAGE_PATH):
        print(f"❌ Image not found at: {IMAGE_PATH}")
        print("   Please put your parking lot image as images/parking.jpg")
        return

    img_original = cv2.imread(IMAGE_PATH)
    img_display  = img_original.copy()

    cv2.namedWindow("Define Parking Spots", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Define Parking Spots", 1000, 700)
    cv2.setMouseCallback("Define Parking Spots", mouse_callback)

    print("\n📌 HOW TO DEFINE PARKING SPOTS:")
    print("─────────────────────────────────────────")
    print("  🖱️  Left-click  → add a corner point of a spot")
    print("  ⏎  ENTER       → finish & save current spot")
    print("  U              → undo last point")
    print("  R              → reset current spot")
    print("  Q              → quit & save all spots to JSON")
    print("─────────────────────────────────────────")
    print("  Click 4 corners of each parking space,")
    print("  then press ENTER. Repeat for each spot.\n")

    while True:
        cv2.imshow("Define Parking Spots", img_display)
        key = cv2.waitKey(20) & 0xFF

        # ENTER → save current spot
        if key == 13:
            if len(current_polygon) >= 3:
                name = f"P{spot_counter}"
                spots.append({
                    "name": name,
                    "coordinates": current_polygon.copy()
                })
                print(f"  ✅ Saved {name}  ({len(current_polygon)} points)")
                spot_counter += 1
                current_polygon.clear()
                redraw()
            else:
                print("  ⚠️  Need at least 3 points — keep clicking corners!")

        # U → undo last point
        elif key == ord('u'):
            if current_polygon:
                current_polygon.pop()
                redraw()
                print("  ↩️  Undo last point")

        # R → reset current polygon
        elif key == ord('r'):
            current_polygon.clear()
            redraw()
            print("  🔄 Reset current spot")

        # Q → quit and save
        elif key == ord('q'):
            break

    cv2.destroyAllWindows()

    if spots:
        os.makedirs("data", exist_ok=True)
        with open(OUTPUT_JSON, "w") as f:
            json.dump(spots, f, indent=2)
        print(f"\n💾 Saved {len(spots)} spots → {OUTPUT_JSON}")
    else:
        print("\n⚠️  No spots were saved.")


if __name__ == "__main__":
    main()