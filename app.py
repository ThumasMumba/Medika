# Imports the required classes to build the application
# render_templates: used to render HTML  templates for the pages
from functools import wraps
from flask import Flask, get_flashed_messages, render_template, request, flash, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
#Imports the mysql.connector in order to handle database operations
import mysql.connector
from mysql.connector import Error
#Creating an instance of the flask class to initialize the system. Also a secret string used to encrypt session data and flash messages
app = Flask(__name__)
admin_password = "admin123"
hash_password = generate_password_hash(admin_password)
# print("Store this in DB: ", hash_password)

# Add this configuration to ensure HTML files process Jinja2 syntax
app.jinja_env.add_extension('jinja2.ext.do')
app.secret_key = 'medika_ai_secret_key'

# We define a function that checks if the connection to the database was a success or not
def create_connection():
    try:
         # Connects to the MYSQL database and store the results in the variable conn
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
        )
        
        #in order to execute statements we are going to create a cursor which is a function
        cursor = connection.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS medika")
        cursor.execute("USE medika")

        return connection

    except Error as e:
        print(f"Database connection error: {e}")
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
                            password VARCHAR(255) NOT NULL,
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
                            role ENUM('admin') DEFAULT 'admin',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            is_active BOOLEAN DEFAULT TRUE
                       )""")
        
        connection.commit()
        print("✅ Database initialized successfully!")
     except Error as e:
           print(f"Error Initializing Database: {e}")
            
initialize_db()
# # ─── Auth helpers ─────────────────────────────────────────────────────────────

def login_required(f):
    """Decorator: redirect to login if the admin is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Please log in to access the admin dashboard.", "error")
            return redirect(url_for("adminLogin"))
        return f(*args, **kwargs)
    return decorated

#App decorator: Tied to the function that comes after it
@app.route('/')
def index():
     return render_template("/index.html")
#Admin login route
@app.route('/adminLogin', methods=['GET', 'POST'])
def adminLogin():
     """"
     Handles the login process for administrators.
     It accepts both GET and POST requests.
     """
     
     error = None
     # Login Admin
     if request.method == 'GET':
        session.get('admin_logged_in')
    
     if 'admin_logged_in' in session:
        flash("Admin already logged in. ", "success")
        return redirect(url_for('admin_dashboard'))
     if request.method == 'POST':
          #Get login details from the admin
          email = request.form.get("email")
          password = request.form.get("password")
          #Debugging admin login details
          print("DEBUG: Submitted email: ", email)
          print("DEBUG: Submitted password: ", password)
          
          if not email or not password:
            flash('Please enter both email and password.', 'error')
            return redirect(url_for(('adminLogin')))
          else:
               connection = create_connection()
               if connection is None:
                    flash("Failed to connect to the database. Please try again later.", "error")
               else:
                    try:
                         cursor = connection.cursor(dictionary=True) 
                         #SQL query to check if the admin with the provided email exists in the database
                         cursor.execute("SELECT * FROM admin WHERE email = %s", (email,))
                         # Fetch the admin record from the database
                         admin = cursor.fetchone()
                         # Fetch admin record from DB
                         print("DEBUG: admin record from DB: ", admin)
                         if not admin:
                              flash("Invalid email or password", 'error')
                              return redirect(url_for('adminLogin'))
                         elif not check_password_hash(admin['password'], password):
                              flash("Invalid password", 'error')
                              return redirect(url_for('adminLogin'))
                         # Check if admin exists
                         elif admin and check_password_hash(admin['password'], password):
                              # Only sets session to true after successful check and the admin exists in our DB
                              session['admin_logged_in'] = True
                              session['admin_id'] = admin['id']
                              session['admin_email'] = admin['email']
                              session['admin_username'] = admin['username']
                              session['admin_role'] = admin['role']
                              flash("Admin login successfully!",'success')
                              return redirect(url_for('admin_dashboard'))
                         else:
                             flash('No admin found with that email and password.', 'error')
                             return redirect(url_for('adminLogin'))
                    except Error as e:
                         print(f"Database error: {e}")
                         flash("An error occurred while processing your request. Please try again later.", "error")
                         return redirect(url_for('adminLogin'))
     return render_template("adminLogin.html", error=error)
# Admin logout route
@app.route('/admin_logout')
def admin_logout():
    session.clear()
    flash("Logout successfully.", "success")
    return redirect(url_for('adminLogin'))

