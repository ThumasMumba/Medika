# -*- coding: utf-8 -*-
"""
test_cli.py
===========
Terminal tester — test the AI model without running Flask or a backend.

Run:
    python test_cli.py

Modes:
    1 - Type symptoms manually (with optional patient details)
    2 - Run built-in test suite
    3 - Quit
"""

import textwrap
import model_core
# ── Terminal colors (work on Windows 10+, Linux, Mac) ────────────────────────

R = "\033[91m"; G = "\033[92m"; Y = "\033[93m"
B = "\033[94m"; C = "\033[96m"; W = "\033[1m"; X = "\033[0m"

ACTION_LABEL = {
    "otc":       G  + "HOME TREATMENT" + X,
    "clinic":    Y  + "VISIT CLINIC"   + X,
    "hospital":  R  + "GO TO HOSPITAL" + X,
    "emergency": R+W + "!! EMERGENCY !!" + X,
}


def print_result(result: dict):
    print("\n" + C + "─"*58 + X)
    print(f"  {W}Condition :{X} {W}{result['disease']}{X}")
    print(f"  {W}Confidence:{X} {result['confidence']:.0%}")
    print(f"  {W}Action    :{X} {ACTION_LABEL.get(result['action'], result['action'])}")
    print(f"  {W}Refer     :{X} {'Yes' if result['refer'] else 'No'}")
    print()

    print(f"  {W}Advice:{X}")
    for line in textwrap.wrap(result["advice"], 54):
        print(f"    {line}")

    if result.get("otc"):
        print()
        print(f"  {W}OTC medicine:{X}")
        for line in textwrap.wrap(result["otc"], 54):
            print(f"    {line}")

    # Personalized notes from patient history
    if result.get("context_notes"):
        print()
        print(f"  {W}Notes from your medical history:{X}")
        for note in result["context_notes"]:
            for line in textwrap.wrap(note, 52):
                print(f"    - {line}")

    # Allergy / drug interaction warnings
    if result.get("warnings"):
        print()
        print(f"  {R}{W}WARNINGS:{X}")
        for warn in result["warnings"]:
            for line in textwrap.wrap(warn, 52):
                print(f"  {R}  ! {line}{X}")

    if result.get("description"):
        print()
        print(f"  {W}About this condition:{X}")
        for line in textwrap.wrap(result["description"], 54):
            print(f"    {line}")

    if result.get("precautions"):
        print()
        print(f"  {W}Precautions:{X}")
        for p in result["precautions"]:
            print(f"    - {p}")

    if result.get("patient_summary") and any(result["patient_summary"].values()):
        ps = result["patient_summary"]
        print()
        print(f"  {W}Patient context used:{X}")
        if ps.get("age"):        print(f"    Age        : {ps['age']}")
        if ps.get("gender"):     print(f"    Gender     : {ps['gender']}")
        if ps.get("conditions"): print(f"    Conditions : {', '.join(ps['conditions'])}")
        if ps.get("medications"):print(f"    Medications: {', '.join(ps['medications'])}")
        if ps.get("allergies"):  print(f"    Allergies  : {', '.join(ps['allergies'])}")
        if ps.get("past_diagnoses"): print(f"    Past dx    : {', '.join(ps['past_diagnoses'])}")

    print()
    print(f"  {Y}{DISCLAIMER_SHORT}{X}")
    print(C + "─"*58 + X + "\n")

DISCLAIMER_SHORT = "AI assessment only — always consult a healthcare professional."


