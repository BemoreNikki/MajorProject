from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient

import random
import string
import smtplib
from email.mime.text import MIMEText
from pymongo import MongoClient


app = Flask(__name__)
app.secret_key = 'your_secret_key'

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

def generate_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def send_login_details(to_email, username, password):
    sender_email = "notifysunilkumar@gmail.com"
    sender_password = "svjnearjremyufje"
    
    # Email content
    subject = "Your HOD Account Details"
    body = f"Hello,\n\nWELCOME to GNITS Project Management System your account has been created.\n\nUsername: {username}\nPassword: {password}\n\nPlease log in to the system."
    
    # Setup MIME
    message = MIMEText(body)
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = to_email

    # Send email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, message.as_string())

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client.gnits_project_management
departments_collection = db.department

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == DEFAULT_USERNAME and password == DEFAULT_PASSWORD:
            session['admin_logged_in'] = True  
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            session.pop('admin_logged_in', None)  
            flash('Invalid username or password. Please try again.', 'danger')
            return redirect(url_for('admin_login'))
    
    return render_template('admin/admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    # Check if admin is logged in
    if not session.get('admin_logged_in'):
        flash('Please log in to access the admin dashboard.', 'warning')
        return redirect(url_for('admin_login'))
    
    # Fetch department names from MongoDB for the dropdown
    departments = [dept['name'] for dept in db['department'].find()]
    
    # Render dashboard with departments
    return render_template('admin/admin_dashboard.html', departments=departments)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


# hod_login--------------------------------------------------

@app.route('/hod_login', methods=['GET', 'POST'])
def hod_login():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if the username exists in the database
        hod = db['hod'].find_one({"username": username})
        
        if hod and hod['password'] == password:  # Verify password match
            session['hod_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('hod_dashboard'))  # Redirect to HOD dashboard (you can create this route)
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            return redirect(url_for('hod_login'))  # Redirect back to login page
    
    return render_template('hod/hod_login.html')  # Render HOD login page

# end of hod_login------------------------------------------------------------

@app.route('/hod_dashboard')
def hod_dashboard():
    return render_template('hod/hod_dashboard.html') 

@app.route('/mentor_login')
def mentor_login():
    return "<h2>Mentor Login Page</h2>"


# student login--------------------------------------
@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        
        students = db['students'].find_one({"username": username})
        
        if students and students['password'] == password:  
            session['student_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('student_dashboard')) 
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            return redirect(url_for('student_login')) 
    
    return render_template('student/student_login.html')  

# end of hod_login------------------------------------------------------------

@app.route('/student_dashboard')
def student_dashboard():
    return render_template('student/student_dashboard.html') 
# student login end-------------------------------------

@app.route('/student_coordinator_login')
def student_coordinator_login():
    return "<h2>Student Coordinator Login Page</h2>"

@app.route('/teacher_login')
def teacher_login():
    return "<h2>Teacher Login Page</h2>"


# add department--------------------------------------------------

@app.route('/add_department', methods=['GET', 'POST'])
def add_department():
    if request.method == 'POST':
        department_name = request.form.get('department_name')
        
        if department_name:
            # Insert into MongoDB
            department_data = {'name': department_name}
            departments_collection.insert_one(department_data)
            flash('Department added successfully!', 'success')
            return redirect(url_for('add_department'))
        else:
            flash('Please enter a valid department name.', 'danger')
    
    return render_template('admin/add_department.html')

#end add deprtment----------------------------------------------------


#add hod----------------------------------------------------
@app.route('/add_hod', methods=['POST'])
def add_hod():
    # Form data
    username = request.form.get('username')
    name = request.form.get('name')
    department = request.form.get('department')
    contact_number = request.form.get('contact_number')
    email = request.form.get('email')
    address = request.form.get('address')
    
    # Check if HOD with the same name, email, or contact number already exists
    existing_hod = db['hod'].find_one({
        "$or": [
            {"name": name},
            {"email": email},
            {"contact_number": contact_number}
        ]
    })
    
    if existing_hod:
        flash('An HOD with the same name, email, or contact number already exists.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Generate random password
    password = generate_password()
    
    # Insert HOD into MongoDB
    hod_data = {
        "username": username,
        "name": name,
        "department": department,
        "contact_number": contact_number,
        "email": email,
        "address": address,
        "password": password  # Store hashed password in production
    }
    db['hod'].insert_one(hod_data)
    
    # Send email with login details
    send_login_details(email, username, password)
    
    flash('HOD added successfully and login details sent!', 'success')
    return redirect(url_for('admin_dashboard'))

#add hod end-----------------------------------------------------

#add mentor----------------------------------------------------
@app.route('/add_mentor', methods=['POST'])
def add_mentor():
    # Form data
    username = request.form.get('username')
    name = request.form.get('name')
    department = request.form.get('department')
    contact_number = request.form.get('contact_number')
    email = request.form.get('email')
    address = request.form.get('address')
    
    
    existing_mentor = db['mentor'].find_one({
        "$or": [
            {"username": username},
            {"name": name},
            {"email": email},
            {"contact_number": contact_number}
        ]
    })
    
    if existing_mentor:
        flash('Mentor with the same name, email, or contact number already exists.', 'danger')
        return redirect(url_for('admin_dashboard'))

    
    password = generate_password()
    
    
    mentor_data = {
        "username": username,
        "name": name,
        "department": department,
        "contact_number": contact_number,
        "email": email,
        "address": address,
        "password": password  
    }
    db['mentor'].insert_one(mentor_data)
    
    send_login_details(email, username, password)
    
    flash('Mentor added successfully and login details sent!', 'success')
    return redirect(url_for('admin_dashboard'))

#add mentor end-----------------------------------------------------


#add student----------------------------------------------------------
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        # Form data
        username = request.form.get('username')
        student_name = request.form.get('student_name')
        department = request.form.get('department')
        semester = request.form.get('semester')
        roll_number = request.form.get('roll_number')
        contact_number = request.form.get('contact_number')
        email = request.form.get('email')
        address = request.form.get('address')
        section = request.form.get('section')
        from_year = request.form.get('from_year')
        to_year = request.form.get('to_year')

        # Check if a student with the same roll number or email already exists
        existing_student = db['students'].find_one({
            "$or": [
                {"roll_number": roll_number},
                {"email": email},
                {"username": username},
                {"contact_number": contact_number}
            ]
        })

        if existing_student:
            flash('A student with the same roll number or email already exists.', 'danger')
            return redirect(url_for('add_student'))
        
        password = generate_password()

        # Insert student into MongoDB
        student_data = {
            "username": username,
            "student_name": student_name,
            "department": department,
            "semester": semester,
            "roll_number": roll_number,
            "contact_number": contact_number,
            "email": email,
            "address": address,
            "section": section,
            "from_year": from_year,
            "to_year": to_year,
            "password": password
        }
        db['students'].insert_one(student_data)
        
        send_login_details(email, username, password)

        flash('Student added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_student.html')

#add student end--------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)
