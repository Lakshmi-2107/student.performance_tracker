import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a-default-secret-key-for-local-dev')

# Use persistent storage on Render or local fallback
DB_PATH = '/data/students.db' if os.path.exists('/data') else 'students.db'

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_average(grades):
    """Calculates the average percentage from a list of grade objects."""
    if not grades:
        return 0
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

def ensure_db():
    """Initialize the database with schema.sql if it doesn't exist or lacks tables."""
    if not os.path.exists(DB_PATH):
        print(f"Database not found. Creating at {DB_PATH}...")
        with sqlite3.connect(DB_PATH) as conn:
            with open('schema.sql', 'r') as f:
                conn.executescript(f.read())
        print("Database initialized successfully.")
    else:
        # Check if 'students' table exists; if not, initialize
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='students';")
            if not cursor.fetchone():
                print("Table 'students' missing. Initializing database...")
                with open('schema.sql', 'r') as f:
                    conn.executescript(f.read())
                print("Database schema applied successfully.")

# Ensure DB is ready before handling any request
ensure_db()

@app.route('/')
def index():
    conn = get_db_connection()
    search_query = request.args.get('search', '')
    if search_query:
        students_data = conn.execute(
            'SELECT * FROM students WHERE name LIKE ? OR email LIKE ? ORDER BY name',
            (f'%{search_query}%', f'%{search_query}%')
        ).fetchall()
    else:
        students_data = conn.execute('SELECT * FROM students ORDER BY name').fetchall()
    all_grades = conn.execute('SELECT * FROM grades').fetchall()
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

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    grades = conn.execute('SELECT * FROM grades WHERE student_id = ? ORDER BY created_at DESC', (student_id,)).fetchall()
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
            try:
                conn.execute('INSERT INTO students (name, email, grade_level) VALUES (?, ?, ?)', (name, email, grade_level))
                conn.commit()
                flash(f'Student "{name}" added successfully!', 'success')
            except sqlite3.IntegrityError:
                flash(f'Email "{email}" already exists.', 'error')
            finally:
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
        conn.execute('INSERT INTO grades (student_id, subject, assignment_name, score, max_score) VALUES (?, ?, ?, ?, ?)',
                     (student_id, request.form['subject'], request.form['assignment_name'], score, max_score))
        conn.commit()
        conn.close()
        flash('Grade added successfully!', 'success')
    return redirect(url_for('student_detail', student_id=student_id))

@app.route('/student/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM students WHERE id = ?', (student_id,))
    conn.commit()
    conn.close()
    flash('Student and all their grades have been deleted.', 'success')
    return redirect(url_for('index'))

@app.route('/grade/<int:grade_id>/delete', methods=['POST'])
def delete_grade(grade_id):
    conn = get_db_connection()
    grade = conn.execute('SELECT student_id FROM grades WHERE id = ?', (grade_id,)).fetchone()
    if grade:
        student_id = grade['student_id']
        conn.execute('DELETE FROM grades WHERE id = ?', (grade_id,))
        conn.commit()
        flash('Grade deleted.', 'success')
    conn.close()
    return redirect(url_for('student_detail', student_id=student_id))

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    conn = get_db_connection()
    subjects_data = conn.execute('SELECT DISTINCT subject FROM grades ORDER BY subject').fetchall()
    subjects = [row['subject'] for row in subjects_data]
    
    results = None
    selected_subject = None

    if request.method == 'POST':
        selected_subject = request.form.get('subject')
        if selected_subject:
            topper_query = """
                SELECT s.name, g.score, g.max_score
                FROM grades g JOIN students s ON g.student_id = s.id
                WHERE g.subject = ?
                ORDER BY (CAST(g.score AS REAL) / g.max_score) DESC
                LIMIT 1
            """
            topper_data = conn.execute(topper_query, (selected_subject,)).fetchone()
            grades_for_subject = conn.execute('SELECT score, max_score FROM grades WHERE subject = ?', (selected_subject,)).fetchall()
            class_average = calculate_average(grades_for_subject)
            results = {'topper': topper_data, 'class_average': class_average}

    conn.close()
    return render_template('reports.html', subjects=subjects, results=results, selected_subject=selected_subject)

@app.route('/export_data')
def export_data():
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students ORDER BY id').fetchall()
    grades = conn.execute('SELECT * FROM grades ORDER BY student_id').fetchall()
    conn.close()
    backup_content = "--- STUDENT DATA BACKUP ---\n\n"
    for student in students:
        backup_content += f"Student: {student['name']} ({student['email']})\n"
        student_grades = [g for g in grades if g['student_id'] == student['id']]
        for grade in student_grades:
            backup_content += f"  - {grade['subject']}: {grade['score']}/{grade['max_score']}\n"
        backup_content += "\n"
    return Response(
        backup_content,
        mimetype="text/plain",
        headers={"Content-disposition": "attachment; filename=student_backup.txt"}
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)