-- Drop tables if they already exist to ensure a clean start
DROP TABLE IF EXISTS grades;
DROP TABLE IF EXISTS students;

-- Create the students table
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    grade_level TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create the grades table
CREATE TABLE grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    assignment_name TEXT NOT NULL,
    score INTEGER NOT NULL,
    max_score INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- If a student is deleted, all their grades will be deleted automatically
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
);