# admin-dashboard
@app.route('/admin_dashboard', methods=['GET'])
@login_required
def admin_dashboard():
     """Renders the admin dashboard page. 
     This page is only accessible to logged-in administrators."""
     if not session.get('admin_logged_in'):
          flash("Enter both email and password to access the admin dashboard", 'error')
     connection = create_connection()
     if connection is None:
          return "Database connection error. Please try again later."
     try:
          cursor = connection.cursor(dictionary=True)
          #SQL query to get the total number of patients in the database
          cursor.execute("SELECT COUNT(*) AS total_patients FROM patient")
          total_patients = cursor.fetchone()['total_patients']
          #SQL query to get the total number of doctors in the database
          cursor.execute("SELECT COUNT(*) AS total_doctors FROM doctors")
          total_doctors = cursor.fetchone()['total_doctors']
          #SQL query to get the total number of appointments in the database
          cursor.execute("SELECT COUNT(*) AS total_appointments FROM appointments")
          total_appointments = cursor.fetchone()['total_appointments']
          cursor.execute("SELECT * FROM patient ORDER BY registration_date DESC LIMIT 20")
          patients = cursor.fetchall()
          #Patients registered today
          cursor.execute(
               "SELECT COUNT(*) AS total FROM patient "
               "WHERE DATE(registration_date) = CURDATE()")
          patients_registered_today = cursor.fetchone()['total']
          
          #patients registered this month
          cursor.execute(
            "SELECT COUNT(*) AS total FROM patient "
            "WHERE MONTH(registration_date) = MONTH(CURDATE())"
            "AND YEAR(registration_date) = YEAR(CURDATE())")
          patients_registered_this_month = cursor.fetchone()['total']
          
          # Stats
          stats = {
               "total_patients": total_patients,
               "patients_today": patients_registered_today,
               "patients_this_month": patients_registered_this_month,
          }
          # Pagination placeholders
          page = 1
          total_pages = 1
          # Pass the retrieved data to the admin dashboard template for display
          return render_template("admin_dashboard.html", stats=stats, patients=patients, page=page, total_pages=total_pages)
     except Error as e:  
          print(f"Database error: {e}")
          flash("An error occurred while processing your request. Please try again later.", "error")
          return render_template("admin_dashboard.html", stats=None)

#Creates a route for the user login
@app.route('/login', methods = ["POST", "GET"])
def login():
     """"
     Handles the login process for administrators.
     It accepts both GET and POST requests.
     """
     if request.method == 'POST':
        #Get login credentials from the form
        email = request.form.get('email')
        password = request.form.get('password')

        #Check if the fields are not empty
        if not email or not password:
            flash('Please enter both email and password', "error")
            return redirect(url_for('login'))

        connection = create_connection()
        if connection is None:
            flash('Database connection error. Please try again later.', 'error')
            return redirect(url_for('userLogin'))

        try:
            cursor = connection.cursor(dictionary=True, buffered=True)

            #SQL Query to verify patient credentials
            login_query = """
            SELECT id, first_name, last_name, email, password, phone,
             nrc, gender, date_of_birth
            FROM patient
            WHERE email = %s
            """
            cursor.execute(login_query, (email,))
            #Get the patient record
            patient = cursor.fetchone()
            #Check if patient exists
            if patient and check_password_hash(patient['password'], password):
                session['patient_logged_in'] = True
                session['patient_id'] = patient['id']
                session['first_name'] = patient['first_name']
                session['last_name'] = patient['last_name']
                session['gender'] = patient['gender']
                session['email'] = patient['email']
                session['phone'] = patient['phone']
                flash('Login successful! Welcome on board.', 'success')
                return render_template('patient_dashboard.html')
            else:
                flash('No patient found with that email and password.', 'error')
                return redirect(url_for('login'))

        except Error as e:
            flash(f'Database error: {str(e)}', 'error')
            return render_template('/login.html')
      #GET request, show the login form
     return render_template('/login.html')

