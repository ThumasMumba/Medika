# -*- coding: utf-8 -*-
"""
model_core.py
=============
The brain of the AI module. Loaded once by both test_cli.py and app.py.
You never call this file directly — just import it.

The single function you care about:

    result = diagnose("itching skin rash fever")

It returns a plain dict with everything the frontend or backend needs.
"""

import os, json, joblib

BASE = os.path.dirname(os.path.abspath(__file__))
MDL  = os.path.join(BASE, "models")

# ── Load model and support files once at import time ─────────────────────────

_model_path = os.path.join(MDL, "model.pkl")
if not os.path.exists(_model_path):
    raise FileNotFoundError(
        "\n  models/model.pkl not found."
        "\n  Run  python train.py  first.\n"
    )

_model = joblib.load(_model_path)

with open(os.path.join(BASE, "rules.json"), encoding="utf-8") as f:
    _rules = json.load(f)

_info_path = os.path.join(MDL, "disease_info.json")
_disease_info = {}
if os.path.exists(_info_path):
    with open(_info_path, encoding="utf-8") as f:
        _disease_info = json.load(f)

with open(os.path.join(MDL, "meta.json"), encoding="utf-8") as f:
    _meta = json.load(f)

REFER_HOSPITAL = [d.lower() for d in _rules["refer_to_hospital"]]
REFER_CLINIC   = [d.lower() for d in _rules["refer_to_clinic"]]
OTC_ADVICE     = _rules["otc_advice"]
RED_FLAGS      = [r.lower() for r in _rules["red_flags"]]

DISCLAIMER = (
    "This is an AI-assisted preliminary assessment, not a medical diagnosis. "
    "Always consult a qualified healthcare professional."
)
SYMPTOM_ALIASES = {
    "fever": "high fever",
    "temperature": "high fever",
    "headache": "headache",
    "head hurts": "headache",
    "cough": "cough",
    "rash": "skin rash",
    "itchy": "itching",
    "itching": "itching",
    "stomach pain": "abdominal pain",
    "belly pain": "abdominal pain",
}

def normalize_symptoms(text: str) -> str:
    text = text.lower()

    found = []

    for phrase, symptom in SYMPTOM_ALIASES.items():
        if phrase in text:
            found.append(symptom)

    return " ".join(found)

# ── Red flag check ─────────────────────────────────────────────────────────────
def _check_red_flag(text: str):
    """Return the matched phrase if a red-flag symptom is found, else None."""
    t = text.lower()
    for flag in RED_FLAGS:
        if flag in t:
            return flag
    return None


# ── Main diagnose function ────────────────────────────────────────────────────
def diagnose(symptom_text: str) -> dict:
    """
    Run a diagnosis on plain-text symptom input.

    Parameters
    ----------
    symptom_text : str
        What the patient types, e.g. "I have a fever, headache and rash"

    Returns
    -------
    dict with these keys:
        disease          - predicted disease name  (str)
        confidence       - model confidence 0.0-1.0  (float)
        action           - "otc" | "clinic" | "hospital" | "emergency"
        advice           - plain-English sentence for the patient  (str)
        description      - short description of the disease  (str)
        precautions      - list of precaution strings  (list)
        refer            - True if patient should see a doctor  (bool)
        disclaimer       - always-present safety notice  (str)
    """
    
    # ── Empty input ──────────────────────────────────────────────────────────
    if not symptom_text or not symptom_text.strip():
        return {
            "disease":     "No symptoms provided",
            "confidence":  0.0,
            "action":      "otc",
            "advice":      "Please describe your symptoms so we can help.",
            "description": "",
            "precautions": [],
            "refer":       False,
            "disclaimer":  DISCLAIMER,
        }
  

    # ── Red flag check — always runs first ───────────────────────────────────
    # If the patient mentions something serious like "chest pain" or
    # "difficulty breathing", we skip the ML model entirely and send
    # them to hospital immediately.
    flag = _check_red_flag(symptom_text)
    if flag:
        return {
            "disease":     "Urgent symptom detected",
            "confidence":  1.0,
            "action":      "emergency",
            "advice":      (
                f"You mentioned '{flag}'. This may be a medical emergency. "
                "Go to the nearest hospital immediately. Do not wait."
            ),
            "description": "A potentially serious symptom was detected.",
            "precautions": [
                "Go to the nearest hospital or emergency room now",
                "Do not drive yourself if you feel unwell",
                "Call for help if available",
            ],
            "refer":       True,
            "disclaimer":  DISCLAIMER,
        }

    # ── ML prediction ────────────────────────────────────────────────────────
    # Clean the input: lowercase, replace underscores
    clean = normalize_symptoms(symptom_text)
    #Fall back
    if not clean:
        clean = symptom_text.lower()

    # Get confidence scores for every disease
    proba   = _model.predict_proba([clean])[0]
    classes = _model.classes_
    top_i   = proba.argmax()
    disease    = classes[top_i]
    confidence = float(proba[top_i])
    # For debugging: print the top 5 predictions with their confidence scores
    # top5 = sorted(
    #     zip(classes, proba),
    #     key=lambda x: x[1],
    #     reverse=True
    # )[:5]

    # print("\nTop predictions:")
    # for disease, score in top5:
    #     print(f"{disease}: {score:.3f}")
    # If the model is not confident enough, give a safe generic response
    if confidence < 0.10:
        return {
            "disease":     "Uncertain",
            "confidence":  round(confidence, 3),
            "action":      "clinic",
            "advice":      (
                "Your symptoms are not clear enough for a confident assessment. "
                "Please visit a clinic so a doctor can examine you properly."
            ),
            "description": "",
            "precautions": [],
            "refer":       True,
            "disclaimer":  DISCLAIMER,
        }

    # ── Decide action based on rules.json ────────────────────────────────────
    # Three possible actions:
    #   "hospital" - serious disease, needs hospital
    #   "clinic"   - needs a doctor but not emergency
    #   "otc"      - manageable at home with pharmacy medicine
    d_lower = disease.lower()

    if d_lower in REFER_HOSPITAL:
        action = "hospital"
        advice = (
            f"Based on your symptoms, this may be {disease}. "
            "This condition requires medical attention. "
            "Please go to a hospital or clinic as soon as possible."
        )
        refer  = True

    elif d_lower in REFER_CLINIC:
        action = "clinic"
        advice = (
            f"Based on your symptoms, this may be {disease}. "
            "We recommend booking an appointment with a doctor or visiting a clinic."
        )
        # Append OTC tip if available for clinic-level disease
        otc = OTC_ADVICE.get(disease, "")
        if otc:
            advice += f" In the meantime: {otc}"
        refer  = True

    else:
        action = "otc"
        otc    = OTC_ADVICE.get(disease, OTC_ADVICE["Default"])
        advice = (
            f"Based on your symptoms, this may be {disease}. "
            f"{otc}"
        )
        refer  = False

    # ── Enrich with description and precautions from the dataset ─────────────
    info        = _disease_info.get(disease, {})
    description = info.get("description", "")
    precautions = info.get("precautions", [])

    return {
        "disease":     disease,
        "confidence":  round(confidence, 3),
        "action":      action,         # tells backend what referral to make
        "advice":      advice,
        "description": description,
        "precautions": precautions,
        "refer":       refer,
        "disclaimer":  DISCLAIMER,
    }


def model_info() -> dict:
    """Return basic metadata about the loaded model (used by /health endpoint)."""
    return {
        "status":     "ok",
        "accuracy":   _meta.get("accuracy", 0),
        "n_diseases": _meta.get("n_diseases", 0),
    }
