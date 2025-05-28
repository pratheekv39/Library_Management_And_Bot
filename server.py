from flask import Flask, request, session, jsonify, render_template, redirect, url_for
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def get_db_connection():
    conn = sqlite3.connect('books.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    if session.get('logged_in'):
        return redirect(url_for('chat'))
    return render_template('home.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=? AND role='admin'", (username, password)).fetchone()
        conn.close()
        if user:
            session.clear()
            session['logged_in'] = True
            session['username'] = username
            session['role'] = 'admin'
            session['user_id'] = user['id']
            return redirect(url_for('chat'))
        return render_template('admin_login.html', error="Invalid credentials")
    return render_template('admin_login.html')

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=? AND role='student'", (username, password)).fetchone()
        conn.close()
        if user:
            session.clear()
            session['logged_in'] = True
            session['username'] = username
            session['role'] = 'student'
            session['user_id'] = user['id']
            return redirect(url_for('chat'))
        return render_template('student_login.html', error="Invalid credentials")
    return render_template('student_login.html')

@app.route('/student/signup', methods=['GET', 'POST'])
def student_signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if not username or not password:
            return render_template('student_signup.html', error="All fields are required")
        conn = get_db_connection()
        existing = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            conn.close()
            return render_template('student_signup.html', error="Username already taken")
        conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'student')", (username, password))
        conn.commit()
        conn.close()
        return redirect(url_for('student_login'))
    return render_template('student_signup.html')

@app.route('/chat')
def chat():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    return render_template('chat.html', role=session['role'], username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# --- DB Helpers ---

def add_book(title, author, genre):
    conn = get_db_connection()
    conn.execute("INSERT INTO books (title, author, genre, available) VALUES (?, ?, ?, 1)", (title, author, genre))
    conn.commit()
    conn.close()

def delete_book(book_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    conn.close()

def search_books(query):
    conn = get_db_connection()
    rows = conn.execute("SELECT id, title, author, genre, available FROM books WHERE title LIKE ? OR author LIKE ?", (f'%{query}%', f'%{query}%')).fetchall()
    conn.close()
    return rows

def borrow_book(user_id, book_id):
    conn = get_db_connection()
    avail = conn.execute("SELECT available FROM books WHERE id=?", (book_id,)).fetchone()
    if not avail or avail['available'] == 0:
        conn.close()
        return False
    issue_date = datetime.now().date()
    due_date = issue_date + timedelta(days=14)
    conn.execute("INSERT INTO borrow_log (user_id, book_id, issue_date, due_date, returned) VALUES (?, ?, ?, ?, 0)",
                 (user_id, book_id, issue_date.isoformat(), due_date.isoformat()))
    conn.execute("UPDATE books SET available=0 WHERE id=?", (book_id,))
    conn.commit()
    print(f"DEBUG: Book ID {book_id} borrowed and marked as unavailable.")
    conn.close()
    return True

def return_book(user_id, book_id):
    conn = get_db_connection()
    borrow = conn.execute("SELECT * FROM borrow_log WHERE user_id=? AND book_id=? AND returned=0", (user_id, book_id)).fetchone()
    if not borrow:
        conn.close()
        return False
    conn.execute("UPDATE borrow_log SET returned=1 WHERE id=?", (borrow['id'],))
    conn.execute("UPDATE books SET available=1 WHERE id=?", (book_id,))
    conn.commit()
    print(f"DEBUG: Book ID {book_id} returned and marked as available.")
    conn.close()
    return True

def get_borrowed_books(user_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT books.id, books.title, borrow_log.issue_date, borrow_log.due_date, borrow_log.returned FROM borrow_log JOIN books ON borrow_log.book_id = books.id WHERE borrow_log.user_id=? ORDER BY borrow_log.issue_date DESC", (user_id,)).fetchall()
    conn.close()
    return rows

def get_available_books():
    conn = get_db_connection()
    rows = conn.execute("SELECT id, title, author, genre FROM books WHERE available = 1 ORDER BY title").fetchall()
    conn.close()
    return rows

def sync_availability_with_borrow_log():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM books")
    all_books = [row['id'] for row in cursor.fetchall()]

    for book_id in all_books:
        cursor.execute("""
            SELECT COUNT(*) FROM borrow_log
            WHERE book_id = ? AND returned = 0
        """, (book_id,))
        unreturned_count = cursor.fetchone()[0]
        
        available_flag = 0 if unreturned_count > 0 else 1
        cursor.execute("UPDATE books SET available = ? WHERE id = ?", (available_flag, book_id))

    conn.commit()
    conn.close()
    print("DEBUG: Synced book availability with borrow logs.")

# --- Command parsers ---

def parse_admin_command(text):
    text = text.lower()
    if text.startswith('add book') or text.startswith('add'):
        try:
            parts = text[8:].strip().split(' author:')
            title_part = parts[0].replace('title:', '').strip()
            author_genre = parts[1].split(' genre:')
            author_part = author_genre[0].strip()
            genre_part = author_genre[1].strip()
            add_book(title_part, author_part, genre_part)
            return f"✅ Book '{title_part}' added."
        except Exception:
            return "❌ Format: add book title:<title> author:<author> genre:<genre>"
    elif text.startswith('delete book') or text.startswith('delete'):
        try:
            book_id = int(text.split(' ')[2])
            delete_book(book_id)
            return f"🗑️ Book with ID {book_id} deleted."
        except Exception:
            return "❌ Format: delete book <book_id>"
    elif text == 'list books' or text=='list':
        books = search_books('')
        if not books:
            return "No books found."
        response = "📚 Books:\n"
        for b in books:
            status = "✅" if b['available'] == 1 else "❌"
            response += f"ID {b['id']}: '{b['title']}' by {b['author']} ({b['genre']}) - {status}\n"
        return response
    elif text == 'sync availability' or text=='sync':
        sync_availability_with_borrow_log()
        return "✅ Book availability synced with borrow logs."
    elif text == 'help':
        return ("📋 Admin Commands:\n"
                "🟢 add book title:<title> author:<author> genre:<genre>\n"
                "🟡 delete book <book_id>\n"
                "🔵 list books\n"
                "🔴 sync availability\n")
    return "❓ Unknown admin command. Type `help`."

def parse_student_command(text, user_id):
    text = text.lower().strip()

    if text.startswith('search book') or text.startswith('search'):
        query = text[11:].strip()
        results = search_books(query)
        if not results:
            return "🔍 No books found."
        response = "🔍 Search Results:\n"
        for b in results:
            status = "✅" if b['available'] == 1 else "❌"
            response += f"ID {b['id']}: '{b['title']}' by {b['author']} ({b['genre']}) - {status}\n"
        return response

    elif text.startswith('borrow'):
        try:
            book_id = int(text.split(' ')[1])
            if borrow_book(user_id, book_id):
                return f"📘 Book ID {book_id} borrowed successfully. Due in 14 days."
            return "❌ Book not available or does not exist."
        except Exception:
            return "❌ Format: borrow <book_id>"

    elif text.startswith('return'):
        try:
            book_id = int(text.split(' ')[1])
            if return_book(user_id, book_id):
                return f"✅ Book ID {book_id} returned successfully."
            return "❌ You have not borrowed this book or it has already been returned."
        except Exception:
            return "❌ Format: return <book_id>"

    elif text == 'list available books' or text=='list':
        available = get_available_books()
        if not available:
            return "📕 No books currently available."
        response = "📚 Available Books:\n"
        for b in available:
            response += f"ID {b['id']}: '{b['title']}' by {b['author']} ({b['genre']})\n"
        return response

    elif text == 'my borrowed books' or text.startswith('my'):
        borrowed = get_borrowed_books(user_id)
        if not borrowed:
            return "📦 You have no borrowed books."
        response = "📦 Your Borrowed Books:\n"
        for b in borrowed:
            returned_status = '✅' if b['returned'] else '❌'
            response += (f"'{b['title']}' | Issued: {b['issue_date']}, Due: {b['due_date']}, Returned: {returned_status}\n")
        return response

    elif text == 'help':
        return ("📋 Student Commands:\n"
                "🔍 search book <keyword>\n"
                "📘 borrow <book_id>\n"
                "🔁 return <book_id>\n"
                "📚 list available books\n"
                "📦 my borrowed books")

    return "❓ Unknown student command. Type `help`."

@app.route('/chat', methods=['POST'])
def chat_api():
    if not session.get('logged_in'):
        return jsonify({"response": "❌ Not logged in. Please login first."})
    msg = request.json.get('message').strip()
    if session['role'] == 'admin':
        response = parse_admin_command(msg)
    else:
        response = parse_student_command(msg, session['user_id'])
    return jsonify({"response": response})

if __name__ == '__main__':
    # Optional: Sync availability at server start
    sync_availability_with_borrow_log()
    app.run(debug=True)
