import os
import uuid
from datetime import datetime, timezone

import boto3
import redis
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask, jsonify, request

app = Flask(__name__)


# ---------- Lab 3: time endpoint ----------
@app.route("/time", methods=["GET"])
def get_time():
    return jsonify({"time": datetime.now(timezone.utc).isoformat()}), 200


# ---------- Part A: object storage ----------
BUCKET = os.environ["BUCKET"]
# S3_ENDPOINT: local storage only; do not set it for AWS
ENDPOINT = os.environ.get("S3_ENDPOINT")
MAX_FILE_SIZE = 1024 * 1024  # 1 MB

s3 = boto3.client(
    "s3",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    endpoint_url=ENDPOINT,
    config=Config(s3={"addressing_style": "path"}) if ENDPOINT else None,
)


# create the bucket once if it does not exist yet
def ensure_bucket():
    try:
        s3.head_bucket(Bucket=BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=BUCKET)


ensure_bucket()


@app.route("/files", methods=["POST"])
def save_file():
    data = request.get_json(silent=True)
    if not data or not isinstance(data.get("text"), str) or not data["text"]:
        return jsonify({"error": "field 'text' is required"}), 400

    body = data["text"].encode("utf-8")
    if len(body) > MAX_FILE_SIZE:
        return jsonify({"error": "file is larger than 1 MB"}), 400

    file_id = str(uuid.uuid4())
    try:
        s3.put_object(Bucket=BUCKET, Key=f"files/{file_id}.txt", Body=body)
    except (ClientError, BotoCoreError):
        return jsonify({"error": "storage unavailable"}), 503
    return jsonify({"id": file_id}), 201


@app.route("/files/<file_id>", methods=["GET"])
def read_file(file_id):
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=f"files/{file_id}.txt")
        text = obj["Body"].read().decode("utf-8")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return jsonify({"error": "file not found"}), 404
        return jsonify({"error": "storage unavailable"}), 503
    except BotoCoreError:
        return jsonify({"error": "storage unavailable"}), 503
    return jsonify({"id": file_id, "text": text}), 200


# ---------- Part B: Redis primary + replica ----------
R_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
primary = redis.Redis(host=R_HOST, port=int(os.environ.get("REDIS_PRIMARY_PORT", "6379")),
                      decode_responses=True, socket_timeout=2)
replica = redis.Redis(host=R_HOST, port=int(os.environ.get("REDIS_REPLICA_PORT", "6380")),
                      decode_responses=True, socket_timeout=2)


@app.route("/counter/increment", methods=["POST"])
def increment():
    try:
        value = primary.incr("counter")          # writes go to the primary only
    except redis.exceptions.RedisError:
        return jsonify({"error": "storage unavailable"}), 503
    return jsonify({"value": value, "source": "primary"}), 200


@app.route("/counter", methods=["GET"])
def get_counter():
    source = request.args.get("from", "primary")  # ?from=primary or ?from=replica
    client = replica if source == "replica" else primary
    try:
        value = client.get("counter")
    except redis.exceptions.RedisError:
        return jsonify({"error": "storage unavailable"}), 503
    return jsonify({"value": int(value or 0), "source": source}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
