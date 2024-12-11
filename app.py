from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from pymongo import MongoClient

import random
import string
import smtplib
from email.mime.text import MIMEText
from bson import ObjectId


from werkzeug.utils import secure_filename
import os
from datetime import datetime
from datetime import timedelta
import os
from werkzeug.utils import secure_filename




app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=30)

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"



def generate_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def send_login_details(to_email, username, password):
    sender_email = "notifysunilkumar@gmail.com"
    sender_password = "svjnearjremyufje"
    
    # Email content
    subject = "Your GNITS Account Details"
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


UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    
    if not session.get('admin_logged_in'):
        flash('Please log in to access the admin dashboard.', 'warning')
        return redirect(url_for('admin_login'))
    
    
    departments = [dept['name'] for dept in db['department'].find()]
    
    
    return render_template('admin/admin_dashboard.html', departments=departments)


# hod_login--------------------------------------------------

@app.route('/hod_login', methods=['GET', 'POST'])
def hod_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check credentials
        hod = db.hod.find_one({'username': username, 'password': password})
        if hod:
            # Set session on successful login
            session['hod_logged_in'] = True
            session['hod'] = {
                'username': hod['username'],
                'department': hod['department']
            }
            flash('Login successful!', 'success')
            return redirect(url_for('hod_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('/hod/hod_login.html')



@app.route('/hod_dashboard', methods=['GET', 'POST'])
def hod_dashboard():
    if not session.get('hod_logged_in'):
        flash('Please log in to perform this action.', 'danger')
        return redirect(url_for('hod_login'))

    try:
        
        projects = list(db.projects.find().sort('updated_at', -1))

        if not projects:
            flash('No projects found.', 'info')

        
        for project in projects:
            student_username = project.get('student_username')
            student = db.students.find_one({'username': student_username})
            project['student_department'] = student.get('department', 'Not Found') if student else 'Unknown'

        
        if request.method == 'POST':
            project_id = request.form.get('project_id')  
            review_text = request.form.get('review')    

            if project_id and review_text:
                
                project = db.projects.find_one({'_id': ObjectId(project_id)})

                if project:
                    
                    review_data = {
                        'project_id': str(project['_id']),
                        'project_name': project.get('project_name', ''),
                        'student_name': project.get('student_name', ''),
                        'student_department': project.get('student_department', ''),
                        'project_description': project.get('project_description', ''),
                        'team_members': project.get('team_members', ''),
                        'upload_date': project.get('upload_date', ''),
                        'review_text': review_text,
                        'reviewed_by': session['hod']['username'],  
                        'review_date': datetime.now()
                    }

                    
                    db.reviews.update_one(
                        {'project_id': str(project['_id'])},  
                        {'$set': review_data},               
                        upsert=True                          
                    )
                    flash('Review submitted successfully and updated if already existed.', 'success')
                else:
                    flash('Project not found.', 'danger')
            else:
                flash('Please provide a valid project and review.', 'warning')

        # Render the dashboard
        return render_template('hod/hod_dashboard.html', projects=projects)

    except Exception as e:
        flash(f'An error occurred while fetching projects: {str(e)}', 'danger')
        return render_template('hod/hod_dashboard.html', projects=[])


@app.route('/view_project/<project_id>', methods=['GET'])
def view_project(project_id):
    try:
        
        project = db.projects.find_one({'_id': ObjectId(project_id)})
        if not project:
            flash('Project not found.', 'danger')
            return redirect(url_for('hod_dashboard'))
    except Exception as e:
        flash(f'An error occurred while fetching project details: {str(e)}', 'danger')
        return redirect(url_for('hod_dashboard'))

    return render_template('view_project.html', project=project)

    
    
@app.route('/reviews', methods=['GET'])
def reviews():
    try:
        
        reviews = list(db.reviews.find()) 

        
        return render_template('hod/reviews.html', reviews=reviews)

    except Exception as e:
        flash(f'An error occurred while fetching reviews: {str(e)}', 'danger')
        return render_template('hod/reviews.html', reviews=[])
    
 
@app.route('/public_reviews', methods=['GET'])
def public_reviews():
    try:
        
        reviews = list(db.reviews.find()) 

        
        return render_template('public_reviews.html', reviews=reviews)

    except Exception as e:
        flash(f'An error occurred while fetching reviews: {str(e)}', 'danger')
        return render_template('public_reviews.html', reviews=[])

# end of hod_login------------------------------------------------------------

# mentor login and logics-----------------------------------
@app.route('/mentor_login', methods=['GET', 'POST'])
def mentor_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Find the mentor by username
        mentor = db['mentor'].find_one({"username": username})

        if mentor and mentor['password'] == password:
            # Store mentor details in session
            session['mentor_logged_in'] = True
            session['mentor'] = {
                'username': mentor['username'],
                'name': mentor['name'],
                '_id': str(mentor['_id'])  # Save the mentor's unique ID for later use
            }
            flash('Login successful!', 'success')
            return redirect(url_for('mentor_dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            return redirect(url_for('mentor_login'))

    return render_template('mentor/mentor_login.html')



@app.route('/mentor_dashboard', methods=['GET', 'POST'])
def mentor_dashboard():
    
    if not session.get('mentor_logged_in'):
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('mentor_login'))

    mentor = session.get('mentor')
    mentor_id = mentor.get('_id')  

    
    assigned_projects = list(db.assigned_projects.find({"mentor_id": mentor_id}))

    
    for project in assigned_projects:
        
        student = db.students.find_one({"username": project['student_username']})
        if student:
            project['student_name'] = student.get('student_name', 'Unknown')
        else:
            project['student_name'] = 'Unknown'

        
        if 'document_path' in project:
            project['document_url'] = os.path.join(UPLOAD_FOLDER, project['document_path'])
        else:
            project['document_url'] = None

        
        feedback = db.mentor_feedback.find_one({"project_id": project['_id'], "mentor_id": mentor_id})
        if feedback:
            
            project['approval_status'] = feedback.get('status', 'pending')  
            project['comment'] = feedback.get('comment', '')
            project['timestamp'] = feedback.get('timestamp', '')
        else:
            project['approval_status'] = 'pending'  
            project['comment'] = ''
            project['timestamp'] = ''

    
    if request.method == 'POST':
        project_id = request.form.get('project_id')
        approval_status = request.form.get('approval_status')
        comment = request.form.get('comment')

        
        if not project_id or not approval_status:
            flash('Project ID and approval status are required.', 'danger')
            return redirect(url_for('mentor_dashboard'))

        
        feedback = db.mentor_feedback.find_one({"project_id": ObjectId(project_id), "mentor_id": mentor_id})

        if feedback:
            
            db.mentor_feedback.update_one(
                {'_id': feedback['_id']},
                {'$set': {
                    'status': approval_status,
                    'comment': comment,
                    'timestamp': datetime.utcnow()
                }}
            )
        else:
            
            db.mentor_feedback.insert_one({
                'project_id': ObjectId(project_id),
                'mentor_id': mentor_id,
                'status': approval_status,
                'comment': comment,
                'timestamp': datetime.utcnow()
            })

        flash('Your feedback has been submitted successfully!', 'success')
        return redirect(url_for('mentor_dashboard'))

    return render_template(
        'mentor/mentor_dashboard.html',
        assigned_projects=assigned_projects,
        mentor_name=mentor.get('name')  
    )


@app.route('/assigned_batch')
def assigned_batch():
    
    if not session.get('mentor_logged_in'):
        flash('Please log in to access the assigned batch.', 'warning')
        return redirect(url_for('mentor_login'))

    mentor = session.get('mentor')
    mentor_id = mentor.get('_id')  

    
    assigned_projects = list(db.assigned_projects.find({"mentor_id": mentor_id}))

    
    for project in assigned_projects:
        
        student = db.students.find_one({"username": project['student_username']})
        if student:
            project['student_name'] = student.get('student_name', 'Unknown')
        else:
            project['student_name'] = 'Unknown'

        if 'document_path' in project:
            project['document_url'] = os.path.join(UPLOAD_FOLDER, project['document_path'])
        else:
            project['document_url'] = None

        feedback = db.mentor_feedback.find_one({"project_id": project['_id'], "mentor_id": mentor_id})
        if feedback:
            project['approval_status'] = feedback.get('status', 'pending')  # Default to 'pending'
            project['comment'] = feedback.get('comment', '')
            project['timestamp'] = feedback.get('timestamp', '')
        else:
            project['approval_status'] = 'pending'  
            project['comment'] = ''
            project['timestamp'] = ''

    
    return render_template(
        'mentor/assigned_batch.html',  
        assigned_projects=assigned_projects,
        mentor_name=mentor.get('name') 
    )




#mentor logics end ---------------------------------------------------------

# student coordinator login and logics-----------------------------------
@app.route('/student_coordinator_login', methods=['GET', 'POST'])
def student_coordinator_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        student_coordinator = db['student_coordinator'].find_one({"username": username})
        
        if student_coordinator and student_coordinator['password'] == password:
            session['student_coordinator_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('student_coordinator_dashboard'))
        else:
            flash('Invalid username or password. Plese try again.', 'danger')
            return redirect(url_for('student_coordinator_login'))
    return render_template('student_coordinator/student_coordinator_login.html')


@app.route('/student_coordinator_dashboard')
def student_coordinator_dashboard():
    try:
        
        project_status = list(db.project_status.find())  

        return render_template('student_coordinator/student_coordinator_dashboard.html', project_status=project_status)

    except Exception as e:
        flash(f'An error occurred while fetching reviews: {str(e)}', 'danger')
        return render_template('student_coordinator/student_coordinator_dashboard.html', project_status=[])

#student coordinator logics end ---------------------------------------------------------


# teacher coordinator login---------------------------------------
@app.route('/teacher_coordinator_login', methods=['GET', 'POST'])
def teacher_coordinator_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        
        teacher_coordinator = db['teacher_coordinator'].find_one({"username": username})
        
        if teacher_coordinator and teacher_coordinator['password'] == password:
           
            session['teacher_coordinator'] = {
                'username': teacher_coordinator['username'],
                'department': teacher_coordinator['department']
            }
            session['teacher_coordinator_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('teacher_coordinator_dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            return redirect(url_for('teacher_coordinator_login'))
    
    return render_template('teacher_coordinator/teacher_coordinator_login.html')



@app.route('/teacher_coordinator_dashboard', methods=['GET'])
def teacher_coordinator_dashboard():
    
    if not session.get('teacher_coordinator_logged_in'):
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('teacher_coordinator_login'))

    
    teacher_coordinator = session.get('teacher_coordinator')
    if not teacher_coordinator:
        flash('Invalid session. Please log in again.', 'danger')
        return redirect(url_for('teacher_coordinator_login'))

    
    coordinator_department = teacher_coordinator.get('department')

    
    students_in_department = list(db.students.find({"department": coordinator_department}, {"username": 1, "student_name": 1, "_id": 0}))

    
    student_username_to_name = {student['username']: student.get('student_name', 'Unknown') for student in students_in_department}

    
    search_query = request.args.get('search_query', '').strip()

    
    query_filter = {"student_username": {"$in": list(student_username_to_name.keys())}}

    
    if search_query:
        query_filter['$or'] = [
            {'project_name': {'$regex': search_query, '$options': 'i'}},  
            {'student_name': {'$regex': search_query, '$options': 'i'}}   
        ]

    
    projects = list(db.projects.find(query_filter))

    
    for project in projects:
        project['student_name'] = student_username_to_name.get(project['student_username'], 'Unknown')

        
        if 'document_path' in project:
            project['document_url'] = os.path.join(UPLOAD_FOLDER, project['document_path'])
        else:
            project['document_url'] = None

    return render_template(
        'teacher_coordinator/teacher_coordinator_dashboard.html',
        projects=projects,
        department=coordinator_department
    )


#------------------------Project Status------------------------------
@app.route('/update_project_status', methods=['POST'])
def update_project_status():
    if not session.get('teacher_coordinator_logged_in'):
        flash('Please log in to perform this action.', 'danger')
        return redirect(url_for('teacher_coordinator_login'))

    project_id = request.form.get('project_id')
    project_status = request.form.get('project_status')
    prc_status_stage = request.form.get('prc_status_stage')
    mentor_comment = request.form.get('mentor_comment')

    if not project_id or not project_status or not prc_status_stage or not mentor_comment:
        flash('All fields are required.', 'danger')
        return redirect(url_for('teacher_coordinator_dashboard'))

    
    project = db.projects.find_one({'_id': ObjectId(project_id)})
    if not project:
        flash('Project not found.', 'danger')
        return redirect(url_for('teacher_coordinator_dashboard'))
    
    result = db.project_status.update_one(
        {'project_id': project_id},  
        {
            '$set': {  
                'project_name': project['project_name'],
                'student_name': project['student_name'],
                'project_status': project_status,
                'prc_status_stage': prc_status_stage,
                'mentor_comment': mentor_comment,
                'updated_by': session.get('teacher_coordinator')['username'],
                'updated_at': datetime.utcnow()
            }
        },
        upsert=True
    )

    if result.matched_count > 0:
        flash('Project status updated successfully!', 'success')
    else:
        flash('Project status added successfully!', 'success')

    return redirect(url_for('teacher_coordinator_dashboard'))
#------------------------Project Status End---------------------------


#-----------------project_status_list------------------------------------
@app.route('/project_status_list', methods=['GET'])
def project_status_list():
    
    if not session.get('teacher_coordinator_logged_in'):
        flash('Please log in to perform this action.', 'danger')
        return redirect(url_for('teacher_coordinator_login'))

    teacher_coordinator = session.get('teacher_coordinator')
    
    
    if not teacher_coordinator:
        flash('Invalid session. Please log in again.', 'danger')
        return redirect(url_for('teacher_coordinator_login'))

    try:
        
        project_status_list = list(db.project_status.find())

        
        return render_template('teacher_coordinator/tcd.html', project_status_list=project_status_list)

    except Exception as e:
        
        flash(f'An error occurred while fetching project statuses: {str(e)}', 'danger')
        return render_template('teacher_coordinator/tcd.html', project_status_list=[])

#-----------------------project_status_list_end-------------------------------------------


# teacher coordinator login end -----------------------------------

# student login--------------------------------------
@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        students = db['students'].find_one({"username": username})
        
        if students and students['password'] == password:  
            session['student_logged_in'] = True
            session['user_id'] = str(students['_id'])
            projects = db['projects'].find({"student_username": session.get('user_id')})

            
            projects = list(projects)
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




@app.route('/project_status')
def project_status():
    mentor_feedback = list(db.mentor_feedback.find())

    feedback_data = []
    for feedback in mentor_feedback:
        assigned_project = db.assigned_projects.find_one({"_id": feedback.get('project_id')})

        if assigned_project:
            project_name = assigned_project.get('project_name', 'Unknown')  
        else:
            project_name = 'Unknown'

        feedback_data.append({
            'project_name': project_name,
            'status': feedback.get('status', 'pending'),
            'comment': feedback.get('comment', 'No comments provided'),
            'timestamp': feedback.get('timestamp', 'Not available'),
        })

    return render_template(
        'student/project_status.html',  
        feedback_data=feedback_data  
    )

 
# student login end-------------------------------------

# add department--------------------------------------------------

@app.route('/add_department', methods=['GET', 'POST'])
def add_department():
    if request.method == 'POST':
        department_name = request.form.get('department_name')
        
        if department_name:
           
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

    
    password = generate_password()
    
    
    hod_data = {
        "username": username,
        "name": name,
        "department": department,
        "contact_number": contact_number,
        "email": email,
        "address": address,
        "password": password  
    }
    db['hod'].insert_one(hod_data)
    
    
    send_login_details(email, username, password)
    
    flash('HOD added successfully and login details sent!', 'success')
    return redirect(url_for('admin_dashboard'))

#add hod end-----------------------------------------------------

#add mentor----------------------------------------------------
@app.route('/add_mentor', methods=['POST'])
def add_mentor():
    
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

#------------------assign_project-----------------------------
@app.route('/assign_project', methods=['GET'])
def assign_project_get():
    if not session.get('admin_logged_in'):  
        flash('Please log in as an admin to access this page.', 'danger')
        return redirect(url_for('admin_login'))

    projects = list(db.projects.find({}, {"_id": 1, "project_name": 1, "student_name": 1, "student_username": 1, "project_description": 1, "team_members": 1, "document_path": 1, "upload_date": 1, "mentor_id": 1}))

    mentors = list(db.mentor.find({}, {"_id": 1, "name": 1}))

    return render_template('admin/assign_project.html', projects=projects, mentors=mentors)


@app.route('/assign_project', methods=['POST'])
def assign_project_post():
    if not session.get('admin_logged_in'):
        return jsonify({"message": "Please log in as an admin to access this page."}), 403

    data = request.get_json()
    project_id = data.get('project_id')
    mentor_id = data.get('mentor_id')

    if not project_id or not mentor_id:
        return jsonify({"message": "Project ID and Mentor ID are required."}), 400

    project = db.projects.find_one({"_id": ObjectId(project_id), "mentor_id": None})
    mentor = db.mentor.find_one({"_id": ObjectId(mentor_id)})

    if not project:
        return jsonify({"message": "Project not found or already assigned."}), 404
    if not mentor:
        return jsonify({"message": "Mentor not found."}), 404

    db.projects.update_one({"_id": ObjectId(project_id)}, {"$set": {"mentor_id": mentor_id}})

    assignment_data = {
        "project_id": str(project_id),  
        "mentor_id": str(mentor_id),   
        "student_username": project.get('student_username'),
        "student_name": project.get('student_name'),
        "project_name": project.get('project_name'),
        "project_description": project.get('project_description'),
        "team_members": project.get('team_members'),
        "document_path": project.get('document_path'),
        "upload_date": project.get('upload_date'),
        "mentor_name": mentor.get('name'),
        "assigned_at": datetime.now()
    }

    db.assigned_projects.insert_one(assignment_data)

    return jsonify({"message": "Project assigned successfully!"}), 200




#---------------------end_of_assign_project------------------------------------------


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


#add_student_coordinator---------------------------------------------
@app.route('/add_student_coordinator', methods=['POST'])
def add_student_coordinator():
    # Form data
    username = request.form.get('username')
    name = request.form.get('name')
    department = request.form.get('department')
    contact_number = request.form.get('contact_number')
    email = request.form.get('email')
    address = request.form.get('address')
    
    
    existing_student_coordinator = db['student_coordinator'].find_one({
        "$or": [
            {"username": username},
            {"name": name},
            {"email": email},
            {"contact_number": contact_number}
        ]
    })
    
    if existing_student_coordinator:
        flash('Student Coordinator with the same name, email, or contact number already exists.', 'danger')
        return redirect(url_for('admin_dashboard'))

    
    password = generate_password()
    
    
    student_coordinator_data = {
        "username": username,
        "name": name,
        "department": department,
        "contact_number": contact_number,
        "email": email,
        "address": address,
        "password": password  
    }
    db['student_coordinator'].insert_one(student_coordinator_data)
    
    send_login_details(email, username, password)
    
    flash('Student Coordinator added successfully and login details sent!', 'success')
    return redirect(url_for('admin_dashboard'))
#student_coordinator_end---------------------------------------------


# teacher coordinator login and logics-----------------------------------
@app.route('/add_teacher_coordinator', methods=['POST'])
def add_teacher_coordinator():
    # Form data
    username = request.form.get('username')
    name = request.form.get('name')
    department = request.form.get('department')
    contact_number = request.form.get('contact_number')
    email = request.form.get('email')
    address = request.form.get('address')
    
    
    existing_teacher_coordinator = db['teacher_coordinator'].find_one({
        "$or": [
            {"username": username},
            {"name": name},
            {"email": email},
            {"contact_number": contact_number}
        ]
    })
    
    if existing_teacher_coordinator:
        flash('Teacher Coordinator with the same name, email, or contact number already exists.', 'danger')
        return redirect(url_for('admin_dashboard'))

    
    password = generate_password()
    
    
    teacher_coordinator_data = {
        "username": username,
        "name": name,
        "department": department,
        "contact_number": contact_number,
        "email": email,
        "address": address,
        "password": password  
    }
    db['teacher_coordinator'].insert_one(teacher_coordinator_data)
    
    send_login_details(email, username, password)
    
    flash('Teacher Coordinator added successfully and login details sent!', 'success')
    return redirect(url_for('admin_dashboard'))

# teacher coordinator logics end------------------------------------------


# upload document------------------------------------------------------





@app.route('/upload_document', methods=['POST'])
def upload_document():
    if 'user_id' not in session:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('student_login'))

    
    print("Session User ID:", session.get('user_id'))
    
    if request.method == 'POST':
        
        project_name = request.form['project_name']
        project_description = request.form['project_description']
        team_members = request.form.getlist('team_members[]')
        document = request.files['document']

        
        if not document or document.filename == '':
            flash('No document selected!', 'danger')
            return redirect(url_for('student_dashboard'))

        
        if not allowed_file(document.filename):
            flash('Invalid file type. Only PDF and Word documents are allowed.', 'danger')
            return redirect(url_for('student_dashboard'))

        
        filename = secure_filename(document.filename)
        document_path = os.path.join('static', 'uploads', filename)  
        document.save(document_path)

        
        user_id = session.get('user_id')
        if user_id:
            try:
                user = db['students'].find_one({"_id": ObjectId(user_id)})  
            except Exception as e:
                print("Error querying database:", e)
                user = None
        else:
            user = None

        if user is None:
            flash('User not found!', 'danger')
            return redirect(url_for('student_login'))

        
        document_data = {
            'student_username': user['username'],  
            'student_name': user['student_name'],  
            'project_name': project_name,
            'project_description': project_description,
            'team_members': team_members,
            'document_path': os.path.join('uploads', filename),
            'upload_date': datetime.utcnow()  
        }

        
        db['projects'].insert_one(document_data)

        flash('Document uploaded successfully!', 'success')
        return redirect(url_for('student_dashboard'))



def get_logged_in_user():
    user_id = session.get('user_id')
    if user_id:
        user = db['students'].find_one({"_id": ObjectId(user_id)})  
    return None  


# end of upload document

# -------------------------------update project details----------------------------------------------------


@app.route('/update_project', methods=['GET'])
def update_project():
    if 'user_id' not in session:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('student_login'))

    # Fetch all projects for the logged-in user
    user_id = session.get('user_id')
    if user_id:
        try:
            user = db['students'].find_one({"_id": ObjectId(user_id)})
            projects = db['projects'].find({"student_username": user['username']})  # Query projects for this student
        except Exception as e:
            print("Error querying database:", e)
            projects = []
    else:
        projects = []

    # Pass the projects data to the template
    return render_template('student/update_project.html', projects=projects)



@app.route('/edit_project/<project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if 'user_id' not in session:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('student_login'))

    project = db['projects'].find_one({"_id": ObjectId(project_id)})

    if request.method == 'POST':
        # Update the project details
        project_name = request.form['project_name']
        project_description = request.form['project_description']
        team_members = request.form.getlist('team_members[]')

        # Check if a document is uploaded
        document = request.files.get('document')
        if document:
            if not allowed_file(document.filename):
                flash('Invalid file type. Only PDF and Word documents are allowed.', 'danger')
                return redirect(url_for('edit_project', project_id=project_id))

            # Secure and save the document
            filename = secure_filename(document.filename)
            document_path = os.path.join('static', 'uploads', filename)  
            document.save(document_path)

            project_data = {
                'document_path': document_path
            }
        else:
            project_data = {}

        # Update the project in MongoDB
        db['projects'].update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {
                "project_name": project_name,
                "project_description": project_description,
                "team_members": team_members,
                **project_data  # Include document path if it was uploaded
            }}
        )

        flash('Project updated successfully!', 'success')
        return redirect(url_for('update_project'))

    return render_template('student/edit_project.html', project=project)



@app.route('/delete_project/<project_id>', methods=['POST'])
def delete_project(project_id):
    try:
        # Find the project in the database
        result = db['projects'].delete_one({'_id': ObjectId(project_id)})
        
        if result.deleted_count > 0:
            flash('Project deleted successfully!', 'success')
        else:
            flash('Project not found!', 'danger')
        
    except Exception as e:
        flash(f'Error deleting project: {e}', 'danger')
    
    return redirect(url_for('update_project'))  






# end of update project details-----------------------------------------------

#my team-----------------------------
@app.route('/my_team')
def my_team():
    
    projects = list(db.projects.find()) 
    
    
    project_teams = [
        {"project_name": project['project_name'], "team_members": project.get('team_members', [])}
        for project in projects
    ]
    
    return render_template('student/my_team.html', project_teams=project_teams)




#my team end-------------------------------


#logout------------------------
@app.route('/logout')
def logout():
    # Clear the entire session
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
