import sqlite3
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_college_system'

# Use Vercel Postgres if available, else fallback to SQLite
DB_URL = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
USE_POSTGRES = DB_URL is not None

def get_db_connection():
    if USE_POSTGRES:
        # Connect to Postgres (Vercel Production)
        conn = psycopg2.connect(DB_URL)
        return conn
    else:
        # Connect to SQLite (Local Development)
        conn = sqlite3.connect('college.db')
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(query, params=(), fetchone=False, fetchall=False):
    conn = get_db_connection()
    # Support placeholder conversion if running locally/SQLite via '?'
    if not USE_POSTGRES:
        cur = conn.cursor()
        cur.execute(query, params)
    else:
        # Convert '?' placeholders to '%s' for Postgres
        pg_query = query.replace('?', '%s')
        cur = conn.cursor()
        cur.execute(pg_query, params)
    
    result = None
    if fetchone:
        row = cur.fetchone()
        if row and USE_POSTGRES:
            # Map Postgres tuple to dictionary-like Row
            cols = [desc[0] for desc in cur.description]
            result = dict(zip(cols, row))
        else:
            result = row
    elif fetchall:
        rows = cur.fetchall()
        if rows and USE_POSTGRES:
            cols = [desc[0] for desc in cur.description]
            result = [dict(zip(cols, row)) for row in rows]
        else:
            result = rows
    
    if not (fetchone or fetchall):
        conn.commit()
    
    conn.close()
    return result

