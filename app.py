import os
import sqlite3
# We will import psycopg2 only when needed to avoid local installation issues
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a-default-secret-key-for-local-dev')

def get_db_connection():
    """Establishes a connection to Postgres (production) or SQLite (local)."""
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Production on Heroku/Render: Connect to PostgreSQL
        import psycopg2
        from psycopg2.extras import DictCursor
        conn = psycopg2.connect(database_url)
        conn.cursor_factory = DictCursor
    else:
        # Local Development: Connect to SQLite
        conn = sqlite3.connect('students.db')
        conn.row_factory = sqlite3.Row
    return conn

# --- NEW FUNCTION FOR AUTOMATIC DATABASE SETUP ---
def check_and_init_db():
    """
    Checks if the 'students' table exists. If not, it runs the schema.sql
    script to initialize the database. This runs once on first startup.
    """
    print("Checking if database is initialized...")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Check for the existence of the 'students' table
        if os.getenv('DATABASE_URL'):
            # PostgreSQL check
            cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'students');")
        else:
            # SQLite check
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='students';")
        
        table_exists = cur.fetchone()
        
        if table_exists and table_exists[0]:
            print("Database already initialized.")
        else:
            print("Database not initialized. Creating tables...")
            with open('schema.sql', 'r') as f:
                # Use executescript for SQLite and a simple execute for Postgres
                if conn.__class__.__name__ == 'Connection': # SQLite check
                    cur.executescript(f.read())
                else:
                    cur.execute(f.read())
            conn.commit()
            print("Database initialized successfully.")
            
    except Exception as e:
        print(f"An error occurred during DB check/initialization: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# --- Run the check right after the app is created ---
check_and_init_db()


def calculate_average(grades):
    """Calculates the average percentage from a list of grade objects."""
    if not grades: return 0
    total_percentage = sum((g['score'] / g['max_score']) * 100 for g in grades if g['max_score'] > 0)
    return total_percentage / len(grades) if grades else 0

@app.context_processor
def utility_processor():
    """Makes a utility function available in all Jinja2 templates for styling."""
    def get_grade_color_class(percentage):
        if percentage >= 90: return 'text-green-600 bg-green-100'
        if percentage >= 80: return 'text-blue-600 bg-blue-100'
        if percentage >= 70: return 'text-amber-600 bg-amber-100'
        return 'text-red-600 bg-red-100'
    return dict(get_grade_color_class=get_grade_color_class)

# --- All your routes remain exactly the same ---
# ... (The full code for all routes goes here, unchanged) ...
@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    search_query = request.args.get('search', '')
    placeholder = '%s' if os.getenv('DATABASE_URL') else '?'
    if search_query:
        query = f"SELECT * FROM students WHERE name LIKE {placeholder} OR email LIKE {placeholder} ORDER BY name"
        cur.execute(query, (f'%{search_query}%', f'%{search_query}%'))
    else:
        cur.execute("SELECT * FROM students ORDER BY name")
    students_data = cur.fetchall()
    cur.execute("SELECT * FROM grades")
    all_grades = cur.fetchall()
    cur.close()
    conn.close()
    student_details, student_averages = [], []
    for student in students_data:
        grades = [g for g in all_grades if g['student_id'] == student['id']]
        average = calculate_average(grades)
        student_averages.append(average)
        student_details.append({'info': student, 'average': average, 'grade_count': len(grades)})
    class_average = sum(student_averages) / len(student_averages) if student_averages else 0
    a_students_count = sum(1 for avg in student_averages if avg >= 90)
    stats = {'total_students': len(students_data), 'total_assignments': len(all_grades), 'class_average': class_average, 'a_students_count': a_students_count}
    return render_template('index.html', students=student_details, stats=stats, search_query=search_query)

# ... (All other routes are the same)
@app.route('/student/<int:student_id>')
def student_detail(student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    placeholder = '%s' if os.getenv('DATABASE_URL') else '?'
    cur.execute(f"SELECT * FROM students WHERE id = {placeholder}", (student_id,))
    student = cur.fetchone()
    cur.execute(f"SELECT * FROM grades WHERE student_id = {placeholder} ORDER BY created_at DESC", (student_id,))
    grades = cur.fetchall()
    cur.close()
    conn.close()
    if student is None:
        flash('Student not found.', 'error')
        return redirect(url_for('index'))
    average = calculate_average(grades)
    return render_template('student_detail.html', student=student, grades=grades, average=average)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name, email, grade_level = request.form['name'], request.form['email'], request.form['grade_level']
        if not all([name, email, grade_level]):
            flash('All fields are required.', 'error')
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            placeholder = '%s' if os.getenv('DATABASE_URL') else '?'
            query = f"INSERT INTO students (name, email, grade_level) VALUES ({placeholder}, {placeholder}, {placeholder})"
            try:
                cur.execute(query, (name, email, grade_level))
                conn.commit()
                flash(f'Student "{name}" added successfully!', 'success')
            except Exception:
                flash(f'An error occurred: Email might already exist.', 'error')
                conn.rollback()
            finally:
                cur.close()
                conn.close()
            return redirect(url_for('index'))
    return render_template('add_student.html')

@app.route('/student/<int:student_id>/add_grade', methods=['POST'])
def add_grade(student_id):
    score, max_score = int(request.form['score']), int(request.form['max_score'])
    if score > max_score:
        flash('Score cannot be greater than Max Score.', 'error')
    else:
        conn = get_db_connection()
        cur = conn.cursor()
        placeholder = '%s' if os.getenv('DATABASE_URL') else '?'
        query = f"INSERT INTO grades (student_id, subject, assignment_name, score, max_score) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})"
        cur.execute(query, (student_id, request.form['subject'], request.form['assignment_name'], score, max_score))
        conn.commit()
        cur.close()
        conn.close()
        flash('Grade added successfully!', 'success')
    return redirect(url_for('student_detail', student_id=student_id))

@app.route('/student/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    placeholder = '%s' if os.getenv('DATABASE_URL') else '?'
    cur.execute(f"DELETE FROM students WHERE id = {placeholder}", (student_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Student and all associated grades have been deleted.', 'success')
    return redirect(url_for('index'))

@app.route('/grade/<int:grade_id>/delete', methods=['POST'])
def delete_grade(grade_id):
    conn = get_db_connection()
    cur = conn.cursor()
    placeholder = '%s' if os.getenv('DATABASE_URL') else '?'
    cur.execute(f"SELECT student_id FROM grades WHERE id = {placeholder}", (grade_id,))
    grade = cur.fetchone()
    if grade:
        student_id = grade['student_id']
        cur.execute(f"DELETE FROM grades WHERE id = {placeholder}", (grade_id,))
        conn.commit()
        flash('Grade deleted.', 'success')
        redirect_url = url_for('student_detail', student_id=student_id)
    else:
        flash('Grade not found.', 'error')
        redirect_url = url_for('index')
    cur.close()
    conn.close()
    return redirect(redirect_url)

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT subject FROM grades ORDER BY subject")
    subjects = [row['subject'] for row in cur.fetchall()]
    results, selected_subject = None, None
    if request.method == 'POST':
        selected_subject = request.form.get('subject')
        if selected_subject:
            placeholder = '%s' if os.getenv('DATABASE_URL') else '?'
            topper_query = f"SELECT s.name, g.score, g.max_score FROM grades g JOIN students s ON g.student_id = s.id WHERE g.subject = {placeholder} ORDER BY (CAST(g.score AS REAL) / g.max_score) DESC LIMIT 1"
            cur.execute(topper_query, (selected_subject,))
            topper_data = cur.fetchone()
            cur.execute(f"SELECT score, max_score FROM grades WHERE subject = {placeholder}", (selected_subject,))
            grades_for_subject = cur.fetchall()
            class_average = calculate_average(grades_for_subject)
            results = {'topper': topper_data, 'class_average': class_average}
    cur.close()
    conn.close()
    return render_template('reports.html', subjects=subjects, results=results, selected_subject=selected_subject)

@app.route('/export_data')
def export_data():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students ORDER BY id"), (students := cur.fetchall())
    cur.execute("SELECT * FROM grades ORDER BY student_id, id"), (grades := cur.fetchall())
    cur.close()
    conn.close()
    backup_content = "--- STUDENT PERFORMANCE TRACKER BACKUP ---\n\n--- STUDENTS ---\n"
    for s in students: backup_content += f"ID: {s['id']}, Name: {s['name']}, Email: {s['email']}, Grade Level: {s['grade_level']}, Joined: {s['created_at']}\n"
    backup_content += "\n--- GRADES ---\n"
    for g in grades: backup_content += f"ID: {g['id']}, StudentID: {g['student_id']}, Subject: {g['subject']}, Assignment: {g['assignment_name']}, Score: {g['score']}/{g['max_score']}, Date: {g['created_at']}\n"
    return Response(backup_content, mimetype="text/plain", headers={"Content-disposition": "attachment; filename=student_data_backup.txt"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='127.0.0.1', port=port)