import sqlite3

def init_db():
    conn = sqlite3.connect('books.db')
    c = conn.cursor()

    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'student')) NOT NULL
        )
    ''')

    # Create books table
    c.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT NOT NULL,
            available INTEGER NOT NULL DEFAULT 1
        )
    ''')

    # Create borrow_log table
    c.execute('''
        CREATE TABLE IF NOT EXISTS borrow_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            book_id INTEGER,
            issue_date TEXT,
            due_date TEXT,
            returned INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(book_id) REFERENCES books(id)
        )
    ''')

    # Insert sample users only
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('student1', 'stud123', 'student')")

    conn.commit()
    conn.close()
    print("✅ Database initialized without sample books.")

if __name__ == "__main__":
    init_db()