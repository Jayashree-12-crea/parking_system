from flask import Flask, render_template, jsonify, Response, request
from pymongo import MongoClient
import datetime
from video_stream import generate_frames, get_latest_status

app = Flask(__name__)

# ── MongoDB ──────────────────────────────────────────────
client  = MongoClient("mongodb://localhost:27017/")
db      = client["parking_system"]
col     = db["parking_status"]
res_col = db["reservations"]

res_col.create_index("expireAt", expireAfterSeconds=0)
# ────────────────────────────────────────────────────────


def get_latest_data():
    doc = col.find_one(sort=[("timestamp", -1)])
    if not doc:
        return None
    doc["_id"] = str(doc["_id"])
    if "timestamp" in doc:
        doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return doc


# ── Page routes ──────────────────────────────────────────

@app.route("/")
def index():
    data = get_latest_data()
    return render_template("index.html", data=data)


@app.route("/book")
def book_page():
    return render_template("book.html")


@app.route("/admin")
def admin_page():
    return render_template("admin.html")


# ── Video / live status ──────────────────────────────────

@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/live_status")
def api_live_status():
    return jsonify(get_latest_status())


@app.route("/api/status")
def api_status():
    data = get_latest_data()
    if not data:
        return jsonify({"error": "No data available"}), 404
    data["reservations"] = res_col.count_documents({})
    return jsonify(data)


# ── Booking ──────────────────────────────────────────────

@app.route("/api/book", methods=["POST"])
def create_booking():
    data  = request.json
    name  = data.get("name")
    plate = data.get("plate")

    if not name or not plate:
        return jsonify({"error": "Name and Plate are required"}), 400

    active_res  = res_col.count_documents({})
    total_spots = 14

    latest = get_latest_data()
    if latest and "total" in latest:
        total_spots = int(latest.get("total", 14))

    if active_res >= total_spots:
        return jsonify({"error": "No available slots. Lot is fully reserved."}), 400

    now       = datetime.datetime.utcnow()
    expire_at = now + datetime.timedelta(minutes=10)

    res_col.insert_one({
        "name":      name,
        "plate":     plate,
        "createdAt": now,
        "expireAt":  expire_at,
    })

    return jsonify({
        "success":  True,
        "message":  "Slot booked! You have 10 minutes to arrive.",
        "expireAt": expire_at.isoformat() + "Z",
    })


# ── Admin API ────────────────────────────────────────────

@app.route("/api/reservations")
def api_reservations():
    docs = list(res_col.find({}, {"_id": 0}).sort("createdAt", -1))
    for d in docs:
        if isinstance(d.get("createdAt"), datetime.datetime):
            d["createdAt"] = d["createdAt"].isoformat() + "Z"
        if isinstance(d.get("expireAt"), datetime.datetime):
            d["expireAt"] = d["expireAt"].isoformat() + "Z"
    return jsonify(docs)


# ── Nearest spot ─────────────────────────────────────────

@app.route("/api/nearest")
def api_nearest():
    status = get_latest_status()
    return jsonify({"nearest": status.get("nearest")})


# ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🌐  Flask server starting …")
    print("    Dashboard  → http://localhost:5000/")
    print("    Admin      → http://localhost:5000/admin")
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)