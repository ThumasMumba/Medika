# -*- coding: utf-8 -*-
"""model_core.py
=============
The AI brain. Loaded once by both test_cli.py and app.py.

NEW in this version:
    diagnose() now accepts an optional `patient` dict containing data
    pulled from the database by the backend. It uses that data to:
        - Adjust confidence based on medical history
        - Flag medication interactions
        - Boost severity for patients with relevant existing conditions
        - Personalize advice based on age, gender, allergies

The single function you call:

    result = diagnose("fever headache rash", patient={...})

If no patient dict is passed it works exactly like before.
"""
import re
if True:
    import os, json, joblib

    BASE = os.path.dirname(os.path.abspath(__file__))
    MDL  = os.path.join(BASE, "models")

    # ── Load once at import ───────────────────────────────────────────────────────
    _model_path = os.path.join(MDL, "model.pkl")
    if not os.path.exists(_model_path):
        raise FileNotFoundError(
            "\n  models/model.pkl not found."
            "\n  Run  python train.py  first.\n"
        )

    _model = joblib.load(_model_path)

    with open(os.path.join(BASE, "rules.json"), encoding="utf-8") as f:
        _rules = json.load(f)

    _disease_info = {}
    _info_path = os.path.join(MDL, "disease_info.json")
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

    # ─────────────────────────────────────────────────────────────────────────────
    # PATIENT CONTEXT RULES
    # ─────────────────────────────────────────────────────────────────────────────
    #
    # These dicts tell the AI how to adjust its output when it knows something
    # about the patient from the database.
    #
    # CONDITION_RISK_MAP
    #   If the patient has an existing condition AND the model predicts a related
    #   disease, bump severity up and set refer=True.
    #   Format: "existing condition (lowercase)" -> [list of related predicted diseases]
    #
    CONDITION_RISK_MAP = {
        "diabetes":          ["Fungal infection", "Urinary tract infection", "Hypertension",
                            "Heart attack", "Hypoglycemia"],
        "hypertension":      ["Heart attack", "Paralysis (brain hemorrhage)", "Hypertension"],
        "asthma":            ["Pneumonia", "Bronchial Asthma", "Common Cold", "Influenza"],
        "tuberculosis":      ["Tuberculosis", "Pneumonia"],
        "hiv":               ["Tuberculosis", "Pneumonia", "Fungal infection"],
        "aids":              ["Tuberculosis", "Pneumonia", "Fungal infection"],
        "liver disease":     ["Jaundice", "Hepatitis A", "Hepatitis B", "Alcoholic hepatitis",
                            "Chronic cholestasis"],
        "heart disease":     ["Heart attack", "Hypertension"],
        "kidney disease":    ["Urinary tract infection", "Hypertension"],
        "malaria":           ["Malaria", "Dengue", "Typhoid"],
        "anaemia":           ["Malaria", "Jaundice", "Dengue"],
        "pregnancy":         ["Malaria", "Urinary tract infection", "Hypertension",
                            "Diabetes", "Typhoid"],
    }

    #
    # MEDICATION_DISEASE_MAP
    #   If the patient is on a medication AND the diagnosis or OTC advice would
    #   conflict, add a warning.
    #   Format: "medication keyword (lowercase)" -> [list of disease names to flag]
    #
    MEDICATION_DISEASE_MAP = {
        "metformin":       ["Hypoglycemia"],
        "insulin":         ["Hypoglycemia", "Diabetes"],
        "warfarin":        ["Drug Reaction", "Dengue"],         # bleeding risk
        "aspirin":         ["Dengue", "Peptic ulcer disease"],   # aspirin dangerous in dengue
        "ibuprofen":       ["Peptic ulcer disease", "Dengue"],
        "steroid":         ["Fungal infection", "Tuberculosis", "Diabetes"],
        "prednisolone":    ["Fungal infection", "Tuberculosis", "Diabetes"],
        "antihypertensive":["Hypertension", "Hypoglycemia"],
        "antiretroviral":  ["Tuberculosis", "Drug Reaction"],
        "antimalarial":    ["Malaria", "Drug Reaction"],
    }

    #
    # ALLERGY_OTC_MAP
    #   If the patient is allergic to something and the OTC advice mentions it,
    #   we strip that medicine from the advice and add a warning.
    #
    ALLERGY_OTC_MAP = {
        "paracetamol":  ["paracetamol", "acetaminophen"],
        "ibuprofen":    ["ibuprofen"],
        "aspirin":      ["aspirin"],
        "penicillin":   ["penicillin", "amoxicillin"],
        "sulfa":        ["cotrimoxazole", "sulfamethoxazole"],
        "cotrimoxazole": ["cotrimoxazole"],
        "loratadine":   ["loratadine"],
        "cetirizine":   ["cetirizine"],
    }


    # ─────────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────────

    def _check_red_flag(text: str):
        t = text.lower()
        for flag in RED_FLAGS:
            if flag in t:
                return flag
        return None


    def _normalise_patient(raw: dict) -> dict:
        """
        Accept a loose patient dict from the backend and return a clean version
        with predictable keys and types. Missing fields default to safe values.

        The backend can send any subset of these keys — missing ones are ignored.
        """
        def to_list(val):
            """Turn None / str / list into a clean list of lowercase strings."""
            if not val:
                return []
            if isinstance(val, str):
                return [val.lower().strip()]
            return [str(v).lower().strip() for v in val if v]

        age = raw.get("age") or raw.get("patient_age")
        try:
            age = int(age)
        except (TypeError, ValueError):
            age = None

        return {
            "age":             age,
            "gender":          str(raw.get("gender", "")).upper()[:1],   # "M" or "F" or ""

            # Lists — backend sends whatever column names it uses
            "conditions":  to_list(raw.get("conditions")  or raw.get("medical_history")
                                    or raw.get("existing_conditions")),
            "medications": to_list(raw.get("medications") or raw.get("current_medications")),
            "allergies":   to_list(raw.get("allergies")),

            # Past diagnoses — list of disease name strings
            "past_diagnoses": to_list(raw.get("past_diagnoses") or raw.get("diagnosis_history")),

            # Last appointment reason — single string
            "last_visit_reason": str(raw.get("last_visit_reason") or "").lower().strip(),
        }


    def _apply_patient_context(disease: str, action: str, advice: str,
                                severity: str, refer: bool, otc: str,
                                patient: dict) -> dict:
        """
        Takes the base ML output and adjusts it using the patient's data.
        Returns a dict of overrides + a list of context notes shown to the patient.
        """
        notes    = []   # plain-English notes added to the response
        warnings = []   # medical warnings (allergy conflicts, drug interactions)

        # ── Age adjustments ───────────────────────────────────────────────────────
        age = patient["age"]
        if age is not None:
            if age < 5:
                refer   = True
                action  = max_action(action, "clinic")
                notes.append("Children under 5 should always be seen by a doctor regardless of severity.")
            elif age < 12:
                notes.append("For children, consult a doctor before giving any medication.")
            elif age > 65 and action == "otc":
                refer   = True
                action  = "clinic"
                notes.append("Patients over 65 are advised to consult a doctor even for mild symptoms.")

        # ── Gender adjustments ─────────────────────────────────────────────────────
        gender = patient["gender"]
        if gender == "F":
            if disease in ["Urinary tract infection"]:
                notes.append("UTIs are more common in women. Drink plenty of water and seek antibiotic treatment promptly.")
            if disease in ["Malaria", "Typhoid", "Hypertension", "Diabetes"]:
                notes.append("If you are or may be pregnant, seek medical attention immediately — this condition requires careful management during pregnancy.")

        # ── Existing conditions risk boost ────────────────────────────────────────
        for condition in patient["conditions"]:
            related = CONDITION_RISK_MAP.get(condition, [])
            if disease in related:
                # Patient has a condition that makes this disease more dangerous
                if severity == "mild":
                    severity = "moderate"
                if severity == "moderate":
                    severity = "high"
                    refer    = True
                    action   = max_action(action, "clinic")
                notes.append(
                    f"Your existing condition ({condition.title()}) means {disease} "
                    f"may affect you more seriously. Medical review is recommended."
                )

        # ── Past diagnosis — same disease recurring ───────────────────────────────
        for past in patient["past_diagnoses"]:
            if past.lower() == disease.lower():
                notes.append(
                    f"You have been diagnosed with {disease} before. "
                    f"If symptoms are similar to your previous episode, inform your doctor."
                )
                # Recurring serious disease → always refer
                if action == "otc" and disease.lower() in REFER_HOSPITAL + REFER_CLINIC:
                    refer  = True
                    action = "clinic"
                break

        # ── Medication interactions ────────────────────────────────────────────────
        for med in patient["medications"]:
            for keyword, flagged_diseases in MEDICATION_DISEASE_MAP.items():
                if keyword in med and disease in flagged_diseases:
                    warnings.append(
                        f"You are taking {med} — this may interact with or complicate {disease}. "
                        f"Inform your doctor about your current medications."
                    )
                    refer  = True
                    action = max_action(action, "clinic")

        # ── Allergy check against OTC advice ──────────────────────────────────────
        for allergy in patient["allergies"]:
            for allergen, keywords in ALLERGY_OTC_MAP.items():
                if allergen in allergy:
                    for kw in keywords:
                        if kw in otc.lower():
                            warnings.append(
                                f"WARNING: You are allergic to {allergen}. "
                                f"Do NOT take any medicine containing {allergen}. "
                                f"Ask a pharmacist for a safe alternative."
                            )
                            # Remove the allergen mention from OTC advice
                            otc = otc.replace(allergen.title(), f"[AVOID: {allergen} — ALLERGIC]")
                            otc = otc.replace(allergen, f"[AVOID: {allergen} — ALLERGIC]")

        # ── Last visit reason — flag if same symptom pattern recurring ────────────
        last = patient["last_visit_reason"]
        if last and any(word in last for word in disease.lower().split()):
            notes.append(
                f"Your last appointment was also related to {last}. "
                f"If symptoms are recurring, your doctor should know."
            )

        return {
            "severity":  severity,
            "action":    action,
            "refer":     refer,
            "otc":       otc,
            "notes":     notes,
            "warnings":  warnings,
        }
    


    def max_action(current: str, minimum: str) -> str:
        """
        Returns whichever action is more urgent.
        Order: otc < clinic < hospital < emergency
        """
        order = ["otc", "clinic", "hospital", "emergency"]
        ci = order.index(current)  if current  in order else 0
        mi = order.index(minimum)  if minimum  in order else 0
        return order[max(ci, mi)]
    

