# Imports the required classes to build the application
# render_templates: used to render HTML  templates for the pages
from datetime import  date, timedelta
from contextlib import contextmanager
import datetime
from functools import wraps
from database import create_connection
from mysql.connector import Error
from flask_cors import CORS
from routes.ai_routes import ai_app
from flask import Flask, get_flashed_messages, render_template, request, flash, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
#Imports the mysql.connector in order to handle database operations

#Creating an instance of the flask class to initialize the system. Also a secret string used to encrypt session data and flash messages
app = Flask(__name__)
# print("Store this in DB: ", hash_password)

# Add this configuration to ensure HTML files process Jinja2 syntax
app.jinja_env.add_extension('jinja2.ext.do')
app.secret_key = 'medika_ai_secret_key'
CORS(app)
app.register_blueprint(ai_app)  # Register the AI routes under the /ai prefix
# We define a function that checks if the connection to the database was a success or not

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
                            patient_id INT AUTO_INCREMENT PRIMARY KEY,
                            first_name VARCHAR(100) NOT NULL,
                            last_name VARCHAR(100) NOT NULL,
                            date_of_birth DATE NOT NULL,
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
                            doctor_id INT AUTO_INCREMENT PRIMARY KEY,
                            doctor_first_name VARCHAR(100) NOT NULL,
                            gender VARCHAR(4) NOT NULL,
                            password VARCHAR(30),
                            doctor_last_name VARCHAR(100) NOT NULL,
                            email VARCHAR(100) UNIQUE NOT NULL,
                            phone VARCHAR(20) UNIQUE NOT NULL,
                            specialization VARCHAR(100) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            has_registered BOOLEAN DEFAULT FALSE
                       )
     """)
        #SQL query to create appointments table if it does not exists
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS appointments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    patient_id INT NOT NULL,
                    doctor_id INT NOT NULL,
                    appointment_date DATE NOT NULL,
                    appointment_time TIME NOT NULL,
                    mode ENUM('in_person', 'virtual') NOT NULL DEFAULT 'in_person',
                    reason TEXT,
                    status ENUM('pending', 'approved', 'rejected', 'cancelled') NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
                    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
                    INDEX(patient_id),
                    INDEX(doctor_id),
                    INDEX(status)
                    );
  """)
        #SQL query to create notifications table if it does not exists
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    recipient_type ENUM('patient', 'doctor') NOT NULL,
                    recipient_id INT NOT NULL,
                    appointment_id INT,
                    type ENUM('booked', 'approved', 'rejected', 'cancelled') NOT NULL,
                    message VARCHAR(255) NOT NULL,
                    read_flag BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE,
                    INDEX(recipient_type, recipient_id, read_flag)
                    );
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


