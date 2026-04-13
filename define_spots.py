"""
define_spots.py  —  Draw parking spot polygons on a LIVE frame from your phone camera.

HOW TO USE:
  1. Make sure IP Webcam is running on your phone
  2. Update PHONE_STREAM_URL below with your phone's IP
  3. Run:  python define_spots.py
  4. A window opens showing a live frame from your phone
  5. Press SPACE to freeze/capture that frame
  6. Click 4 corners of each parking spot (draws a polygon)
  7. Press ENTER after each spot to save it
  8. Press 'u' to undo the last point if you mis-click
  9. Press 's' when all spots are done — saves to data/parking_spots.json
  10. Press 'q' to quit without saving

CONTROLS:
  SPACE      → freeze the live feed and start drawing
  Left-click → place a point
  ENTER      → finish current spot (needs at least 3 points)
  u          → undo last point
  s          → save all spots and exit
  r          → restart (clear all spots and re-capture frame)
  q          → quit without saving
"""

import cv2

import json
import os
import numpy as np

# ══════════════════════════════════════════════════════════
#  ✅ CHANGE THIS to your phone's IP address
# ══════════════════════════════════════════════════════════
PHONE_STREAM_URL = "http://10.138.4.71:8080/video"   # ← CHANGE THIS

SPOTS_JSON   = "data/parking_spots.json"
WINDOW_NAME  = "Define Parking Spots"
# ─────────────────────────────────────────────────────────

# Colours
COL_POINT    = (0,   255, 255)   # yellow  — point dot
COL_LINE     = (0,   255, 255)   # yellow  — polygon edges being drawn
COL_DONE     = (0,   255,   0)   # green   — completed spots
COL_OCCUPIED = (0,     0, 255)   # red     — (unused here, kept for reference)
COL_TEXT     = (255, 255, 255)   # white


# ── State ─────────────────────────────────────────────────
spots        = []          # list of completed spots: [{name, coordinates}]
current_pts  = []          # points being placed for the current spot
frozen_frame = None        # the captured frame we draw on
display_img  = None        # copy we redraw each time


def spot_name(index):
    return f"S{index + 1}"


def redraw():
    """Redraw display_img from frozen_frame + all saved spots + current points."""
    global display_img
    display_img = frozen_frame.copy()

    # Draw completed spots
    for spot in spots:
        pts = np.array(spot["coordinates"], np.int32)
        overlay = display_img.copy()
        cv2.fillPoly(overlay, [pts], COL_DONE)
        display_img = cv2.addWeighted(overlay, 0.20, display_img, 0.80, 0)
        cv2.polylines(display_img, [pts], True, COL_DONE, 2)
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        cv2.putText(display_img, spot["name"], (cx - 10, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COL_TEXT, 2)

    # Draw in-progress polygon
    for pt in current_pts:
        cv2.circle(display_img, pt, 5, COL_POINT, -1)
    if len(current_pts) >= 2:
        cv2.polylines(display_img, [np.array(current_pts, np.int32)],
                      False, COL_LINE, 2)

    # HUD instructions
    instructions = [
        f"Spots saved: {len(spots)}   |   Points placed: {len(current_pts)}",
        "Left-click=add point  |  ENTER=finish spot  |  u=undo  |  s=save all  |  r=restart  |  q=quit",
    ]
    y = display_img.shape[0] - 50
    cv2.rectangle(display_img, (0, y - 10), (display_img.shape[1], display_img.shape[0]), (0, 0, 0), -1)
    for i, line in enumerate(instructions):
        cv2.putText(display_img, line, (10, y + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (180, 220, 255), 1)

    cv2.imshow(WINDOW_NAME, display_img)


def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        current_pts.append((x, y))
        redraw()


def capture_frame_from_phone():
    """Connect to phone camera and return one frame."""
    print(f"📱  Connecting to phone: {PHONE_STREAM_URL}")
    cap = cv2.VideoCapture(PHONE_STREAM_URL)
    if not cap.isOpened():
        print("❌  Cannot connect to phone camera!")
        print("    Check: same WiFi, IP Webcam running, correct IP in PHONE_STREAM_URL")
        return None

    print("✅  Connected! Showing live feed — press SPACE to freeze and start drawing …")

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 1100, 700)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️  Frame read failed, retrying …")
            continue

        preview = frame.copy()
        cv2.putText(preview,
                    "LIVE FEED — Press SPACE to freeze and start defining spots",
                    (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow(WINDOW_NAME, preview)

        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):   # SPACE → freeze
            cap.release()
            print("✅  Frame captured! Now click to define parking spots.")
            return frame
        elif key == ord('q'):
            cap.release()
            return None


def main():
    global frozen_frame, current_pts, spots

    os.makedirs("data", exist_ok=True)

    # ── Step 1: Capture a live frame ────────────────────
    frozen_frame = capture_frame_from_phone()
    if frozen_frame is None:
        print("Exiting.")
        return

    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)
    redraw()

    print("\n─── Controls ─────────────────────────────────────")
    print("  Left-click → place point")
    print("  ENTER      → finish current spot (min 3 points)")
    print("  u          → undo last point")
    print("  s          → save all spots to JSON and exit")
    print("  r          → clear everything and re-capture frame")
    print("  q          → quit without saving")
    print("──────────────────────────────────────────────────\n")

    while True:
        key = cv2.waitKey(0) & 0xFF

        # ── ENTER: finish current spot ──────────────────
        if key == 13:
            if len(current_pts) < 3:
                print("⚠️  Need at least 3 points to define a spot. Keep clicking.")
            else:
                name = spot_name(len(spots))
                spots.append({"name": name, "coordinates": list(current_pts)})
                print(f"✅  Spot {name} saved with {len(current_pts)} points. "
                      f"Total spots: {len(spots)}")
                current_pts = []
                redraw()

        # ── u: undo last point ──────────────────────────
        elif key == ord('u'):
            if current_pts:
                removed = current_pts.pop()
                print(f"↩️  Undid point {removed}")
                redraw()

        # ── s: save all to JSON ─────────────────────────
        elif key == ord('s'):
            if not spots:
                print("⚠️  No spots defined yet!")
            else:
                # Convert tuples to lists for JSON serialisation
                output = [
                    {"name": s["name"],
                     "coordinates": [list(p) for p in s["coordinates"]]}
                    for s in spots
                ]
                with open(SPOTS_JSON, "w") as f:
                    json.dump(output, f, indent=2)
                print(f"\n✅  Saved {len(output)} spots → {SPOTS_JSON}")
                print("    You can now run:  python app.py")
                break

        # ── r: restart ──────────────────────────────────
        elif key == ord('r'):
            print("🔄  Restarting — clearing all spots and re-capturing frame …")
            spots       = []
            current_pts = []
            cv2.destroyAllWindows()
            frozen_frame = capture_frame_from_phone()
            if frozen_frame is None:
                break
            cv2.setMouseCallback(WINDOW_NAME, mouse_callback)
            redraw()

        # ── q: quit ─────────────────────────────────────
        elif key == ord('q'):
            print("👋  Quit without saving.")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()