import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_college_system'

# Use /tmp/ for database if running on Vercel (read-only filesystem elsewhere)
if os.environ.get('VERCEL'):
    DB_PATH = '/tmp/college.db'
else:
    DB_PATH = 'college.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT,
            dob TEXT,
            gender TEXT,
            gpa TEXT DEFAULT '0.0',
            overall_attendance TEXT DEFAULT '0',
            department TEXT
        )
    ''')
    
    # Check for missing columns in existing table (Migration)
    try:
        conn.execute('ALTER TABLE users ADD COLUMN gpa TEXT DEFAULT "0.0"')
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute('ALTER TABLE users ADD COLUMN overall_attendance TEXT DEFAULT "0"')
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute('ALTER TABLE users ADD COLUMN department TEXT')
    except sqlite3.OperationalError:
        pass

    # Subjects table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            attendance TEXT DEFAULT '0',
            marks TEXT DEFAULT '0',
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
    ''')
    
    # Notices table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            department TEXT NOT NULL,
            date_posted TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Deadlines table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_date TEXT NOT NULL,
            department TEXT NOT NULL
        )
    ''')
    
    # Dummy data
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    if cur.fetchone()[0] == 0:
        pw_hash = generate_password_hash('password123')
        conn.execute("INSERT INTO users (username, password, role, name, department) VALUES (?, ?, ?, ?, ?)", ('student1', pw_hash, 'student', 'John Doe', 'COMPUTER'))
        conn.execute("INSERT INTO users (username, password, role, name, department) VALUES (?, ?, ?, ?, ?)", ('teacher1', pw_hash, 'teacher', 'Prof. Smith', 'COMPUTER'))
        conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if 'user_id' in session:
        if session['role'] == 'student':
            return redirect(url_for('student_dashboard'))
        elif session['role'] == 'teacher':
            return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            session['department'] = user['department']
            
            if user['role'] == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('teacher_dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        department = request.form.get('department')
        role_type = request.form.get('role_type', 'student')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user:
            flash('Username already exists. Please choose a different one.')
            conn.close()
            return render_template('register.html', default_role=role_type)
            
        pw_hash = generate_password_hash(password)
        conn.execute("INSERT INTO users (username, password, role, name, department) VALUES (?, ?, ?, ?, ?)", (username, pw_hash, role_type, name, department))
        conn.commit()
        conn.close()
        
        flash('Account created successfully! You can now log in.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/student')
def student_dashboard():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    subjects = conn.execute('SELECT * FROM subjects WHERE student_id = ?', (session['user_id'],)).fetchall()
    
    # Target students by department
    dept = user['department']
    notices = conn.execute('SELECT * FROM notices WHERE department = ? ORDER BY date_posted DESC', (dept,)).fetchall()
    deadlines = conn.execute('SELECT * FROM deadlines WHERE department = ? ORDER BY due_date ASC', (dept,)).fetchall()
    conn.close()
    
    return render_template('student.html', name=session['name'], user=user, subjects=subjects, notices=notices, deadlines=deadlines)

@app.route('/add_subject', methods=['POST'])
def add_subject():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
        
    subject_name = request.form.get('subject_name')
    if subject_name:
        conn = get_db_connection()
        conn.execute('INSERT INTO subjects (student_id, name) VALUES (?, ?)', (session['user_id'], subject_name))
        conn.commit()
        conn.close()
        flash(f'Subject "{subject_name}" added successfully!')
    
    return redirect(url_for('student_dashboard'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
        
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    address = request.form.get('address')
    dob = request.form.get('dob')
    gender = request.form.get('gender')
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE users 
        SET name=?, email=?, phone=?, address=?, dob=?, gender=? 
        WHERE id=?
    ''', (name, email, phone, address, dob, gender, session['user_id']))
    conn.commit()
    conn.close()
    
    session['name'] = name
    flash('Profile settings updated successfully!')
    return redirect(url_for('student_dashboard'))

@app.route('/teacher')
def teacher_dashboard():
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    dept = session.get('department')
    students = conn.execute('SELECT * FROM users WHERE role = "student" AND department = ?', (dept,)).fetchall()
    notices = conn.execute('SELECT * FROM notices WHERE department = ? ORDER BY date_posted DESC', (dept,)).fetchall()
    deadlines = conn.execute('SELECT * FROM deadlines WHERE department = ? ORDER BY due_date ASC', (dept,)).fetchall()
    conn.close()
    
    return render_template('teacher.html', name=session['name'], department=dept, students=students, notices=notices, deadlines=deadlines)

@app.route('/add_notice', methods=['POST'])
def add_notice():
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    title = request.form.get('title')
    content = request.form.get('content')
    dept = session.get('department')
    
    conn = get_db_connection()
    conn.execute('INSERT INTO notices (title, content, department) VALUES (?, ?, ?)', (title, content, dept))
    conn.commit()
    conn.close()
    flash('New notice posted successfully!')
    return redirect(url_for('teacher_dashboard'))

@app.route('/add_deadline', methods=['POST'])
def add_deadline():
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    title = request.form.get('title')
    due_date = request.form.get('due_date')
    dept = session.get('department')
    
    conn = get_db_connection()
    conn.execute('INSERT INTO deadlines (title, due_date, department) VALUES (?, ?, ?)', (title, due_date, dept))
    conn.commit()
    conn.close()
    flash('New deadline added successfully!')
    return redirect(url_for('teacher_dashboard'))

@app.route('/delete_notice/<int:id>')
def delete_notice(id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM notices WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('teacher_dashboard'))

@app.route('/delete_deadline/<int:id>')
def delete_deadline(id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM deadlines WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('teacher_dashboard'))

@app.route('/view_profile/<int:student_id>')
def view_profile(student_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM users WHERE id = ? AND role = "student"', (student_id,)).fetchone()
    subjects = conn.execute('SELECT * FROM subjects WHERE student_id = ?', (student_id,)).fetchall()
    conn.close()
    
    if not student:
        flash('Student not found.')
        return redirect(url_for('teacher_dashboard'))
        
    return render_template('view_profile.html', student=student, subjects=subjects)

@app.route('/bulk_update_subjects/<int:student_id>', methods=['POST'])
def bulk_update_subjects(student_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    subjects = conn.execute('SELECT id FROM subjects WHERE student_id = ?', (student_id,)).fetchall()
    
    for subj in subjects:
        subj_id = subj['id']
        attendance = request.form.get(f'attendance_{subj_id}')
        marks = request.form.get(f'marks_{subj_id}')
        
        if attendance is not None and marks is not None:
            conn.execute('UPDATE subjects SET attendance=?, marks=? WHERE id=?', (attendance, marks, subj_id))
    
    conn.commit()
    conn.close()
    
    flash('All academic records updated successfully!')
    return redirect(url_for('view_profile', student_id=student_id))

@app.route('/update_gpa_attendance/<int:student_id>', methods=['POST'])
def update_gpa_attendance(student_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
        
    gpa = request.form.get('gpa')
    overall_attendance = request.form.get('overall_attendance')
    
    conn = get_db_connection()
    conn.execute('UPDATE users SET gpa=?, overall_attendance=? WHERE id=?', (gpa, overall_attendance, student_id))
    conn.commit()
    conn.close()
    
    flash('Overall performance stats updated successfully!')
    return redirect(url_for('view_profile', student_id=student_id))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
