#!/usr/bin/env python3
import os
import time
import random
import threading
from flask import Flask, request, jsonify, make_response

# ─── config ────────────────────────────────────────────────────────────────

START_TIME = time.time()
MODE       = os.environ.get("MODE", "stable")
VERSION    = os.environ.get("APP_VERSION", "1.0.0")
PORT       = int(os.environ.get("APP_PORT", 3000))

app = Flask(__name__)

# ─── chaos manager ─────────────────────────────────────────────────────────

class ChaosManager:
    def __init__(self):
        self._lock       = threading.Lock()
        self._mode       = None
        self._duration   = 0
        self._error_rate = 0.0
        self._slow_until = 0

    def apply(self, payload: dict) -> dict:
        mode = payload.get("mode")
        with self._lock:
            if mode == "slow":
                duration = int(payload.get("duration", 5))
                self._mode       = "slow"
                self._duration   = duration
                self._slow_until = time.time() + 3600
                return {"chaos": "slow", "duration": duration}

            elif mode == "error":
                rate = float(payload.get("rate", 0.5))
                self._mode       = "error"
                self._error_rate = rate
                return {"chaos": "error", "rate": rate}

            elif mode == "recover":
                self._mode       = None
                self._duration   = 0
                self._error_rate = 0.0
                self._slow_until = 0
                return {"chaos": "recovered"}

            else:
                return {"error": "unknown chaos mode"}

    def get_effect(self):
        with self._lock:
            delay        = 0
            should_error = False
            if self._mode == "slow" and time.time() < self._slow_until:
                delay = self._duration
            elif self._mode == "error":
                should_error = random.random() < self._error_rate
            return delay, should_error


chaos = ChaosManager()

# ─── helpers ───────────────────────────────────────────────────────────────

def add_mode_header(response):
    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    return response


def apply_chaos():
    delay, should_error = chaos.get_effect()
    if delay:
        time.sleep(delay)
    if should_error:
        resp = make_response(jsonify({"error": "chaos error injection"}), 500)
        return add_mode_header(resp)
    return None

# ─── routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    chaos_resp = apply_chaos()
    if chaos_resp:
        return chaos_resp
    resp = make_response(jsonify({
        "message": "Welcome to SwiftDeploy",
        "mode":    MODE,
        "version": VERSION,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }), 200)
    return add_mode_header(resp)


@app.route("/healthz")
def healthz():
    resp = make_response(jsonify({
        "status":         "ok",
        "uptime_seconds": round(time.time() - START_TIME, 2)
    }), 200)
    return add_mode_header(resp)


@app.route("/chaos", methods=["POST"])
def chaos_endpoint():
    if MODE != "canary":
        resp = make_response(jsonify({
            "error": "chaos only available in canary mode"
        }), 403)
        return add_mode_header(resp)

    payload = request.get_json(silent=True)
    if not payload:
        resp = make_response(jsonify({"error": "invalid JSON"}), 400)
        return add_mode_header(resp)

    result = chaos.apply(payload)
    resp = make_response(jsonify(result), 200)
    return add_mode_header(resp)

# ─── entry ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"[swiftdeploy] API running on port {PORT} | mode={MODE} | version={VERSION}")
    app.run(host="0.0.0.0", port=PORT)