def patient_required(f):
    """Decorator: redirect to login if the patient is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('patient_logged_in'):
            flash("Please log in to access the patient dashboard.", "error")
            return redirect(url_for("login"))
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

@app.route("/ai_ui", methods=["GET"])
@patient_required
def ai_ui():
     """Renders the AI UI page. 
     This page is intended to provide an interface for AI-related features and functionalities."""
     return render_template("ai_ui.html")

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
            SELECT patient_id, first_name, last_name, email, password, phone,
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
                session['patient_id'] = patient['patient_id']
                session['first_name'] = patient['first_name']
                session['last_name'] = patient['last_name']
                session['gender'] = patient['gender']
                session['date_of_birth'] = patient['date_of_birth']
                session['email'] = patient['email']
                session['phone'] = patient['phone']
                flash('Login successful! Welcome on board.', 'success')
                return render_template('patient_dashboard.html')
            else:
                flash('No patient found with that email and password.', 'error')
                return redirect(url_for('login'))

        except Error as e:
            flash(f'Database error: {str(e)}', 'error')
            print(f"Database error: {str(e)}")
            return render_template('/login.html')
      #GET request, show the login form
     return render_template('/login.html')

# user logout route
@app.route('/logout')
def logout():
     session.clear()
     flash("Logout successfully.", "success")
     return redirect(url_for('login'))

@app.route("/patient_dashboard", methods=["POST", "GET"])
@patient_required
def patient_dashboard():
     """
     Handles the patient dashboard data that when the patient submits their symptoms and other ailments
     """
     #
     flash('Login successful! Welcome on board.', 'success')
     return render_template('patient_dashboard.html')

@app.route("/patient_pro", methods=["POST", "GET"])
def patient_pro():
     """Handles patient profile dashboard"""
     return render_template("/patient_pro.html")

@app.route("/patient_records", methods=['GET'])
@patient_required
def patient_records():
     """Handles patient records dashboard"""
     return render_template("/patient_records.html")

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
               "SELECT patient_id, first_name, last_name, email, password, phone, nrc, gender, date_of_birth, registration_date "
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
     return redirect(url_for("admin_dashboard"))

@app.route("/manage_patients", methods=["GET"])
@login_required
def manage_patients():
     """Handles the management of patient information. 
     This route is a placeholder and should be implemented with the actual logic to manage patients in the system."""
     flash("Manage Patients functionality is not implemented yet.", "error")
     return redirect(url_for('admin_dashboard'))

####  HELPER FUNCTIONS  ####

@contextmanager
def get_dict_cursor(connection, commit=False):
    cursor = connection.cursor(dictionary=True, buffered=True)
    try:
        yield cursor
        if commit:
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

def _row_to_appointment(row, include="doctor"):
    """include='doctor' for patient-facing views, 'patient' for doctor-facing views."""
    apt = {
        "id": row["id"],
        "date": row["date"],
        "time": _to_time(row["time"]),
        "mode": row["mode"],
        "reason": row.get("reason"),
        "status": row["status"],
    }
    if include == "doctor":
        apt["doctor"] = {
            "first_name": row["doctor_first_name"],
            "last_name": row["doctor_last_name"],
            "specialty": row["specialization"],
            "photo_url": row.get("photo_url"),
        }
    else:
        apt["patient"] = {
            "first_name": row["patient_first_name"],
            "last_name": row["patient_last_name"],
        }
    return apt

def create_notification(cursor, recipient_type, recipient_id, appointment_id, ntype, message):
    cursor.execute(
        "INSERT INTO notifications (recipient_type, recipient_id, appointment_id, type, message) "
        "VALUES (%s, %s, %s, %s, %s)",
        (recipient_type, recipient_id, appointment_id, ntype, message),
    )

def get_notifications(cursor, recipient_type, recipient_id, limit=20):
    cursor.execute(
        "SELECT id, type, message, read_flag AS `read`, created_at "
        "FROM notifications WHERE recipient_type = %s AND recipient_id = %s "
        "ORDER BY created_at DESC LIMIT %s",
        (recipient_type, recipient_id, limit),
    )
    return cursor.fetchall()


@app.route("/appointment", methods=["GET", "POST"])
@patient_required
def appointment():
    connection = create_connection()
    if connection is None:
        flash("Database connection error. Please try again later.", "error")
        return redirect(url_for("patient_dashboard"))

    if request.method == "POST":
        doctor_id = request.form.get("doctor_id", type=int)
        date_str = request.form.get("date", "").strip()
        time_str = request.form.get("time", "").strip()
        mode = request.form.get("mode", "").strip()
        reason = request.form.get("reason", "").strip()

        errors = []
        try:
            apt_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            if apt_date < date.today():
                errors.append("Date can't be in the past.")
        except ValueError:
            errors.append("Invalid date.")
        try:
            apt_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            errors.append("Invalid time.")
        if mode not in ("in_person", "virtual"):
            errors.append("Invalid consultation type.")
        if not reason:
            errors.append("Please provide a reason for the visit.")
        if not doctor_id:
            errors.append("Please choose a doctor.")

        if errors:
            for e in errors:
                flash(e, "error")
            return redirect(url_for("appointment"))

        try:
               cursor = connection.cursor(dictionary=True, buffered=True)
                # confirm the doctor actually exists before trusting the id
               cursor.execute("SELECT doctor_id FROM doctors WHERE doctor_id = %s", (doctor_id,))
               if cursor.fetchone() is None:
                    flash("Selected doctor not found.", "error")
                    return redirect(url_for("appointment"))

               cursor.execute(
                    "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, mode, reason, status) "
                    "VALUES (%s, %s, %s, %s, %s, %s, 'pending')",
                    (session.get("patient_id"), doctor_id, apt_date, apt_time, mode, reason),
               )
               new_id = cursor.lastrowid

               cursor.execute(
                    "SELECT first_name, last_name FROM patient WHERE patient_id = %s", (session.get("patient_id"),)
               )
               patient = cursor.fetchone()

               create_notification(
                    cursor, "doctor", doctor_id, new_id, "booked",
                    f"New appointment request from {patient['first_name']} {patient['last_name']} "
                    f"on {apt_date.strftime('%b %d, %Y')} at {apt_time.strftime('%I:%M %p')}."
               )

               flash("Appointment request sent. You'll be notified once it's confirmed.", "success")
               return redirect(url_for("appointment"))
        except Error as e:
             print(f"Database error: {e}")
             flash("An error occurred while processing your request. Please try again later.", "error")
             return redirect(url_for("appointment"))

    # GET
    try:
        cursor = connection.cursor(dictionary=True, buffered=True)
        cursor.execute(
            "SELECT doctor_id AS id, doctor_first_name, doctor_last_name, specialization "
            "FROM doctors ORDER BY doctor_last_name"
        )
        doctors = cursor.fetchall()

        base_query = """
            SELECT appointment_id, appointment_date, appointment_time, mode, reason, status,
                   doctor_first_name AS doctor_first_name, doctor_last_name AS doctor_last_name,
                   specialization
            FROM appointments a
            JOIN doctors d ON d.doctor_id = a.doctor_id
            WHERE a.patient_id = %s AND {condition}
            ORDER BY appointment_date ASC, appointment_time ASC
        """
        cursor.execute(
            base_query.format(condition="a.status IN ('pending','approved')"),
            (session.get("patient_id"),),
        )
        upcoming_appointments = [_row_to_appointment(r) for r in cursor.fetchall()]

        cursor.execute(
            base_query.format(condition="a.status IN ('rejected','cancelled')"),
            (session.get("patient_id"),),
        )
        past_appointments = [_row_to_appointment(r) for r in cursor.fetchall()]

        notifications = get_notifications(cursor, "patient", session.get("patient_id"))

        return render_template(
               "appointment.html",
               doctor=doctors,
               upcoming_appointments=upcoming_appointments,
               past_appointments=past_appointments,
               notifications=notifications,
               today=date.today().isoformat(),
          )
    except Error as e:
            print(f"GET: try block")
            print(f"Database error: {e}")
            flash("An error occurred while processing your request. Please try again later.", "error")
            return redirect(url_for("patient_dashboard"))

@app.route("/appointment/<int:appointment_id>/cancel", methods=["POST"])
@patient_required
def cancel_appointment(appointment_id):
    patient_id = session["patient_id"]
    connection = create_connection()
    try:
         
       cursor = connection.cursor(dictionary=True, buffered=True)
       cursor.execute(
            "UPDATE appointments SET status = 'cancelled' "
            "WHERE id = %s AND patient_id = %s AND status IN ('pending','approved')",
            (appointment_id, patient_id),
        )
       if cursor.rowcount:
            cursor.execute(
                "SELECT doctor_id FROM appointments WHERE id = %s", (appointment_id,)
            )
            row = cursor.fetchone()
            if row:
                create_notification(
                    cursor, "doctor", row["doctor_id"], appointment_id, "cancelled",
                    "A patient cancelled their appointment."
                              )
       flash("Appointment cancelled.", "success")
       return redirect(url_for("appointment"))
    except Error as e:
          print(f"Database error: {e}")
          flash("An error occurred while processing your request. Please try again later.", "error")
          return redirect(url_for("appointment"))     

@app.route("/system_settings", methods=["GET"])
@login_required
def system_settings():
     """Handles the management of system settings. 
     This route is a placeholder and should be implemented with the actual logic to manage system settings in the system."""
     flash("System Settings functionality is not implemented yet.", "error")
     return redirect(url_for('admin_dashboard'))

def _to_time(value):
    """mysql-connector returns TIME columns as datetime.timedelta, not
    datetime.time, so `apt.time.strftime(...)` in the template would fail.
    Normalize to a real `time` object here so templates can call strftime
    directly."""
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return time_cls(hour=hours % 24, minute=minutes, second=seconds) # type: ignore #type ignore
    return value
 
 
@app.route('/doctor_signUp', methods=["POST", "GET"])
def doctor_signUp():
     """Handles the sign up process for doctors.
     It accepts both GET and POST requests.
     On a GET request, it renders the sign-up form.
     On a POST request, it processes the form data, validates it, and if valid, inserts the new doctor record into the database.
     """
     #Check if the form submission method is POST request
     if request.method == "POST":
          #Extract form data
          doctor_first_name = request.form.get("fName")
          doctor_last_name = request.form.get("lName")
          gender = request.form.get("gender")
          email = request.form.get("email")
          phone_number = request.form.get("phone_number")
          password = request.form.get("password")
          specialization = request.form.get("specialization")

          #Check if fields are not empty before inserting into the database
          if not all([doctor_first_name, doctor_last_name, gender, email, phone_number, password, specialization]):
               flash("Please fill in all the required fields.", 'error')
               return redirect(url_for("doctor_signUp"))
          
     # Get a database connection then insert into the doctors table
          connection = create_connection()
          if connection is None:
               flash("Failed to connect to the database. Please try again later.", 'error')
               return render_template("doctor_signUp.html")
          try:
               cursor = connection.cursor()
               #SQL query to check if doctor with the same email, phone number or NRC already exists
               cursor.execute("SELECT * FROM doctors WHERE email = %s OR phone = %s", (email, phone_number))
               existing_doctor = cursor.fetchone()
               if existing_doctor:
                    flash("A doctor with the same email, phone number, or NRC already exists.", "error")
                    return redirect(url_for("doctor_signUp"))
               #SQL query to insert new doctor record into the database
          #     Hash the password before inserting it
               hash_password = generate_password_hash(password)
               insert_query = """
                  INSERT INTO doctors
                         (doctor_first_name, doctor_last_name, gender, email, phone, password, specialization)
                         VALUES (%s, %s, %s, %s, %s, %s, %s)"""
               #Exceptions are handled in case of any database errors during the insertion process
               cursor.execute(insert_query, (doctor_first_name, doctor_last_name, gender, email, phone_number, hash_password, specialization))
               session['doctor_logged_in'] = True
               session['doctor_id'] = cursor.lastrowid # Gets the auto-incremented id
               session['doctor_first_name'] = doctor_first_name
               session['doctor_last_name'] = doctor_last_name
               session['email'] = email
               session['specialization'] = specialization
               connection.commit()
               flash("You have successfully signed up!", 'success')
               return redirect(url_for("doctor_dashboard"))
          except Error as e:
               print(f"Database error: {e}")
               flash("An error occurred while processing your request. Please try again later.", 'error')
     return render_template("doctor_signUp.html")

def doctor_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("doctor_id"):
            flash("Please sign in to continue.", "error")
            return redirect(url_for("doctor_login"))
        return view(*args, **kwargs)
 
    return wrapped
 
# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
 
#Creates a route for the doctor login
@app.route('/doctor_login', methods = ["POST", "GET"])
def doctor_login():
     """"
     Handles the login process for doctors.
     It accepts both GET and POST requests.
     """
     if request.method == 'POST':
        #Get login credentials from the form
        email = request.form.get('email')
        password = request.form.get('password')

        #Check if the fields are not empty
        if not email or not password:
            flash('Please enter both email and password', "error")
            return redirect(url_for('doctor_login'))

        connection = create_connection()
        if connection is None:
            flash('Database connection error. Please try again later.', 'error')
            
            return redirect(url_for('doctor_login'))

        try:
            cursor = connection.cursor(dictionary=True, buffered=True)

            #SQL Query to verify doctor credentials
            login_query = """
            SELECT doctor_id, doctor_first_name, doctor_last_name, email, password, phone,
             gender, specialization
            FROM doctors
            WHERE email = %s
            """
            cursor.execute(login_query, (email,))
            #Get the doctor record
            doctor = cursor.fetchone()
            #Check if doctor exists
            if doctor and check_password_hash(doctor['password'], password):
                session['doctor_logged_in'] = True
                session['doctor_id'] = doctor['doctor_id']
                session['doctor_first_name'] = doctor['doctor_first_name']
                session['doctor_last_name'] = doctor['doctor_last_name']
                session['gender'] = doctor['gender']
                session['email'] = doctor['email']
                session['phone'] = doctor['phone']
                session['specialization'] = doctor['specialization']
                flash('Login successful! Welcome on board.', 'success')
                return redirect(url_for('doctor_dashboard'))
            else:
                flash('No doctor found with that email and password.', 'error')
                return redirect(url_for('doctor_login'))

        except Error as e:
            flash(f'Database error: ', 'error')
            print(f"Database error: {str(e)}")
            return render_template('doctor_login.html')
      #GET request, show the login form
     return render_template('doctor_login.html')
 
 
@app.route("/logout")
def doctor_logout():
    session.pop("doctor_id", None)
    session.pop("doctor_logged_in", None)
    session.pop("doctor_first_name", None)
    session.pop("doctor_last_name", None)
    session.pop("email", None)
    session.pop("specialization", None)
    flash("You've been signed out.", "success")
    return redirect(url_for("doctor_login"))
 
 
# ---------------------------------------------------------------------------
# Doctor Dashboard
# ---------------------------------------------------------------------------
 
@app.route("/doctor_dashboard")

def doctor_dashboard():
    # Create a connection first
    connection = create_connection()
    doctor = None
    pending_appointments = []
    upcoming_appointments = []
    todays_appointments = []
    try:
        if connection is None:
            flash("Database connection error. Please try again later.", "error")
            return redirect(url_for("doctor_login"))
        cursor = connection.cursor(dictionary=True, buffered=True)
        cursor.execute(
            "SELECT doctor_id, doctor_first_name, doctor_last_name, specialization, phone "
            "FROM doctors WHERE doctor_id = %s",
            (session.get("doctor_id"),)
        )
        doctor = cursor.fetchone()
          
        base_query = """
                    SELECT
                         appointment_id, appointment_date, appointment_time, mode, reason, status,
                         first_name AS first_name,
                         last_name  AS last_name
                    FROM appointments a
                    JOIN patient p ON p.patient_id = a.patient_id
                    WHERE a.doctor_id = %s AND a.status = %s
                    ORDER BY a.appointment_date ASC, a.appointment_time ASC
               """
          
        cursor.execute(base_query, (session.get("doctor_id"), "pending"))
        pending_appointments = [_row_to_appointment(r) for r in cursor.fetchall()]
          
        cursor.execute(base_query, (session.get("doctor_id"), "approved"))
        upcoming_appointments = [_row_to_appointment(r) for r in cursor.fetchall()]
        
    except Error as e:
         print(f"Dashboard query error: {e}")  
    finally:
         connection.close()     
         
    todays_appointments = [
         apt for apt in upcoming_appointments if apt["date"] == date.today()
            ]
    return render_template(
        "doctor_dashboard.html",
        doctor=doctor,
        pending_appointments=pending_appointments,
        upcoming_appointments=upcoming_appointments,
        todays_appointments=todays_appointments,
    )
 
 
# ---------------------------------------------------------------------------
# Accept / Reject
# ---------------------------------------------------------------------------
 
@app.route("/appointment/<int:appointment_id>/accept", methods=["POST"])
@doctor_login_required
def accept_appointment(appointment_id):
    _update_appointment_status(appointment_id, "approved")
    flash("Appointment confirmed.", "success")
    return redirect(url_for("doctor_dashboard"))
 
 
@app.route("/appointment/<int:appointment_id>/reject", methods=["POST"])
@doctor_login_required
def reject_appointment(appointment_id):
    _update_appointment_status(appointment_id, "rejected")
    flash("Appointment rejected.", "success")
    return redirect(url_for("doctor_dashboard"))
 
 
def _update_appointment_status(appointment_id, new_status):
    doctor_id = session["doctor_id"]
    connection = create_connection()
    with get_dict_cursor(connection, commit=True) as cursor: # type: ignore
        # Scope the UPDATE to this doctor's own id so one doctor can
        # never accept/reject another doctor's appointment via a
        # crafted request.
        cursor.execute(
            "UPDATE appointments SET status = %s "
            "WHERE id = %s AND doctor_id = %s",
            (new_status, appointment_id, doctor_id),
        )
if __name__ == '__main__':
     app.run(debug=True)