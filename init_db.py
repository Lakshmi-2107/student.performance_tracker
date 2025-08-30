import sqlite3
import os

def initialize_database():
    """Reads the schema.sql file and executes it to set up the database."""
    
    # Connect to the database file (it will be created if it doesn't exist)
    conn = sqlite3.connect('students.db')
    
    try:
        # Create a cursor to execute commands
        cur = conn.cursor()
        
        # Open and read the schema.sql file
        with open('schema.sql', 'r') as f:
            # executescript can run multiple SQL statements at once
            cur.executescript(f.read())
        
        # Commit (save) the changes
        conn.commit()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"An error occurred during database initialization: {e}")
    finally:
        # Always close the connection
        conn.close()

if __name__ == '__main__':
    print("Running database initialization script...")
    # For a clean start, delete the old database file if it exists
    if os.path.exists('students.db'):
        os.remove('students.db')
        print("Removed existing database.")
    initialize_database()