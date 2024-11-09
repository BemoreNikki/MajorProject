from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

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
    
    return render_template('admin/admin_dashboard.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/hod_login')
def hod_login():
    return "<h2>HOD Login Page</h2>"

@app.route('/mentor_login')
def mentor_login():
    return "<h2>Mentor Login Page</h2>"

@app.route('/student_login')
def student_login():
    return "<h2>Student Login Page</h2>"

@app.route('/student_coordinator_login')
def student_coordinator_login():
    return "<h2>Student Coordinator Login Page</h2>"

@app.route('/teacher_login')
def teacher_login():
    return "<h2>Teacher Login Page</h2>"

if __name__ == '__main__':
    app.run(debug=True)
