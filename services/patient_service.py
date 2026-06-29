from datetime import date, datetime
from database import create_connection, get_cursor, close_connection


def calculate_age(date_of_birth):
    if isinstance(date_of_birth, str):
        date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()

    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def build_patient_context(patient_id):
    """
    Builds patient context for MEDIKA AI using MySQL.
    """

    context = {
        "age": None,
        "gender": "",
        "conditions": [],
        "medications": [],
        "allergies": [],
        "past_diagnoses": [],
        "last_visit_reason": ""
    }

    connection = create_connection()
    if connection is None:
        return context

    cursor = get_cursor(connection)

    try:
        # ─────────────────────────────
        # 1. Basic patient info
        # ─────────────────────────────
        cursor.execute("""
            SELECT date_of_birth, gender
            FROM patient
            WHERE patient_id = %s
        """, (patient_id,))

        patient = cursor.fetchone()

        if not patient:
            return context

        context["age"] = calculate_age(patient["date_of_birth"])
        context["gender"] = patient["gender"]

        # ─────────────────────────────
        # 2. Conditions (future-ready)
        # ─────────────────────────────
        context["conditions"] = []

        # ─────────────────────────────
        # 3. Medications (future-ready)
        # ─────────────────────────────
        context["medications"] = []

        # ─────────────────────────────
        # 4. Allergies (from patient table if exists)
        # ─────────────────────────────
        context["allergies"] = []
        # cursor.execute("""
        #     SELECT allergies
        #     FROM patient
        #     WHERE patient_id = %s
        # """, (patient_id,))

        # allergy_row = cursor.fetchone()

        # if allergy_row and allergy_row.get("allergies"):
        #     context["allergies"] = [
        #         a.strip().lower()
        #         for a in allergy_row["allergies"].split(",")
        #         if a.strip()
        #     ]

        # ─────────────────────────────
        # 5. Past diagnoses (future table)
        # ─────────────────────────────
        context["past_diagnoses"] = []

        # ─────────────────────────────
        # 6. Last visit reason (not in schema yet → safe fallback)
        # ─────────────────────────────
        cursor.execute("""
            SELECT appointment_time
            FROM appointments
            WHERE patient_id = %s
            AND status = 'scheduled'
            ORDER BY appointment_date DESC
            LIMIT 1
        """, (patient_id,))

        last = cursor.fetchone()

        if last:
            context["last_visit_reason"] = "recent appointment exists"

        return context

    finally:
        close_connection(connection, cursor)