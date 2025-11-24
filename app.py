from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
# Cho phép CORS toàn cục, hỗ trợ cả preflight OPTIONS
CORS(app, origins="https://luongtranbaoanhbirthday.netlify.app", supports_credentials=True)

# Kết nối MongoDB Atlas
uri = "mongodb+srv://nguyenxuanthanh1112010:<qIH3VyU7emvcYBFe>@cluster0.4s8ij9x.mongodb.net/?appName=Cluster0"
client = MongoClient(uri)
db = client["comment_db"]
collection = db["comments"]

@app.route("/")
def home():
    return "API đang chạy rồi nè! 🥳"

# API lấy comment
@app.route("/comments", methods=["GET"])
def get_comments():
    comments = list(collection.find({}, {"_id": 0}))
    return jsonify(comments)

# API gửi comment
@app.route("/comments", methods=["POST"])
def post_comment():
    data = request.get_json()
    name = data.get("name", "Ẩn danh")
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message is empty!"}), 400

    comment = {
        "name": name,
        "message": message,
        "replies": []
    }

    collection.insert_one(comment)
    return jsonify({"status": "ok"}), 201

# API gửi phản hồi
@app.route("/comments/<int:index>/reply", methods=["POST", "OPTIONS"])
def reply_comment(index):
    if request.method == "OPTIONS":
        # Phản hồi preflight
        return '', 200

    data = request.get_json()
    reply = {
        "name": data.get("name", "Ẩn danh"),
        "message": data.get("message", "").strip()
    }

    if not reply["message"]:
        return jsonify({"error": "Reply is empty!"}), 400

    # Lấy tất cả comments (ẩn _id để dễ xử lý)
    comments = list(collection.find({}, {"_id": 0}))

    if index < 0 or index >= len(comments):
        return jsonify({"error": "Invalid comment index"}), 404

    target_message = comments[index]["message"]

    collection.update_one(
        {"message": target_message},
        {"$push": {"replies": reply}}
    )

    return jsonify({"status": "reply ok"}), 201

# Chạy server
if __name__ == "__main__":
    app.run(debug=True)