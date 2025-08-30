-- Drop tables if they exist to allow for clean re-initialization
DROP TABLE IF EXISTS grades;
DROP TABLE IF EXISTS students;

-- Use SERIAL for auto-incrementing primary keys in PostgreSQL
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    grade_level TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE grades (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    assignment_name TEXT NOT NULL,
    score INTEGER NOT NULL,
    max_score INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
);