# user logout route
@app.route('/logout')
def logout():
     session.clear()
     flash("Logout successfully.", "success")
     return redirect(url_for('login'))

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
          password = request.form.get("password")
          
          #Check if fields are not empty before inserting into the database
          if not all([first_name, last_name, date_of_birth, gender, email, phone_number, nrc, password]):
               flash("Please fill in all the required fields.", 'error')
               return redirect(url_for("signUp"))
          
     # Get a database connection then insert into the patient table
          connection = create_connection()
          if connection is None:
               flash("Failed to connect to the database. Please try again later.", 'error')
               return render_template("signUp.html")
          try:
               cursor = connection.cursor()
               #SQL query to check if patient with the same email, phone number or NRC already exists
               cursor.execute("SELECT * FROM patient WHERE email = %s OR phone = %s OR nrc = %s", 
               (email, phone_number, nrc))
               existing_patient = cursor.fetchone()
               if existing_patient:
                    flash("A patient with the same email, phone number, or NRC already exists.", "error")
                    return redirect(url_for("signUp"))
               #SQL query to insert new patient record into the database
          #     Hash the password before inserting it
               hash_password = generate_password_hash(password)
               insert_query = """
                  INSERT INTO patient
                         (first_name, last_name, date_of_birth, gender, email, phone, nrc, password)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
               #Exceptions are handled in case of any database errors during the insertion process
               cursor.execute(insert_query, (first_name, last_name, date_of_birth, gender, email, phone_number, nrc, hash_password))
               connection.commit()
               flash("You have successfully signed up!", 'success')
               return redirect(url_for("patient_dashboard"))
          except Error as e:
               print(f"Database error: {e}")
               flash("An error occurred while processing your request. Please try again later.", 'error')
     return render_template("signUp.html")

@app.route("/create_offers", methods=["POST"])
@login_required
def create_offers():
     """Handles the creation of new offers. 
     This route is a placeholder and should be implemented with the actual logic to create offers in the system."""
     flash("Create Offers functionality is not implemented yet.", "error")
     return redirect(url_for('admin_dashboard'))



@app.route("/view_patients", methods=["GET"])
@login_required
def view_patients():
     """Handles the viewing of patient information. 
     This route is a placeholder and should be implemented with the actual logic to view patients in the system."""
     connection = create_connection()
     if connection is None:
          flash("Database connection error. Please try again later.", "error")
          return render_template("admin_dashboard.html", stats=None)
     try:
          cursor = connection.cursor(dictionary=True)
          #SQL query to get the total number of patients in the database
          #total patient count
          cursor.execute("SELECT COUNT(*) AS total_patients FROM patient")
          total_patients = cursor.fetchone()['total_patients']
          # Paginated patient list (20 per page)
          page     = max(1, int(request.args.get("page", 1)))
          per_page = 20
          offset   = (page - 1) * per_page
          
          #Selects all patients from the database ordered by registration date in descending order and limits the results to 20 per page based on the pagination parameters
          cursor.execute(
               "SELECT id, first_name, last_name, email, password, phone, nrc, gender, date_of_birth, registration_date "
               "FROM patient ORDER BY registration_date DESC LIMIT %s OFFSET %s",
               (per_page, offset),
          )
          # patient variable stores all the patient records fetched from the database based on the pagination parameters and is passed to the template for rendering the patient list on the admin dashboard
          patients = cursor.fetchall()

          total_pages = max(1, -(-total_patients // per_page))  # ceiling division

          flash(f"Total registered patients in the database: {total_patients}", "success")
          return render_template(
               "view_patients.html",
               stats={"total_patients": total_patients, "patients_today": None, "patients_this_month": None},
               patients=patients,
               page=page,
               total_pages=total_pages,
               total_patients=total_patients,
          )
     except Error as e:  
          print(f"Database error: {e}")
          flash("An error occurred while processing your request. Please try again later.", "error")
     return render_template("admin_dashboard.html")

@app.route("/manage_patients", methods=["GET"])
@login_required
def manage_patients():
     """Handles the management of patient information. 
     This route is a placeholder and should be implemented with the actual logic to manage patients in the system."""
     flash("Manage Patients functionality is not implemented yet.", "error")
     return redirect(url_for('admin_dashboard'))

@app.route("/system_settings", methods=["GET"])
@login_required
def system_settings():
     """Handles the management of system settings. 
     This route is a placeholder and should be implemented with the actual logic to manage system settings in the system."""
     flash("System Settings functionality is not implemented yet.", "error")
     return redirect(url_for('admin_dashboard'))



if __name__ == '__main__':
     app.run(debug=True)