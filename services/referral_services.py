from database import create_connection, get_cursor, close_connection


def create_referral(patient_id, disease, reason, urgency="urgent"):
    """
    Stores referral when AI detects serious condition.
    """

    connection = create_connection()
    if connection is None:
        return False

    cursor = get_cursor(connection)

    try:
        cursor.execute("""
            INSERT INTO referrals (
                patient_id,
                reason,
                disease,
                urgency,
                created_at
            )
            VALUES (%s, %s, %s, %s, NOW())
        """, (
            patient_id,
            reason,
            disease,
            urgency
        ))

        connection.commit()
        return True

    except Exception as e:
        print("[REFERRAL ERROR]", e)
        return False

    finally:
        close_connection(connection, cursor)