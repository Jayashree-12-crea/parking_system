from flask import Flask, render_template, jsonify
from pymongo import MongoClient
import base64
import os

app = Flask(__name__)

# ── MongoDB Connection ──────────────────────────────────
client = MongoClient("mongodb://localhost:27017/")
db     = client["parking_system"]
col    = db["parking_status"]
# ───────────────────────────────────────────────────────


def get_latest_data():
    """Get latest parking data from MongoDB."""
    doc = col.find_one(sort=[("timestamp", -1)])
    if not doc:
        return None
    doc["_id"] = str(doc["_id"])
    if "timestamp" in doc:
        doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return doc


def get_result_image():
    """Read result image and convert to base64 for web display."""
    img_path = "images/parking_result.jpg"
    if not os.path.exists(img_path):
        return None
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


@app.route("/")
def index():
    """Main website page."""
    data  = get_latest_data()
    image = get_result_image()
    return render_template("index.html", data=data, image=image)


@app.route("/api/status")
def api_status():
    """REST API endpoint — returns latest parking data as JSON."""
    data = get_latest_data()
    if not data:
        return jsonify({"error": "No data available"}), 404
    return jsonify(data)


@app.route("/api/refresh")
def api_refresh():
    """Trigger a new detection run."""
    try:
        import subprocess
        subprocess.Popen(["python", "detect_parking.py"])
        return jsonify({"status": "Detection started!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🌐 Starting Flask server...")
    print("   Open browser at: http://localhost:5000")
    app.run(debug=True, port=5000)