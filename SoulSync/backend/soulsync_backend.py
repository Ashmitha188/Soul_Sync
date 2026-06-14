# Soul Sync - Flask Backend
# pip install flask flask-cors

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json, os

app = Flask(__name__)
CORS(app)

# ── Simple in-memory store (replace with DB later) ──
DB = {
    "patients": {},    # sid -> patient data
    "guardians": {},   # sid -> guardian data
    "lifestyle": {},   # sid -> today's food/med logs
    "chat_history": {},# sid -> messages
    "mood_alerts": {}  # sid -> music mood events
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GUARDIAN ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/guardian/register", methods=["POST"])
def register_guardian():
    data = request.json
    name  = data.get("name", "").strip()
    email = data.get("email", "").strip()
    if not name or not email:
        return jsonify({"error": "Name and email required"}), 400

    import random
    sid = "SS" + str(random.randint(1000, 9999))
    DB["guardians"][sid] = {
        "name": name,
        "email": email,
        "sid": sid,
        "created": datetime.now().isoformat()
    }
    return jsonify({"sid": sid, "message": "Guardian registered!"})


@app.route("/api/guardian/<sid>", methods=["GET"])
def get_guardian(sid):
    g = DB["guardians"].get(sid)
    if not g:
        return jsonify({"error": "Guardian not found"}), 404
    return jsonify(g)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PATIENT ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/patient/connect", methods=["POST"])
def connect_patient():
    data = request.json
    sid  = data.get("sid", "").strip().upper()
    name = data.get("name", "").strip()
    if not sid or not name:
        return jsonify({"error": "SID and name required"}), 400
    if sid not in DB["guardians"]:
        return jsonify({"error": "Invalid SID"}), 404

    DB["patients"][sid] = {"name": name, "sid": sid, "connected": datetime.now().isoformat()}
    return jsonify({"message": f"Welcome {name}!", "guardian": DB["guardians"][sid]["name"]})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LIFESTYLE LOGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/lifestyle/log", methods=["POST"])
def log_lifestyle():
    data = request.json
    sid  = data.get("sid")
    key  = data.get("key")   # breakfast / lunch / dinner / morning / afternoon / night
    val  = data.get("value") # yes / no / d (done) / p (pending)
    if not sid or not key or val is None:
        return jsonify({"error": "sid, key, value required"}), 400

    if sid not in DB["lifestyle"]:
        DB["lifestyle"][sid] = {}
    DB["lifestyle"][sid][key] = {"value": val, "time": datetime.now().isoformat()}
    return jsonify({"message": "Logged!", "data": DB["lifestyle"][sid]})


@app.route("/api/lifestyle/<sid>", methods=["GET"])
def get_lifestyle(sid):
    return jsonify(DB["lifestyle"].get(sid, {}))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHAT HISTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/chat/save", methods=["POST"])
def save_chat():
    data    = request.json
    sid     = data.get("sid")
    contact = data.get("contact")
    message = data.get("message")
    flagged = data.get("flagged", False)
    if not sid or not contact or not message:
        return jsonify({"error": "sid, contact, message required"}), 400

    if sid not in DB["chat_history"]:
        DB["chat_history"][sid] = []
    DB["chat_history"][sid].append({
        "contact": contact,
        "message": message,
        "flagged": flagged,
        "time": datetime.now().isoformat()
    })
    return jsonify({"message": "Saved!"})


@app.route("/api/chat/<sid>", methods=["GET"])
def get_chats(sid):
    return jsonify(DB["chat_history"].get(sid, []))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MOOD / MUSIC ALERTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/mood/alert", methods=["POST"])
def mood_alert():
    data  = request.json
    sid   = data.get("sid")
    mood  = data.get("mood")   # depressed / good
    songs = data.get("songs")  # list of songs played
    if not sid or not mood:
        return jsonify({"error": "sid and mood required"}), 400

    if sid not in DB["mood_alerts"]:
        DB["mood_alerts"][sid] = []
    DB["mood_alerts"][sid].append({
        "mood": mood,
        "songs": songs,
        "time": datetime.now().isoformat()
    })
    return jsonify({"message": "Alert saved!"})


@app.route("/api/mood/<sid>", methods=["GET"])
def get_mood_alerts(sid):
    return jsonify(DB["mood_alerts"].get(sid, []))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TELEGRAM ALERT (server-side)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/telegram/send", methods=["POST"])
def send_telegram():
    import urllib.request
    data    = request.json
    message = data.get("message", "")
    TG_TOKEN = "8673833008:AAGtme9ChpD9UvDJUDL2uB9MXQjaRH656hM"
    TG_CHAT  = "8506288386"
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TG_CHAT, "text": message}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req)
        return jsonify({"message": "Sent!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HEALTH CHECK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "Soul Sync backend running ✅", "time": datetime.now().isoformat()})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
