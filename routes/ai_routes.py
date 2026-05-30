# -*- coding: utf-8 -*-
"""
app.py
======
Flask REST API for the MEDIKA AI service.
The backend (port 5000) sends requests here (port 5001).
The frontend never talks to this directly.

Run:
    python app.py

Endpoints:
    POST /diagnose    accepts JSON symptoms, returns diagnosis
    GET  /health      returns model status (backend pings this on startup)
"""

from flask import Blueprint,  request, jsonify
from Medika_ai import model_core

ai_app = Blueprint('ai_app', __name__)  # allow the backend to call this from a different port


# ── POST /diagnose ─────────────────────────────────────────────────────────────
# This is the only endpoint the backend needs to call.
#
# Request JSON:
#   { "symptoms": "fever headache skin rash" }
#
# Response JSON: everything from model_core.diagnose()
#   {
#     "disease":      "Malaria",
#     "confidence":   0.91,
#     "action":       "hospital",    <-- backend uses this to trigger referral
#     "advice":       "...",
#     "description":  "...",
#     "precautions":  ["...", "..."],
#     "refer":        true,
#     "disclaimer":   "..."
#   }
#
# The "action" field tells the backend what to do:
#   "otc"       -> show OTC advice, no referral needed
#   "clinic"    -> backend creates a clinic appointment booking
#   "hospital"  -> backend creates a hospital referral
#   "emergency" -> backend shows emergency alert + nearest hospital

@ai_app.route("/diagnose", methods=["POST"])
def diagnose():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    symptoms = str(data.get("symptoms", "")).strip()

    if not symptoms:
        return jsonify({"error": "'symptoms' field is required"}), 400

    result = model_core.diagnose(symptoms)
    print("INPUT:", symptoms)
    print("OUTPUT:", result)
    return jsonify(result), 200


# ── GET /health ────────────────────────────────────────────────────────────────
# Backend should call this on startup to confirm the AI service is running.
@ai_app.route("/health", methods=["GET"])
def health():
    return jsonify(model_core.model_info()), 200


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*50)
    print("  MEDIKA AI Service")
    print("  http://localhost:5001")
    print("  POST /diagnose   GET /health")
    print("="*50 + "\n")
    ai_app.run(host="0.0.0.0", port=5001, debug=True)
