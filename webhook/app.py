import os
import urllib.error
import urllib.request
import json

from flask import Flask, jsonify, request

app = Flask(__name__)

RECOVERY_URL = "http://recovery:5001/recover"
RECOVERY_TOKEN = os.environ["RECOVERY_TOKEN"]


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "self-healing-webhook"
    }), 200


@app.route("/alert", methods=["POST"])
def receive_alert():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    # Only process firing notifications.
    if payload.get("status") != "firing":
        return jsonify({"status": "ignored", "reason": "not firing"}), 200

    alerts = payload.get("alerts")
    if not isinstance(alerts, list):
        return jsonify({"error": "Invalid alerts list"}), 400

    # Accept only our approved NGINX failure alert.
    approved = any(
        isinstance(alert, dict)
        and alert.get("status") == "firing"
        and isinstance(alert.get("labels"), dict)
        and alert["labels"].get("alertname") == "NginxServiceDown"
        and alert["labels"].get("service") == "nginx"
        and alert["labels"].get("severity") == "critical"
        for alert in alerts
    )

    if not approved:
        return jsonify({"status": "ignored", "reason": "no approved alert"}), 200

    print("Approved NGINX failure alert received", flush=True)

    recovery_request = urllib.request.Request(
        RECOVERY_URL,
        data=json.dumps({"service": "nginx"}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Recovery-Token": RECOVERY_TOKEN
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(recovery_request, timeout=50) as response:
            result = response.read().decode("utf-8")
            print(f"Recovery API response: {result}", flush=True)
            return jsonify({"status": "recovery_requested"}), 200

    except urllib.error.HTTPError as error:
        print(f"Recovery API returned HTTP {error.code}", flush=True)

        # A recovery already running or in cooldown needs no new attempt.
        if error.code in (409, 429):
            return jsonify({"status": "recovery_suppressed"}), 200

        return jsonify({"status": "recovery_failed"}), 502

    except (urllib.error.URLError, TimeoutError) as error:
        print(f"Recovery API connection failed: {error}", flush=True)
        return jsonify({"status": "recovery_unavailable"}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
