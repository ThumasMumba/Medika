import mysql.connector
from mysql.connector import Error
def create_connection():
    try:
         # Connects to the MYSQL database and store the results in the variable conn
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="medika",
            connection_timeout=10
        )
        
        #in order to execute statements we are going to create a cursor which is a function
        cursor = connection.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS medika")
        cursor.execute("USE medika")

        return connection

    except Error as e:
        print(f"Database connection error: {e}")
        return None
def get_cursor(connection):
    """
    Returns a dictionary cursor so rows can be accessed
    like row['patient_id'] instead of row[0].
    """
    return connection.cursor(dictionary=True)




def close_connection(connection, cursor=None):
    """
    Safely closes cursor and connection.
    """
    try:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

    except Error as e:
        print(f"[DATABASE CLOSE ERROR] {e}")
