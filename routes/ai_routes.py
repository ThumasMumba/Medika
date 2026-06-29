from flask import Blueprint, request, jsonify, session

from services.patient_service import build_patient_context
from services.ai_service import run_diagnosis
from services.referral_services import create_referral

ai_app = Blueprint('ai_app', __name__)


@ai_app.route("/diagnose", methods=["POST"])
def diagnose():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    symptoms = str(data.get("symptoms", "")).strip()

    patient_id = session.get("patient_id")

    if not patient_id:
        return jsonify({"error": "Unauthorized"}), 401

    # 1. Build context
    patient_context = build_patient_context(patient_id)

    # 2. Run AI
    result, status = run_diagnosis(symptoms, patient_context)

    # If AI failed
    if not result.get("success"):
        return jsonify(result), status

    ai_data = result["data"]

    action = ai_data.get("action", "otc")

    # 3. Handle referral logic
    if action == "hospital":
        success = create_referral(
            patient_id=patient_id,
            disease=ai_data.get("disease", ""),
            reason=symptoms,
            urgency="urgent"
        )

        ai_data["referral_created"] = success

    elif action == "clinic":
        ai_data["suggest_booking"] = True
        ai_data["booking_reason"] = ai_data.get("disease", "")

    elif action == "emergency":
        ai_data["emergency_alert"] = True

    print("INPUT:", symptoms)
    print("OUTPUT:", ai_data)
    print("AI ROUTE HIT")
    return jsonify(result), status