def init_db():
    # Tables creation SQL (Standard compatible)
    commands = [
        '''CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
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
        )''',
        '''CREATE TABLE IF NOT EXISTS subjects (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            attendance TEXT DEFAULT '0',
            marks TEXT DEFAULT '0'
        )''',
        '''CREATE TABLE IF NOT EXISTS notices (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            department TEXT NOT NULL,
            date_posted TEXT DEFAULT CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS deadlines (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            due_date TEXT NOT NULL,
            department TEXT NOT NULL
        )'''
    ]
    
    conn = get_db_connection()
    cur = conn.cursor()
    for cmd in commands:
        if not USE_POSTGRES:
            # SQLite specific SERIAL replacement (AUTOINCREMENT)
            cmd = cmd.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        cur.execute(cmd)
    
    # Simple migration/column check for SQLite fallback
    if not USE_POSTGRES:
        for col in ['gpa', 'overall_attendance', 'department']:
            try: cur.execute(f'ALTER TABLE users ADD COLUMN {col} TEXT')
            except: pass

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('student_dashboard' if session['role'] == 'student' else 'teacher_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = execute_query('SELECT * FROM users WHERE username = ?', (request.form['username'],), fetchone=True)
        if user and check_password_hash(user['password'], request.form['password']):
            session.update({'user_id': user['id'], 'role': user['role'], 'name': user['name'], 'department': user['department']})
            return redirect(url_for('student_dashboard' if user['role'] == 'student' else 'teacher_dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        f = request.form
        if execute_query('SELECT * FROM users WHERE username = ?', (f['username'],), fetchone=True):
            flash('Username already exists.')
            return render_template('register.html', default_role=f.get('role_type'))
        
        execute_query("INSERT INTO users (username, password, role, name, department) VALUES (?, ?, ?, ?, ?)", 
                      (f['username'], generate_password_hash(f['password']), f.get('role_type', 'student'), f['name'], f.get('department')))
        flash('Account created successfully!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/student')
def student_dashboard():
    if 'user_id' not in session or session['role'] != 'student': return redirect(url_for('login'))
    user = execute_query('SELECT * FROM users WHERE id = ?', (session['user_id'],), fetchone=True)
    subjects = execute_query('SELECT * FROM subjects WHERE student_id = ?', (session['user_id'],), fetchall=True)
    notices = execute_query('SELECT * FROM notices WHERE department = ? ORDER BY date_posted DESC', (user['department'],), fetchall=True)
    deadlines = execute_query('SELECT * FROM deadlines WHERE department = ? ORDER BY due_date ASC', (user['department'],), fetchall=True)
    return render_template('student.html', name=session['name'], user=user, subjects=subjects, notices=notices, deadlines=deadlines)

@app.route('/add_subject', methods=['POST'])
def add_subject():
    if 'user_id' in session and session['role'] == 'student':
        execute_query('INSERT INTO subjects (student_id, name) VALUES (?, ?)', (session['user_id'], request.form.get('subject_name')))
    return redirect(url_for('student_dashboard'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' in session and session['role'] == 'student':
        f = request.form
        execute_query('UPDATE users SET name=?, email=?, phone=?, address=?, dob=?, gender=? WHERE id=?', 
                      (f.get('name'), f.get('email'), f.get('phone'), f.get('address'), f.get('dob'), f.get('gender'), session['user_id']))
        session['name'] = f.get('name')
    return redirect(url_for('student_dashboard'))

@app.route('/teacher')
def teacher_dashboard():
    if 'user_id' not in session or session['role'] != 'teacher': return redirect(url_for('login'))
    dept = session.get('department')
    students = execute_query("SELECT * FROM users WHERE role = 'student' AND department = ?", (dept,), fetchall=True)
    notices = execute_query('SELECT * FROM notices WHERE department = ? ORDER BY date_posted DESC', (dept,), fetchall=True)
    deadlines = execute_query('SELECT * FROM deadlines WHERE department = ? ORDER BY due_date ASC', (dept,), fetchall=True)
    return render_template('teacher.html', name=session['name'], department=dept, students=students, notices=notices, deadlines=deadlines)

@app.route('/add_notice', methods=['POST'])
def add_notice():
    if 'user_id' in session and session['role'] == 'teacher':
        execute_query('INSERT INTO notices (title, content, department) VALUES (?, ?, ?)', (request.form.get('title'), request.form.get('content'), session.get('department')))
    return redirect(url_for('teacher_dashboard'))

@app.route('/add_deadline', methods=['POST'])
def add_deadline():
    if 'user_id' in session and session['role'] == 'teacher':
        execute_query('INSERT INTO deadlines (title, due_date, department) VALUES (?, ?, ?)', (request.form.get('title'), request.form.get('due_date'), session.get('department')))
    return redirect(url_for('teacher_dashboard'))

@app.route('/delete_notice/<int:id>')
def delete_notice(id):
    if 'user_id' in session and session['role'] == 'teacher': execute_query('DELETE FROM notices WHERE id = ?', (id,))
    return redirect(url_for('teacher_dashboard'))

@app.route('/delete_deadline/<int:id>')
def delete_deadline(id):
    if 'user_id' in session and session['role'] == 'teacher': execute_query('DELETE FROM deadlines WHERE id = ?', (id,))
    return redirect(url_for('teacher_dashboard'))

@app.route('/view_profile/<int:student_id>')
def view_profile(student_id):
    if 'user_id' not in session or session['role'] != 'teacher': return redirect(url_for('login'))
    student = execute_query("SELECT * FROM users WHERE id = ? AND role = 'student'", (student_id,), fetchone=True)
    subjects = execute_query('SELECT * FROM subjects WHERE student_id = ?', (student_id,), fetchall=True)
    return render_template('view_profile.html', student=student, subjects=subjects)

@app.route('/bulk_update_subjects/<int:student_id>', methods=['POST'])
def bulk_update_subjects(student_id):
    if 'user_id' in session and session['role'] == 'teacher':
        subjects = execute_query('SELECT id FROM subjects WHERE student_id = ?', (student_id,), fetchall=True)
        for s in subjects:
            execute_query('UPDATE subjects SET attendance=?, marks=? WHERE id=?', (request.form.get(f'attendance_{s["id"]}'), request.form.get(f'marks_{s["id"]}'), s['id']))
    return redirect(url_for('view_profile', student_id=student_id))

@app.route('/update_gpa_attendance/<int:student_id>', methods=['POST'])
def update_gpa_attendance(student_id):
    if 'user_id' in session and session['role'] == 'teacher':
        execute_query('UPDATE users SET gpa=?, overall_attendance=? WHERE id=?', (request.form.get('gpa'), request.form.get('overall_attendance'), student_id))
    return redirect(url_for('view_profile', student_id=student_id))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
