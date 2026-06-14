# Soul Sync - Flask + MongoDB Backend
# pip install flask flask-cors pymongo python-dotenv

from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import os, json, random

app = Flask(__name__)
CORS(app)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MONGODB CONNECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")  # or your Atlas URI
client    = MongoClient(MONGO_URI)
db        = client["soulsync"]

# Collections
guardians   = db["guardians"]
patients    = db["patients"]
lifestyle   = db["lifestyle"]
chats       = db["chats"]
mood_alerts = db["mood_alerts"]

# Helper: convert ObjectId to string
def clean(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GUARDIAN ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/guardian/register", methods=["POST"])
def register_guardian():
    data  = request.json
    name  = data.get("name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    relation = data.get("relation", "").strip()

    if not name or not email:
        return jsonify({"error": "Name and email required"}), 400

    # Check if email already registered
    existing = guardians.find_one({"email": email})
    if existing:
        return jsonify({"sid": existing["sid"], "message": "Already registered!"}), 200

    sid = "SS" + str(random.randint(1000, 9999))
    # Make sure SID is unique
    while guardians.find_one({"sid": sid}):
        sid = "SS" + str(random.randint(1000, 9999))

    doc = {
        "name": name,
        "email": email,
        "phone": phone,
        "relation": relation,
        "sid": sid,
        "created_at": datetime.now()
    }
    guardians.insert_one(doc)
    return jsonify({"sid": sid, "message": "Guardian registered successfully!"})


@app.route("/api/guardian/<sid>", methods=["GET"])
def get_guardian(sid):
    g = guardians.find_one({"sid": sid.upper()})
    if not g:
        return jsonify({"error": "Guardian not found"}), 404
    return jsonify(clean(g))


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

    guardian = guardians.find_one({"sid": sid})
    if not guardian:
        return jsonify({"error": "Invalid SID — ask your guardian to register first"}), 404

    # Upsert patient record
    patients.update_one(
        {"sid": sid},
        {"$set": {"name": name, "sid": sid, "connected_at": datetime.now()}},
        upsert=True
    )
    return jsonify({
        "message": f"Welcome {name}!",
        "guardian_name": guardian["name"]
    })


@app.route("/api/patient/<sid>", methods=["GET"])
def get_patient(sid):
    p = patients.find_one({"sid": sid.upper()})
    if not p:
        return jsonify({"error": "Patient not found"}), 404
    return jsonify(clean(p))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LIFESTYLE LOGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/lifestyle/log", methods=["POST"])
def log_lifestyle():
    data  = request.json
    sid   = data.get("sid", "").upper()
    key   = data.get("key")    # breakfast/lunch/dinner/morning/afternoon/night
    value = data.get("value")  # yes/no/d/p

    if not sid or not key or value is None:
        return jsonify({"error": "sid, key, value required"}), 400

    today = datetime.now().strftime("%Y-%m-%d")

    lifestyle.update_one(
        {"sid": sid, "date": today},
        {"$set": {
            f"logs.{key}": {"value": value, "time": datetime.now().isoformat()}
        }},
        upsert=True
    )
    # Return full today's log
    doc = lifestyle.find_one({"sid": sid, "date": today})
    return jsonify({"message": "Logged!", "logs": doc.get("logs", {})})


@app.route("/api/lifestyle/<sid>", methods=["GET"])
def get_lifestyle(sid):
    today = datetime.now().strftime("%Y-%m-%d")
    doc = lifestyle.find_one({"sid": sid.upper(), "date": today})
    if not doc:
        return jsonify({"logs": {}, "date": today})
    return jsonify({"logs": doc.get("logs", {}), "date": today})


@app.route("/api/lifestyle/<sid>/history", methods=["GET"])
def get_lifestyle_history(sid):
    # Last 7 days
    docs = list(lifestyle.find(
        {"sid": sid.upper()},
        {"_id": 0, "date": 1, "logs": 1}
    ).sort("date", -1).limit(7))
    return jsonify(docs)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHAT HISTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/chat/save", methods=["POST"])
def save_chat():
    data    = request.json
    sid     = data.get("sid", "").upper()
    contact = data.get("contact")
    message = data.get("message")
    flagged = data.get("flagged", False)

    if not sid or not contact or not message:
        return jsonify({"error": "sid, contact, message required"}), 400

    chats.insert_one({
        "sid": sid,
        "contact": contact,
        "message": message,
        "flagged": flagged,
        "time": datetime.now()
    })
    return jsonify({"message": "Chat saved!"})


@app.route("/api/chat/<sid>", methods=["GET"])
def get_chats(sid):
    docs = list(chats.find(
        {"sid": sid.upper()},
        {"_id": 0}
    ).sort("time", -1).limit(50))
    return jsonify(docs)


@app.route("/api/chat/<sid>/flagged", methods=["GET"])
def get_flagged_chats(sid):
    docs = list(chats.find(
        {"sid": sid.upper(), "flagged": True},
        {"_id": 0}
    ).sort("time", -1))
    return jsonify(docs)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MOOD / MUSIC ALERTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/mood/alert", methods=["POST"])
def mood_alert():
    data  = request.json
    sid   = data.get("sid", "").upper()
    mood  = data.get("mood")   # depressed / good
    songs = data.get("songs", [])

    if not sid or not mood:
        return jsonify({"error": "sid and mood required"}), 400

    mood_alerts.insert_one({
        "sid": sid,
        "mood": mood,
        "songs": songs,
        "time": datetime.now()
    })
    return jsonify({"message": "Mood alert saved!"})


@app.route("/api/mood/<sid>", methods=["GET"])
def get_mood_alerts(sid):
    docs = list(mood_alerts.find(
        {"sid": sid.upper()},
        {"_id": 0}
    ).sort("time", -1).limit(20))
    return jsonify(docs)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STREAK / PROGRESS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/streak/<sid>", methods=["GET"])
def get_streak(sid):
    # Pull last 7 days of lifestyle data
    docs = list(lifestyle.find(
        {"sid": sid.upper()},
        {"_id": 0, "date": 1, "logs": 1}
    ).sort("date", -1).limit(7))

    history = []
    for doc in docs:
        logs = doc.get("logs", {})
        food_done = sum(1 for k in ["breakfast","lunch","dinner"] if logs.get(k,{}).get("value") == "yes")
        med_done  = sum(1 for k in ["morning","afternoon","night"]  if logs.get(k,{}).get("value") == "d")
        history.append({
            "date": doc["date"],
            "food_pct": round(food_done / 3 * 100),
            "med_pct":  round(med_done  / 3 * 100),
            "total_pct": round((food_done + med_done) / 6 * 100)
        })
    return jsonify(history)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TELEGRAM (server-side)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/telegram/send", methods=["POST"])
def send_telegram():
    import urllib.request
    data    = request.json
    message = data.get("message", "")

    TG_TOKEN = os.getenv("TG_TOKEN", "8673833008:AAGtme9ChpD9UvDJUDL2uB9MXQjaRH656hM")
    TG_CHAT  = os.getenv("TG_CHAT",  "8506288386")

    url     = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TG_CHAT, "text": message}).encode()
    req     = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req)
        return jsonify({"message": "Telegram message sent!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HEALTH CHECK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/health", methods=["GET"])
def health():
    try:
        client.admin.command("ping")
        db_status = "connected"
    except:
        db_status = "disconnected"
    return jsonify({
        "status": "Soul Sync backend running",
        "database": db_status,
        "time": datetime.now().isoformat()
    })


if __name__ == "__main__":
    print("Soul Sync backend starting...")
    print("MongoDB:", MONGO_URI)
    app.run(debug=True, port=5000)
