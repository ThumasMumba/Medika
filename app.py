# Imports the required classes to build the application
# render_templates: used to render HTML  templates for the pages
from flask import Flask, render_template, request, flash, redirect, url_for

#Imports the mysql.connector in order to handle database operations
import mysql.connector
from mysql.connector import Error
#Creating an instance of the flask class to initialize the system. Also a secret string used to encrypt session data and flash messages
app = Flask(__name__)

# Add this configuration to ensure HTML files process Jinja2 syntax
app.jinja_env.add_extension('jinja2.ext.do')
app.secret_key = 'medika_ai_secret_key'

# Connects to the MYSQL database and store the results in the variable conn
conn = mysql.connector.connect(
     host = "localhost",
     user = "root",
     password = "",
     database = "medika"
)
cursor = conn.cursor()
#in order to execute statements we are going to create a cursor which is a function
# We define a function that checks if the connection to the database was a success or not
def create_connection():
     """Creates and return a database connection"""
     try:
           cursor.execute("CREATE DATABASE IF NOT EXISTS medika")
           conn.commit()
           cursor.execute("USE medika")
           return conn
     except Error as e:
          print(f"An error occurred while connecting to the database:  {e}")
          return None

#Initializes the database and ensures that all the required tables exists  
def initialize_db():
     connection = create_connection()
     if connection is None:
          print("Failed to create database connection")
          return
     try:
        cursor = connection.cursor()
     #    SQL query to create patient table if it does not exist
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS patient(
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            first_name VARCHAR(100) NOT NULL,
                            last_name VARCHAR(100) NOT NULL,
                            date_of_birth VARCHAR(50) NOT NULL,
                            gender VARCHAR(10) NOT NULL,
                            nrc VARCHAR(20) UNIQUE NOT NULL,
                            phone VARCHAR(20) UNIQUE NOT NULL,
                            email VARCHAR(100) UNIQUE NOT NULL,
                            address VARCHAR(100) NOT NULL,
                            password VARCHAR(255) NOT NULL,
                            next_kin_name VARCHAR(100) NOT NULL,
                            next_kin_phone VARCHAR(10) NOT NULL,
                            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            has_signup BOOLEAN DEFAULT FALSE
                       )
     """)
        #SLQ query that creates a table for doctors if it does not exists
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS doctors(
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            first_name VARCHAR(100) NOT NULL,
                            last_name VARCHAR(100) NOT NULL,
                            email VARCHAR(100) UNIQUE NOT NULL,
                            phone VARCHAR(20) UNIQUE NOT NULL,
                            specialization VARCHAR(100) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            has_registered BOOLEAN DEFAULT FALSE
                       )
     """)
        #SQL query to create appointments table if it does not exists
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS appointments(
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            patient_id INT NOT NULL,
                            doctor_id INT NOT NULL,
                            appointment_date DATE NOT NULL,
                            appointment_time TIME NOT NULL,
                            status ENUM('scheduled', 'completed', 'cancelled') DEFAULT 'scheduled',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       )
     """) 
     #    SQL query  to create admin table if it does not exists
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS admin(
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            username VARCHAR(100) NOT NULL,
                            email VARCHAR(100) UNIQUE NOT NULL,
                            password VARCHAR(255) NOT NULL,
                            # Defines a column in the table that can only take the value 'admin' and defaults to 'admin' if no value is provided. This ensures that all entries in the admin table are categorized as 'admin'.
                            role ENUM('admin') DEFAULT 'admin',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            is_active BOOLEAN DEFAULT TRUE
                       )""")
        
        connection.commit()
        print("✅ Database initialized successfully!")
     except Error as e:
           print(f"Error Initializing Database: {e}")
            
initialize_db()
#App decorator: Tied to the function that comes after it
@app.route('/')
def index():
     return render_template("/index.html")

@app.route('/login', methods=['POST', 'GET'])
def login():
     error = None
     # Login Admin
     #if the method in which data is accessed from the form is POST
     if request.method == 'POST':
          #Then check if the entered details form the user are correct then return success
          if request.form['email'] != 'admin@gmail.com' or request.form['password'] != 'test123':
               error = "Invalid credentials"
          else:
               flash("You have successfully logged in")
               return redirect(url_for('index'))
     #Login Patient
          
     return render_template("/login.html", error=error)

@app.route('/signUp', methods=["POST", "GET"])
def signUp():
     """Handles the sign up process for patients.
     It accepts both GET and POST requests.
     On a GET request, it renders the sign-up form.
     On a POST request, it processes the form data, validates it, and if valid, inserts the new patient record into the database.
     """
     #Check if the form submission method is POST request
     if request.method == "POST":
          #Extract form data
          first_name = request.form.get("fName")
          last_name = request.form.get("lName")
          date_of_birth = request.form.get("dob")
          gender = request.form.get("gender")
          email = request.form.get("email")
          phone_number = request.form.get("phone_number")
          nrc = request.form.get("nrc")
          address = request.form.get("address")
          next_kin_name = request.form.get("next_kin_name")
          next_kin_phone = request.form.get("next_kin_phone")
          
          #Check if fields are not empty before inserting into the database
          if not all([first_name, last_name, date_of_birth, gender, email, phone_number, nrc, address, next_kin_name, next_kin_phone]):
               flash("Please fill in all the required fields.")
               return render_template("/signUp.html")
          
     # Get a database connection then insert into the patient table
          connection = create_connection()
          if connection is None:
               flash("Failed to connect to the database. Please try again later.")
               return render_template("/signUp.html")
          try:
               cursor = connection.cursor()
               #SQL query to check if patient with the same email, phone number or NRC already exists
               cursor.execute("SELECT * FROM patient WHERE email = %s OR phone = %s OR nrc = %s", 
               (email, phone_number, nrc))
               existing_patient = cursor.fetchone()
               if existing_patient:
                    flash("A patient with the same email, phone number, or NRC already exists.")
                    return render_template("/signUp.html")
               #SQL query to insert new patient record into the database
               insert_query = """
                  INSERT INTO patient
                         (first_name, last_name, date_of_birth, gender, email, phone, nrc, address, next_kin_name, next_kin_phone)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
               #Exceptions are handled in case of any database errors during the insertion process
               cursor.execute(insert_query, (first_name, last_name, date_of_birth, gender, email, phone_number, nrc, address, next_kin_name, next_kin_phone))
               connection.commit()
               flash("You have successfully signed up!")
          except Error as e:
               print(f"Database error: {e}")
               flash("An error occurred while processing your request. Please try again later.")
     return render_template("/signUp.html")


if __name__ == '__main__':
     app.run(debug=True)