
import os
import subprocess
import threading
import time

from flask import Flask, jsonify, request

app = Flask(__name__)

RECOVERY_TOKEN = os.environ["RECOVERY_TOKEN"]
COOLDOWN_SECONDS = 60

recovery_lock = threading.Lock()
last_attempt = 0.0


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/recover", methods=["POST"])
def recover():
    global last_attempt

    # Authenticate the internal request.
    token = request.headers.get("X-Recovery-Token", "")
    if not token or token != RECOVERY_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True)

    # Only NGINX recovery is permitted.
    if not isinstance(payload, dict) or payload.get("service") != "nginx":
        return jsonify({"error": "Unsupported recovery request"}), 400

    # Prevent overlapping recovery attempts.
    if not recovery_lock.acquire(blocking=False):
        return jsonify({"status": "recovery_in_progress"}), 409

    try:
        now = time.monotonic()

        if now - last_attempt < COOLDOWN_SECONDS:
            return jsonify({"status": "cooldown_active"}), 429

        last_attempt = now

        print("Starting approved NGINX recovery playbook", flush=True)

        result = subprocess.run(
            [
                "ansible-playbook",
                "-i", "/ansible/inventory.ini",
                "/ansible/recover_nginx.yml",
            ],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )

        print(result.stdout, flush=True)
        if result.stderr:
            print(result.stderr, flush=True)

        if result.returncode != 0:
            return jsonify({"status": "recovery_failed"}), 500

        return jsonify({"status": "playbook_completed"}), 200

    except subprocess.TimeoutExpired:
        print("Recovery playbook timed out", flush=True)
        return jsonify({"status": "recovery_timeout"}), 504

    finally:
        recovery_lock.release()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, threaded=True)