# Canonical symptom -> possible user phrases
    SYMPTOM_MAP = {
        "high fever": [
            "high fever",
            "high temperature",
            "burning body",
            "very hot",
            "hot body"
        ],

        "fever": [
            "fever",
            "temperature",
            "hot"
        ],

        "headache": [
            "headache",
            "head pain",
            "migraine",
            "pressure in head",
            "head hurts"
        ],

        "cough": [
            "cough",
            "dry cough",
            "chest cough",
            "persistent cough"
        ],

        "fatigue": [
            "fatigue",
            "weak",
            "tired",
            "exhausted",
            "low energy"
        ],

        "skin rash": [
            "rash",
            "skin rash",
            "itchy rash",
            "red rash"
        ],

        "vomiting": [
            "vomiting",
            "throwing up",
            "throwing-up",
            "vomit"
        ],

        "nausea": [
            "nausea",
            "feeling sick",
            "queasy"
        ]
        }
        
    # A preprocessing function to expand common symptom phrases into standardized tokens
    def expand_symptoms(text: str) -> str:

        text = text.lower()

        # Remove conversational phrases
        fillers = [
            "i have",
            "i've",
            "i am",
            "i'm",
            "i feel",
            "i am feeling",
            "feeling",
            "been having",
            "suffering from",
            "experiencing",
            "my symptoms are",
            "it feels like",
            "there is",
            "having"
        ]

        for phrase in fillers:
            text = text.replace(phrase, " ")

        # Replace synonyms with canonical symptoms
        for canonical, synonyms in SYMPTOM_MAP.items():
            for synonym in synonyms:
                text = text.replace(synonym, canonical)

        # Remove punctuation
        text = re.sub(r"[^a-z ]", " ", text)

        # Remove duplicate words
        words = []
        for word in text.split():
            if word not in words:
                words.append(word)

        return " ".join(words)
    # ─────────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────────────

    def diagnose(symptom_text: str, patient: dict = None) -> dict:
        """
        Run a full diagnosis, optionally personalized with patient DB data.

        Parameters
        ----------
        symptom_text : str
            Plain-text symptom description, e.g. "fever headache skin rash".

        patient : dict, optional
            Patient data from the database, passed by the backend.
            Any subset of these keys is accepted (all are optional):

                age               int     e.g. 34
                gender            str     "M" or "F"
                conditions        list    ["diabetes", "hypertension"]
                medications       list    ["metformin 500mg", "aspirin 75mg"]
                allergies         list    ["penicillin", "ibuprofen"]
                past_diagnoses    list    ["Malaria", "Urinary tract infection"]
                last_visit_reason str     "fever and joint pain"

            Missing keys are ignored safely — no crash.

        Returns
        -------
        dict:
            disease          str    Predicted disease name
            confidence       float  0.0 – 1.0
            action           str    "otc" | "clinic" | "hospital" | "emergency"
            advice           str    Plain-English advice for the patient
            otc              str    OTC medicine suggestion (empty if hospital/emergency)
            description      str    Disease description from dataset
            precautions      list   Precaution strings from dataset
            refer            bool   True if patient should see a doctor
            context_notes    list   Personalized notes based on patient history
            warnings         list   Allergy / drug interaction warnings
            patient_summary  dict   What the AI knew about the patient
            disclaimer       str    Safety notice (always present)
        """

        # ── Empty input ────────────────────────────────────────────────────────────
        if not symptom_text or not symptom_text.strip():
            return {
                "disease": "No symptoms provided", "confidence": 0.0,
                "action": "otc", "advice": "Please describe your symptoms.",
                "otc": "", "description": "", "precautions": [],
                "refer": False, "context_notes": [], "warnings": [],
                "patient_summary": {}, "disclaimer": DISCLAIMER,
            }

     
        
        # ── Red flag check — always first ────────────────────────────────────────
        flag = _check_red_flag(symptom_text)
        if flag:
            return {
                "disease": "Urgent symptom detected", "confidence": 1.0,
                "action": "emergency",
                "advice": (
                    f"You mentioned '{flag}'. This may be a medical emergency. "
                    "Go to the nearest hospital immediately. Do not wait."
                ),
                "otc": "",
                "description": "A potentially serious symptom was detected.",
                "precautions": [
                    "Go to the nearest hospital or emergency room now",
                    "Do not drive yourself if you feel unwell",
                    "Call emergency services if available",
                ],
                "refer": True,
                "context_notes": [],
                "warnings": [],
                "patient_summary": {},
                "disclaimer": DISCLAIMER,
            }

        # Simple symptom map (used elsewhere in the module)

        # ── ML prediction ──────────────────────────────────────────────────────────

        clean = expand_symptoms(symptom_text)
        proba = _model.predict_proba([clean])[0]
        classes = _model.classes_

        top_i = proba.argmax()

        disease = classes[top_i]

        top_prob = float(proba[top_i])
        sorted_probs = sorted(proba, reverse=True)
        second_prob = sorted_probs[1] if len(sorted_probs) > 1 else 0.0

        margin = top_prob - second_prob

        ai_confidence_level = (
            "high" if top_prob > 0.75 else
            "medium" if top_prob > 0.5 else
            "low"
        )

        # ── TOP 3 PREDICTIONS ───────────────────────────────────────────
        top3_idx = proba.argsort()[-3:][::-1]

        top3 = [
            {
                "disease": classes[i],
                "confidence": round(float(proba[i]), 3)
            }
            for i in top3_idx
        ]

        # ── UNCERTAIN LOGIC (FIXED) ─────────────────────────────────────
        low_confidence = top_prob < 0.35 or margin < 0.10

        if low_confidence:
            return {
                "disease": "Uncertain",
                "confidence": round(top_prob, 3),
                "action": "clinic",

                "advice": (
                    "We could not confidently determine a condition. "
                    "The most likely possibilities are: "
                    + ", ".join([t["disease"] for t in top3]) +
                    ". Please visit a clinic for proper evaluation."
                ),

                "otc": "",
                "description": "",
                "precautions": [],

                "refer": True,

                "context_notes": [],
                "warnings": [],

                "top_predictions": top3,

                "patient_summary": {},
                "disclaimer": DISCLAIMER,
                "ai_confidence_level": ai_confidence_level
            }

        # ── Base action from rules.json ────────────────────────────────────────────
        d_lower = disease.lower()

        if d_lower in REFER_HOSPITAL:
            action  = "hospital"
            otc     = ""
            advice  = (
                f"Based on your symptoms, this may be {disease}. "
                "This condition requires medical attention at a hospital or clinic. "
                "Please go as soon as possible."
            )
            refer   = True

        elif d_lower in REFER_CLINIC:
            action  = "clinic"
            otc     = OTC_ADVICE.get(disease, "")
            advice  = (
                f"Based on your symptoms, this may be {disease}. "
                "We recommend seeing a doctor at a clinic."
            )
            if otc:
                advice += f" In the meantime: {otc}"
            refer   = True

        else:
            action  = "otc"
            otc     = OTC_ADVICE.get(disease, OTC_ADVICE["Default"])
            advice  = f"Based on your symptoms, this may be {disease}. {otc}"
            refer = action in ["clinic", "hospital", "emergency"]

        severity = "high" if action == "hospital" else ("moderate" if action == "clinic" else "mild")

        # ── Dataset enrichment ─────────────────────────────────────────────────────
        info        = _disease_info.get(disease, {})
        description = info.get("description", "")
        precautions = info.get("precautions", [])

        # ── Patient context adjustments ────────────────────────────────────────────
        context_notes = []
        warnings      = []
        patient_summary = {}

        if patient:
            p = _normalise_patient(patient)

            # Build a summary of what the AI actually used
            patient_summary = {
                "age":          p["age"],
                "gender":       p["gender"] or "not provided",
                "conditions":   p["conditions"],
                "medications":  p["medications"],
                "allergies":    p["allergies"],
                "past_diagnoses": p["past_diagnoses"],
            }

            overrides = _apply_patient_context(
                disease, action, advice, severity, refer, otc, p
            )

            # Apply any overrides from patient context
            severity      = overrides["severity"]
            action        = overrides["action"]
            refer         = overrides["refer"]
            otc           = overrides["otc"]
            context_notes = overrides["notes"]
            warnings      = overrides["warnings"]

            # Rebuild advice if action was escalated by patient context
            if action == "hospital" and refer:
                advice = (
                    f"Based on your symptoms and medical history, this may be {disease}. "
                    "Given your health background, a hospital visit is strongly recommended."
                )
            elif action == "clinic" and refer and "otc" in advice.lower():
                advice = (
                    f"Based on your symptoms and medical history, this may be {disease}. "
                    "Please see a doctor at a clinic."
                )
                

        return {
            "disease":         disease,
            "confidence":      round(top_prob, 3),
            "action":          action,
            "advice":          advice,
            "otc":             otc,
            "description":     description,
            "precautions":     precautions,
            "refer":           refer,
            "context_notes":   context_notes,     # personalized notes from patient data
            "warnings":        warnings,           # allergy / drug interaction alerts
            "patient_summary": patient_summary,    # what the AI knew about the patient
            "disclaimer":      DISCLAIMER,
        }

    
    def model_info() -> dict:
        return {
            "status":     "ok",
            "accuracy":   _meta.get("accuracy", 0),
            "n_diseases": _meta.get("n_diseases", 0),
        }