# ── Built-in test cases ───────────────────────────────────────────────────────
# Each case has: (label, symptoms, patient_dict, expected_action)
# patient_dict=None means test without any patient context
TESTS = [
    # ── Basic cases (no patient context) ──────────────────────────────────────
    ("Fungal infection — OTC",
     "itching skin rash nodal skin eruptions",
     None, "otc"),

    ("Common cold — OTC",
     "continuous sneezing chills fatigue cough headache",
     None, "otc"),

    ("Malaria — Hospital",
     "chills vomiting high fever sweating headache",
     None, "hospital"),

    ("Typhoid — Hospital",
     "chills vomiting fatigue weight loss nausea",
     None, "hospital"),

    ("UTI — Clinic",
     "burning micturition bladder discomfort foul urine",
     None, "clinic"),

    ("Tuberculosis — Hospital",
     "chills vomiting fatigue cough high fever weight loss",
     None, "hospital"),

    ("Red flag — Emergency",
     "chest pain difficulty breathing sweating",
     None, "emergency"),

    ("Low confidence — Clinic",
     "tired sometimes",
     None, "clinic"),

    # ── Patient context cases ─────────────────────────────────────────────────
    ("Fungal infection + DIABETES → escalate to clinic",
     "itching skin rash nodal skin eruptions",
     {"age": 52, "gender": "M",
      "conditions": ["diabetes"],
      "medications": ["metformin 500mg"],
      "allergies": [],
      "past_diagnoses": []},
     "clinic"),                           # diabetes escalates fungal from OTC -> clinic

    ("UTI + PREGNANCY warning",
     "burning micturition bladder discomfort foul urine",
     {"age": 26, "gender": "F",
      "conditions": ["pregnancy"],
      "medications": [],
      "allergies": [],
      "past_diagnoses": ["Urinary tract infection"]},
     "clinic"),                           # recurring UTI in pregnant woman

    ("Malaria + ASPIRIN allergy warning",
     "chills high fever sweating headache",
     {"age": 30, "gender": "M",
      "conditions": [],
      "medications": ["aspirin 75mg"],
      "allergies": ["aspirin"],
      "past_diagnoses": []},
     "hospital"),                         # aspirin allergy warning added

    ("Child under 5 — auto escalate",
     "continuous sneezing runny nose mild fever",
     {"age": 3, "gender": "F",
      "conditions": [],
      "medications": [],
      "allergies": [],
      "past_diagnoses": []},
     "clinic"),                           # child < 5 always sent to clinic

    ("Elderly patient — mild escalated",
     "itching skin rash fatigue",
     {"age": 70, "gender": "M",
      "conditions": [],
      "medications": [],
      "allergies": [],
      "past_diagnoses": []},
     "clinic"),                           # over 65 → OTC becomes clinic

    ("Hypertension + Heart attack risk",
     "fatigue dizziness breathlessness chest discomfort",
     {"age": 58, "gender": "M",
      "conditions": ["hypertension", "diabetes"],
      "medications": ["antihypertensive", "metformin"],
      "allergies": ["ibuprofen"],
      "past_diagnoses": ["Hypertension"]},
     "hospital"),
]


def run_tests():
    print(f"\n{W}Running {len(TESTS)} test cases ...{X}\n")
    passed = failed = 0

    for label, symptoms, patient, expected in TESTS:
        result = model_core.diagnose(symptoms, patient=patient)
        ok     = result["action"] == expected
        status = G+"PASS"+X if ok else R+"FAIL"+X
        passed += ok; failed += (not ok)

        ctx = " [with patient context]" if patient else ""
        print(f"  [{status}]  {label}{ctx}")
        print(f"          Predicted : {result['disease']}  ({result['confidence']:.0%})")
        print(f"          Action    : {result['action']}  (expected: {expected})")
        if result.get("warnings"):
            for w in result["warnings"]:
                print(f"          {R}Warning: {w[:70]}...{X}")
        if result.get("context_notes"):
            for n in result["context_notes"]:
                print(f"          Note: {n[:70]}")
        if not ok:
            print(f"          {R}>>> MISMATCH{X}")
        print()

    print("─"*58)
    print(f"  {G}{passed} passed{X}  /  {R}{failed} failed{X}  /  {len(TESTS)} total\n")


# ── Interactive mode ───────────────────────────────────────────────────────────
def interactive():
    info = model_core.model_info()
    print(f"\n{C}{W}{'='*58}{X}")
    print(f"{C}{W}  MEDIKA AI — Terminal Tester{X}")
    print(f"  Accuracy: {info['accuracy']:.2%}  |  Diseases: {info['n_diseases']}")
    print(f"{C}{W}{'='*58}{X}\n")

    while True:
        print("  1  Enter symptoms (+ optional patient details)")
        print("  2  Run full test suite")
        print("  3  Quit")
        choice = input("\n  Choice: ").strip()

        if choice == "1":
            print()
            symptoms = input("  Symptoms: ").strip()
            if not symptoms:
                print("  Nothing entered.\n"); continue

            # Ask for patient details
            print(f"\n  {W}Patient details (all optional — press Enter to skip){X}")
            age_s  = input("  Age: ").strip()
            gender = input("  Gender M/F: ").strip().upper()[:1]
            conds  = input("  Existing conditions (comma-separated): ").strip()
            meds   = input("  Current medications (comma-separated): ").strip()
            allgs  = input("  Allergies (comma-separated): ").strip()
            past   = input("  Past diagnoses (comma-separated): ").strip()

            patient = None
            has_data = any([age_s, gender, conds, meds, allgs, past])
            if has_data:
                patient = {
                    "age":           int(age_s) if age_s.isdigit() else None,
                    "gender":        gender,
                    "conditions":    [c.strip() for c in conds.split(",") if c.strip()],
                    "medications":   [m.strip() for m in meds.split(",")  if m.strip()],
                    "allergies":     [a.strip() for a in allgs.split(",") if a.strip()],
                    "past_diagnoses":[d.strip() for d in past.split(",")  if d.strip()],
                }

            result = model_core.diagnose(symptoms, patient=patient)
            print_result(result)

        elif choice == "2":
            run_tests()
        elif choice == "3":
            print("\n  Goodbye!\n"); break
        else:
            print("  Enter 1, 2, or 3.\n")


if __name__ == "__main__":
    interactive()
