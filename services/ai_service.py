from Medika_ai import model_core


def run_diagnosis(symptoms, patient_context):
    """
    Central AI service layer (LOCAL MODE).

    - No HTTP requests
    - No database logic
    - Only calls model_core
    """

    if not symptoms:
        return {
            "success": False,
            "error": "Symptoms are required"
        }, 400

    if not patient_context:
        patient_context = {
            "age": None,
            "gender": "",
            "conditions": [],
            "medications": [],
            "allergies": [],
            "past_diagnoses": [],
            "last_visit_reason": ""
        }

    try:
        result = model_core.diagnose(
            symptoms,
            patient=patient_context
        )

        return {
            "success": True,
            "data": result
        }, 200

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }, 500