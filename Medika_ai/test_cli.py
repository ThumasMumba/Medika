# -*- coding: utf-8 -*-
"""
test_cli.py
===========
Test the AI model in the terminal WITHOUT running Flask or connecting
any backend. This is your main testing tool during development.

Run:
    python test_cli.py

Two modes:
    1 - Type your own symptoms interactively
    2 - Run the built-in test suite (covers all action types)
"""

import textwrap
import model_core   # loads the model

# ── Terminal colours (work on Windows 10+, Linux, Mac) ────────────────────────
R  = "\033[91m"   # red
G  = "\033[92m"   # green
Y  = "\033[93m"   # yellow
B  = "\033[94m"   # blue
C  = "\033[96m"   # cyan
W  = "\033[1m"    # bold
X  = "\033[0m"    # reset

ACTION_COLOUR = {
    "otc":       G + "HOME TREATMENT",
    "clinic":    Y + "VISIT CLINIC",
    "hospital":  R + "GO TO HOSPITAL",
    "emergency": R + W + "!! EMERGENCY !!",
}


def print_result(result: dict):
    """Print a diagnosis result in a readable format."""
    print("\n" + C + "─"*55 + X)

    action_label = ACTION_COLOUR.get(result["action"], result["action"]) + X
    print(f"  {W}Condition :{X} {W}{result['disease']}{X}")
    print(f"  {W}Confidence:{X} {result['confidence']:.0%}")
    print(f"  {W}Action    :{X} {action_label}")
    print(f"  {W}Refer     :{X} {'Yes' if result['refer'] else 'No'}")

    print()
    print(f"  {W}Advice:{X}")
    for line in textwrap.wrap(result["advice"], 51):
        print(f"    {line}")

    if result.get("description"):
        print()
        print(f"  {W}About this condition:{X}")
        for line in textwrap.wrap(result["description"], 51):
            print(f"    {line}")

    if result.get("precautions"):
        print()
        print(f"  {W}Precautions:{X}")
        for p in result["precautions"]:
            print(f"    - {p}")

    print()
    print(f"  {Y}{result['disclaimer']}{X}")
    print(C + "─"*55 + X + "\n")


# ── Built-in test cases ───────────────────────────────────────────────────────
TESTS = [
    # (label,                  symptoms,                                          expected_action)
    ("Fungal infection",       "itching skin rash nodal skin eruptions",          "otc"),
    ("Common cold",            "continuous sneezing chills fatigue cough",        "otc"),
    ("Allergy",                "sneezing runny nose itchy eyes skin rash",        "otc"),
    ("Malaria",                "chills vomiting high fever sweating headache",    "hospital"),
    ("Typhoid",                "chills vomiting fatigue weight loss lethargy",    "hospital"),
    ("Diabetes",               "fatigue weight loss restlessness polyuria",       "hospital"),
    ("Tuberculosis",           "chills vomiting fatigue cough high fever",        "hospital"),
    ("Urinary tract infection","burning micturition bladder discomfort foul urine","clinic"),
    ("Migraine",               "acidity indigestion headache nausea vomiting",    "clinic"),
    ("Chicken pox",            "itching skin rash fatigue lethargy high fever",   "otc"),
    ("Jaundice",               "itching vomiting fatigue weight loss yellowish",  "hospital"),
    ("Red flag - chest pain",  "chest pain difficulty breathing sweating",        "emergency"),
    ("Red flag - seizure",     "convulsions loss of consciousness shaking",       "emergency"),
    ("Low confidence",         "tired sometimes",                                  "clinic"),
]


def run_tests():
    print(f"\n{W}Running {len(TESTS)} test cases ...{X}\n")
    passed = failed = 0

    for label, symptoms, expected in TESTS:
        result  = model_core.diagnose(symptoms)
        ok      = result["action"] == expected
        status  = G + "PASS" + X if ok else R + "FAIL" + X
        passed += ok
        failed += (not ok)

        print(f"  [{status}]  {label}")
        print(f"          Symptoms  : {symptoms[:50]}...")
        print(f"          Predicted : {result['disease']}  ({result['confidence']:.0%})")
        print(f"          Action    : {result['action']}  (expected: {expected})")
        if not ok:
            print(f"          {R}>>> MISMATCH — check rules.json{X}")
        print()

    print("─"*55)
    print(f"  {G}{passed} passed{X}  /  {R}{failed} failed{X}  /  {len(TESTS)} total\n")


# ── Interactive mode ──────────────────────────────────────────────────────────
def interactive():
    info = model_core.model_info()
    print(f"\n{C}{W}{'='*55}{X}")
    print(f"{C}{W}  MEDIKA AI — Terminal Tester{X}")
    print(f"  Model accuracy : {info['accuracy']:.2%}")
    print(f"  Diseases known : {info['n_diseases']}")
    print(f"{C}{W}{'='*55}{X}\n")

    while True:
        print("  1  Enter symptoms manually")
        print("  2  Run built-in test suite")
        print("  3  Quit")
        choice = input("\n  Choice: ").strip()

        if choice == "1":
            print()
            symptoms = input("  Describe your symptoms: ").strip()
            if not symptoms:
                print("  Nothing entered.\n")
                continue
            result = model_core.diagnose(symptoms)
            print_result(result)

        elif choice == "2":
            run_tests()

        elif choice == "3":
            print("\n  Goodbye!\n")
            break
        else:
            print("  Please enter 1, 2, or 3.\n")


if __name__ == "__main__":
    interactive()
