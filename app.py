# app.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from datetime import datetime

# load .env
load_dotenv()

MONGO_URI = os.getenv("mongodb+srv://nguyenxuanthanh1112010:qIH3VyU7emvcYBFe@cluster0.4s8ij9x.mongodb.net/?appName=Cluster0")  # MongoDB connection string
OWNER_EMAIL = os.getenv("nguyenxuanthanh916@gmail.com")  # email để gửi thông báo (nếu dùng)

if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable not set. Please create .env with MONGO_URI.")

app = Flask(__name__)
# CORS: allow your frontend origin (safer) or '*' for dev
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "https://luongtranbaoanhbirthday.netlify.app")
if FRONTEND_ORIGINS.strip() == "https://luongtranbaoanhbirthday.netlify.app":
    CORS(app, supports_credentials=True)
else:
    # support comma-separated list
    origins = [o.strip() for o in FRONTEND_ORIGINS.split(",")]
    CORS(app, origins=origins, supports_credentials=True)

# Mongo connect
client = MongoClient(MONGO_URI)
db = client.get_default_database() if client.get_default_database() else client["comment_db"]
collection = db["comments"]

# helpers
def iso_now():
    return datetime.utcnow().isoformat() + "Z"

def serialize_doc(doc):
    # Convert ObjectId to string and keep fields
    out = {
        "id": str(doc.get("_id")),
        "name": doc.get("name", "Ẩn danh"),
        "message": doc.get("message", ""),
        "replies": doc.get("replies", []),
        "time": doc.get("time", "")
    }
    return out

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "msg": "API đang chạy rồi ông ơi!"})

# GET all comments (root messages) with their replies
@app.route("/comments", methods=["GET"])
def get_comments():
    # return all root messages (parentId == None) sorted by time desc (newest first)
    docs = list(collection.find({"parentId": None}).sort("time", -1))
    results = []
    for d in docs:
        # for each root, fetch replies (embedded or separate)
        doc = serialize_doc(d)
        # replies may be stored as list of dicts (embedded)
        # if replies stored as ObjectId refs, adapt accordingly
        results.append(doc)
    return jsonify(results), 200

# POST a new root comment
@app.route("/comments", methods=["POST"])
def post_comment():
    data = request.get_json(force=True)
    name = (data.get("name") or "Ẩn danh").strip()
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is empty!"}), 400

    doc = {
        "name": name,
        "message": message,
        "replies": [],      # embedded replies
        "parentId": None,
        "time": iso_now()
    }

    result = collection.insert_one(doc)
    new_doc = collection.find_one({"_id": result.inserted_id})
    return jsonify({"status": "ok", "data": serialize_doc(new_doc)}), 201

# POST a reply to a comment by comment id (ObjectId string)
@app.route("/comments/<comment_id>/reply", methods=["POST"])
def reply_comment(comment_id):
    data = request.get_json(force=True)
    reply_name = (data.get("name") or "Ẩn danh").strip()
    reply_message = (data.get("message") or "").strip()
    if not reply_message:
        return jsonify({"error": "Reply is empty!"}), 400

    # validate comment_id
    try:
        oid = ObjectId(comment_id)
    except Exception:
        return jsonify({"error": "Invalid comment id"}), 400

    # ensure parent exists
    parent = collection.find_one({"_id": oid})
    if not parent:
        return jsonify({"error": "Parent comment not found"}), 404

    reply_obj = {
        "id": str(ObjectId()),
        "name": reply_name,
        "message": reply_message,
        "time": iso_now()
    }

    # push embedded reply
    collection.update_one({"_id": oid}, {"$push": {"replies": reply_obj}})

    updated = collection.find_one({"_id": oid})
    return jsonify({"status": "reply ok", "parent": serialize_doc(updated)}), 201

# helper: get single comment (optional)
@app.route("/comments/<comment_id>", methods=["GET"])
def get_comment(comment_id):
    try:
        oid = ObjectId(comment_id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400
    doc = collection.find_one({"_id": oid})
    if not doc:
        return jsonify({"error": "Not found"}), 404
    return jsonify(serialize_doc(doc)), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=(os.getenv("FLASK_DEBUG","1")=="1"))
