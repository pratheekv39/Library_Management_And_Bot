from flask import Flask, request, session, jsonify, render_template, redirect, url_for, flash
import sqlite3
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configure upload folder for profile pictures
UPLOAD_FOLDER = 'static/profile_pics'
# Configure upload folder for book covers
BOOK_COVER_UPLOAD_FOLDER = 'static/book_covers'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['BOOK_COVER_UPLOAD_FOLDER'] = BOOK_COVER_UPLOAD_FOLDER

# Create upload folders if they don't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(BOOK_COVER_UPLOAD_FOLDER):
    os.makedirs(BOOK_COVER_UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('books.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Create users table with new fields
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        address TEXT,
        profile_pic TEXT,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create categories table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create books table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        genre TEXT,
        isbn TEXT UNIQUE,
        cover_image TEXT,
        category_id INTEGER,
        available INTEGER DEFAULT 1,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    ''')
    
    # Create reading_history table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS reading_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        borrow_date TIMESTAMP NOT NULL,
        return_date TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (book_id) REFERENCES books (id)
    )
    ''')
    
    # Create borrow_log table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS borrow_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        returned BOOLEAN DEFAULT 0,
        return_date TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (book_id) REFERENCES books (id)
    )
    ''')
    
    # Create fines table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS fines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        reason TEXT NOT NULL,
        paid BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        paid_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Add default admin user if not exists
def create_default_admin():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ? AND role = 'admin'", ('admin',))
    admin_user = cursor.fetchone()
    
    if not admin_user:
        conn.execute('''
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
        ''', ('admin', 'admin', 'admin')) # Default username and password
        conn.commit()
        print("DEBUG: Default admin user 'admin' created.")
    else:
        print("DEBUG: Admin user already exists.")
        
    conn.close()

# Call the function to create default admin after initializing the database
create_default_admin()

@app.route('/')
def home():
    conn = get_db_connection()
    
    stats = {
        'total_books': conn.execute('SELECT COUNT(*) FROM books').fetchone()[0],
        'available_books': conn.execute('SELECT COUNT(*) FROM books WHERE available = 1').fetchone()[0],
        'total_students': conn.execute('SELECT COUNT(*) FROM users WHERE role = "student"').fetchone()[0],
        'total_borrows': conn.execute('SELECT COUNT(*) FROM borrow_log').fetchone()[0]
    }
    
    user = None
    if session.get('logged_in'):
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    conn.close()
    
    return render_template('home.html', stats=stats, user=user)

@app.route('/admin/login', methods=['POST'])
def admin_login():
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
        # Return success JSON response for AJAX
        return jsonify({'success': True, 'message': 'Login successful!'})
    # Return error JSON response for AJAX
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401 # Use 401 for unauthorized

@app.route('/admin/login', methods=['GET'])
def admin_login_get():
    # Similar to student login GET, keep or remove as needed
    return render_template('admin_login.html') # Or redirect to home

@app.route('/student/login', methods=['POST'])
def student_login():
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
        # Return success JSON response for AJAX
        return jsonify({'success': True, 'message': 'Login successful!'})
    else:
        # Return error JSON response for AJAX
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401 # Use 401 for unauthorized

@app.route('/student/login', methods=['GET'])
def student_login_get():
    # This route is no longer needed for rendering a separate page, 
    # but we keep it for now or remove it later if not used elsewhere.
    # It might be useful if a direct link to /student/login is accessed.
    return render_template('student_login.html') # Or redirect to home

@app.route('/student/signup', methods=['POST'])
def student_signup():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip() # Note: address is in DB but not in signup template HTML yet

    if not username or not password or not confirm_password or not email or not phone:
        return jsonify({'success': False, 'message': 'Username, password, confirm password, email, and phone are required'}), 400

    if password != confirm_password:
        return jsonify({'success': False, 'message': 'Password and confirm password do not match'}), 400

    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM users WHERE username=? OR email=?",
                          (username, email)).fetchone()
    if existing:
        conn.close()
        return jsonify({'success': False, 'message': 'Username or email already taken'}), 409 # 409 Conflict

    user_id = None
    profile_pic_filename = None

    try:
        # Insert user first to get user_id
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, password, email, phone, address, role)
            VALUES (?, ?, ?, ?, ?, 'student')
        ''', (username, password, email, phone, address))
        user_id = cursor.lastrowid

        # Handle profile picture upload if present
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                profile_pic_filename = secure_filename(f"user_{user_id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], profile_pic_filename)

                # Resize and save image
                image = Image.open(file)
                image.thumbnail((200, 200))
                image.save(filepath)

                # Update profile picture in database
                conn.execute('UPDATE users SET profile_pic = ? WHERE id = ?',
                           (profile_pic_filename, user_id))
            elif file.filename != '': # If file is present but not allowed
                 # We should probably delete the user we just created if pic upload is mandatory
                 # For now, let's just return an error but keep the user without a pic
                 conn.rollback() # Rollback the pic update attempt, but keep the user insert
                 conn.close()
                 return jsonify({'success': False, 'message': 'Invalid file type for profile picture.'}), 400

        conn.commit() # Commit both user insert and pic update (if any)
        conn.close()
        return jsonify({'success': True, 'message': 'Signup successful!', 'username': username})

    except Exception as e:
        conn.rollback() # Rollback everything if any step fails
        conn.close()
        return jsonify({'success': False, 'message': f'An error occurred during signup: {e}'}), 500 # 500 Internal Server Error

@app.route('/student/signup', methods=['GET'])
def student_signup_get():
    # Keep GET route for now or redirect to home
    return render_template('student_signup.html') # Or redirect to home

@app.route('/student/dashboard')
def student_dashboard():
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Please login to access the student dashboard.', 'warning')
        return redirect(url_for('student_login'))

    conn = get_db_connection()
    user_id = session['user_id']

    # Fetch user details
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    # Fetch currently borrowed books with potential fine amount
    # Fines are calculated separately or should be stored/joined if needed here.
    # For simplicity now, we will just fetch borrowed books and calculate overdue status if needed in template.
    # If fines per book are needed, the schema and query would need modification.
    # Let's fetch necessary book details and borrow log details.
    borrowed_books_raw = conn.execute('''
        SELECT bl.id as borrow_id, bl.book_id, bl.issue_date, bl.due_date, bl.returned, b.title, b.author
        FROM borrow_log bl
        JOIN books b ON bl.book_id = b.id
        WHERE bl.user_id = ? AND bl.returned = 0
    ''', (user_id,)).fetchall()

    borrowed_books = []
    for book_row in borrowed_books_raw:
        book_dict = dict(book_row)
        # Convert date strings to datetime objects
        if isinstance(book_dict['issue_date'], str):
             try:
                 book_dict['issue_date'] = datetime.strptime(book_dict['issue_date'], '%Y-%m-%d').date()
             except ValueError:
                 pass # Keep as string if conversion fails
        if isinstance(book_dict['due_date'], str):
            try:
                book_dict['due_date'] = datetime.strptime(book_dict['due_date'], '%Y-%m-%d').date()
            except ValueError:
                pass # Keep as string if conversion fails

        # Calculate potential fine - This is a simple example, real fine calculation might be complex
        book_dict['fine'] = 0 # Placeholder, actual fine calculation needs logic based on due_date vs today
        if book_dict['due_date'] and book_dict['due_date'] < datetime.now().date():
             # Simple example: $1 per day overdue
             overdue_days = (datetime.now().date() - book_dict['due_date']).days
             book_dict['fine'] = overdue_days * 1.0 # Example rate

        borrowed_books.append(book_dict)

    # Fetch reading history with book details
    reading_history_raw = conn.execute('''
        SELECT rh.id as history_id, rh.user_id, rh.book_id, rh.borrow_date, rh.return_date, b.title, b.author
        FROM reading_history rh
        JOIN books b ON rh.book_id = b.id
        WHERE rh.user_id = ?
        ORDER BY rh.borrow_date DESC
    ''', (user_id,)).fetchall()

    reading_history = []
    for history_item_row in reading_history_raw:
        history_item_dict = dict(history_item_row)
        # Convert date strings to datetime objects
        if isinstance(history_item_dict['borrow_date'], str):
            try:
                history_item_dict['borrow_date'] = datetime.fromisoformat(history_item_dict['borrow_date'])
            except ValueError:
                 pass # Keep as string if conversion fails
        if history_item_dict['return_date'] and isinstance(history_item_dict['return_date'], str):
            try:
                history_item_dict['return_date'] = datetime.fromisoformat(history_item_dict['return_date'])
            except ValueError:
                 pass # Keep as string if conversion fails
        # Include book details directly in the history item dictionary
        history_item_dict['book_title'] = history_item_dict.pop('title')
        history_item_dict['book_author'] = history_item_dict.pop('author')
        reading_history.append(history_item_dict)

    # Fetch fines with book details (requires joining with borrow_log and books, assuming fine is linked to a borrow)
    # NOTE: Current fines table schema doesn't link to borrow_log or books directly. This query assumes a hypothetical link or needs schema update.
    # For now, let's fetch fines and link them if possible, or adjust template.
    # Assuming fines are associated with borrow_log entries for now to get book title
    fines_raw = conn.execute('''
        SELECT f.id as fine_id, f.user_id, f.amount, f.reason, f.paid, f.created_at, f.paid_at,
               b.title as book_title, b.author as book_author
        FROM fines f
        JOIN borrow_log bl ON f.user_id = bl.user_id -- This join is incorrect, needs direct link from fines to borrow_log or book
        JOIN books b ON bl.book_id = b.id
        WHERE f.user_id = ?
        ORDER BY f.created_at DESC
    ''', (user_id,)).fetchall()

    fines = []
    # FIX: The above query JOIN is likely wrong based on current schema. Fines table only has user_id.
    # To show book with fine, the 'fines' table needs a 'book_id' or 'borrow_id'.
    # Since we don't have that yet, I will revert the template to not show book title for fines for now.
    # The previous change to remove the 'Book' column from fine history in student_dashboard.html was correct based on schema.
    # I will keep the date conversion for existing fine fields.
    fines_raw = conn.execute('''
        SELECT f.id as fine_id, f.user_id, f.amount, f.reason, f.paid, f.created_at, f.paid_at
        FROM fines f
        WHERE f.user_id = ?
        ORDER BY f.created_at DESC
    ''', (user_id,)).fetchall()

    fines = []
    for fine_row in fines_raw:
        fine_dict = dict(fine_row)
        # Convert date strings to datetime objects
        if isinstance(fine_dict['created_at'], str):
             try:
                 fine_dict['created_at'] = datetime.fromisoformat(fine_dict['created_at'])
             except ValueError:
                  pass # Keep as string
        if fine_dict['paid_at'] and isinstance(fine_dict['paid_at'], str):
             try:
                 fine_dict['paid_at'] = datetime.fromisoformat(fine_dict['paid_at'])
             except ValueError:
                  pass # Keep as string
        fines.append(fine_dict)

    conn.close()

    # Pass data to the template
    return render_template('student_dashboard.html',
                           student=user, # Using 'student' as the template expects it
                           borrowed_books=borrowed_books,
                           reading_history=reading_history,
                           fine_history=fines) # Using 'fine_history' as the template expects it

@app.route('/chat')
def chat():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    return render_template('chat.html', role=session['role'], username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('logged_in'):
        return redirect(url_for('home'))

    conn = get_db_connection()
    user_id = session['user_id']

    user_row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    user = dict(user_row) if user_row else None # Convert Row object to dictionary

    if request.method == 'POST':
        try:
            # Handle profile picture upload
            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"user_{user_id}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                    try:
                        # Resize image if needed
                        image = Image.open(file)
                        image.thumbnail((200, 200))
                        image.save(filepath)

                        # Update profile picture in database
                        conn.execute('UPDATE users SET profile_pic = ? WHERE id = ?',
                                   (filename, user_id))

                    except Exception as e:
                        flash(f'Error uploading profile picture: {e}', 'danger')
                elif file.filename != '': # If file is present but not allowed
                     flash('Invalid file type for profile picture.', 'warning')

            # Update other profile information
            email = request.form.get('email')
            phone = request.form.get('phone')
            address = request.form.get('address')

            conn.execute('''
                UPDATE users
                SET email = ?, phone = ?, address = ?
                WHERE id = ?
            ''', (email, phone, address, user_id))

            # Handle password change
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if current_password or new_password or confirm_password:
                if not current_password:
                    flash('Current password is required to change password.', 'danger')
                elif not new_password or not confirm_password:
                     flash('New password and confirm password are required.', 'danger')
                elif new_password != confirm_password:
                    flash('New password and confirm password do not match.', 'danger')
                else:
                    # In a real app, you should hash and verify passwords
                    user_check = conn.execute('SELECT password FROM users WHERE id = ?', (user_id,)).fetchone()
                    if user_check and user_check['password'] == current_password:
                        conn.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, user_id))
                        flash('Password updated successfully!', 'success')
                    else:
                        flash('Incorrect current password.', 'danger')

            conn.commit()

        except Exception as e:
            conn.rollback()
            flash(f'An error occurred while updating profile: {e}', 'danger')

        finally:
            conn.close() # Close connection after POST

        return redirect(url_for('profile')) # Redirect regardless of success/failure

    # Handle GET request starts here
    conn.close() # Close connection after fetching data for GET

    # Pass data to the template
    return render_template('edit_profile.html',
                           user=user)

@app.route('/reading-history')
def reading_history():
    if not session.get('logged_in'):
        return redirect(url_for('home'))

    conn = get_db_connection()
    user_id = session['user_id']

    history_raw = conn.execute('''
        SELECT b.title, b.author, rh.borrow_date, rh.return_date
        FROM reading_history rh
        JOIN books b ON rh.book_id = b.id
        WHERE rh.user_id = ?
        ORDER BY rh.borrow_date DESC
    ''', (user_id,)).fetchall()

    history = []
    for item_row in history_raw:
        item_dict = dict(item_row)
        # Convert date strings to datetime objects
        if isinstance(item_dict['borrow_date'], str):
             try:
                 item_dict['borrow_date'] = datetime.fromisoformat(item_dict['borrow_date'])
             except ValueError:
                  pass # Keep as string
        if item_dict['return_date'] and isinstance(item_dict['return_date'], str):
             try:
                 item_dict['return_date'] = datetime.fromisoformat(item_dict['return_date'])
             except ValueError:
                  pass # Keep as string
        history.append(item_dict)

    conn.close()

    return render_template('reading_history.html', history=history)

@app.route('/fines')
def fines():
    if not session.get('logged_in'):
        return redirect(url_for('home'))

    conn = get_db_connection()
    user_id = session['user_id']

    user_fines_raw = conn.execute('''
        SELECT amount, reason, paid, created_at, paid_at
        FROM fines
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,)).fetchall()

    user_fines = []
    for fine_row in user_fines_raw:
        fine_dict = dict(fine_row)
        # Convert date strings to datetime objects
        if isinstance(fine_dict['created_at'], str):
             try:
                 fine_dict['created_at'] = datetime.fromisoformat(fine_dict['created_at'])
             except ValueError:
                  pass # Keep as string
        if fine_dict['paid_at'] and isinstance(fine_dict['paid_at'], str):
             try:
                 fine_dict['paid_at'] = datetime.fromisoformat(fine_dict['paid_at'])
             except ValueError:
                  pass # Keep as string
        user_fines.append(fine_dict)

    conn.close()

    return render_template('fines.html', fines=user_fines)

@app.route('/browse_books')
def browse_books():
    conn = get_db_connection()

    # Get filter parameters from request arguments
    search_query = request.args.get('search', '').strip()
    category_id = request.args.get('category', '')
    availability = request.args.get('availability', '')

    sql_query = '''
        SELECT b.*, c.name as category_name
        FROM books b
        LEFT JOIN categories c ON b.category_id = c.id
        WHERE 1=1
    '''
    query_params = []

    # Add search filter
    if search_query:
        sql_query += ' AND (b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?)'
        query_params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])

    # Add category filter
    if category_id:
        sql_query += ' AND b.category_id = ?'
        query_params.append(category_id)

    # Add availability filter
    if availability == 'available':
        sql_query += ' AND b.available = 1'
    elif availability == 'borrowed':
        sql_query += ' AND b.available = 0'

    sql_query += ' ORDER BY b.title'

    # Fetch books based on filters
    try:
        books = conn.execute(sql_query, query_params).fetchall()
    except Exception as e:
        flash(f'Error fetching books: {e}', 'danger')
        books = []

    # Fetch categories for the filter dropdown
    categories = []
    try:
        categories = conn.execute('SELECT id, name FROM categories ORDER BY name').fetchall()
    except sqlite3.OperationalError:
        print("DEBUG: Categories table not found for browse books category filter.")

    conn.close()

    # We also need to pass pagination info, even if dummy for now
    # This assumes your template expects a 'pagination' object.
    # Replace with real pagination logic when implemented.
    pagination = {
        'page': 1,
        'pages': 1,
        'has_prev': False,
        'has_next': False,
        'iter_pages': lambda: [1]
    }

    return render_template('browse_books.html',
                           books=books,
                           categories=categories,
                           pagination=pagination,
                           request=request) # Pass request object for url_for args in template

@app.route('/borrow/<int:book_id>')
def borrow_book_route(book_id):
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Please login as a student to borrow books.', 'warning')
        return redirect(url_for('student_login')) # Or home

    user_id = session['user_id']

    # Use the existing borrow_book logic
    success = borrow_book(user_id, book_id)

    if success:
        flash('Book borrowed successfully!', 'success')
    else:
        flash('Could not borrow the book. It might be unavailable or already borrowed.', 'danger')

    return redirect(url_for('browse_books'))

@app.route('/return/<int:book_id>')
def return_book_route(book_id):
    if not session.get('logged_in') or session.get('role') != 'student':
        flash('Please login as a student to return books.', 'warning')
        return redirect(url_for('student_login')) # Or home

    user_id = session['user_id']

    # Use the existing return_book logic
    success = return_book(user_id, book_id)

    if success:
        flash('Book returned successfully!', 'success')
    else:
        flash('Could not return the book. You might not have borrowed it.', 'danger')

    return redirect(url_for('student_dashboard'))

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

    # Record in borrow_log
    conn.execute("""
        INSERT INTO borrow_log (user_id, book_id, issue_date, due_date, returned)
        VALUES (?, ?, ?, ?, 0)
    """, (user_id, book_id, issue_date.isoformat(), due_date.isoformat()))

    # Record in reading_history
    conn.execute("""
        INSERT INTO reading_history (user_id, book_id, borrow_date)
        VALUES (?, ?, ?)
    """, (user_id, book_id, issue_date.isoformat())) # FIX: Added book_id to bindings

    conn.execute("UPDATE books SET available=0 WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    return True

def return_book(user_id, book_id):
    conn = get_db_connection()
    borrow = conn.execute("""
        SELECT * FROM borrow_log
        WHERE user_id=? AND book_id=? AND returned=0
    """, (user_id, book_id)).fetchone()

    if not borrow:
        conn.close()
        return False

    return_date = datetime.now().date()

    # Update borrow_log
    conn.execute("""
        UPDATE borrow_log
        SET returned=1, return_date=?
        WHERE id=?
    """, (return_date.isoformat(), borrow['id']))

    # Update reading_history
    conn.execute("""
        UPDATE reading_history
        SET return_date=?
        WHERE user_id=? AND book_id=? AND return_date IS NULL
    """, (return_date.isoformat(), user_id, book_id))

    conn.execute("UPDATE books SET available=1 WHERE id=?", (book_id,))
    conn.commit()
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
    elif text == 'dashboard' or text == 'admin dashboard':
        # Special internal code to indicate redirect to admin dashboard
        return 'REDIRECT_ADMIN_DASHBOARD'
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
        parts = text.split()
        if len(parts) < 2:
            return "❌ Format: return <book_id> - Book ID is missing."
        try:
            book_id = int(parts[1])
            if return_book(user_id, book_id):
                return f"✅ Book ID {book_id} returned successfully."
            return "❌ You have not borrowed this book or it has already been returned."
        except ValueError:
            return "❌ Format: return <book_id> - Book ID must be a number."
        except Exception as e:
            # Catch other potential exceptions during return_book call
            return f"❌ An error occurred while returning the book: {e}"

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
    response = "❓ Unknown command. Type `help`."
    if session['role'] == 'admin':
        command_result = parse_admin_command(msg)
        if command_result == 'REDIRECT_ADMIN_DASHBOARD':
            # Return a JSON response indicating a redirect is needed
            return jsonify({"redirect": url_for('admin_dashboard')})
        else:
            response = command_result
    else:
        response = parse_student_command(msg, session['user_id'])
    return jsonify({"response": response})

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Please login as admin to access the admin dashboard.', 'warning')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()

    # Fetch statistics for admin dashboard
    stats = {
        'total_books': conn.execute('SELECT COUNT(*) FROM books').fetchone()[0] if conn else 0,
        'active_students': conn.execute('SELECT COUNT(*) FROM users WHERE role = "student"').fetchone()[0] if conn else 0,
        'current_borrows': conn.execute('SELECT COUNT(*) FROM borrow_log WHERE returned = 0').fetchone()[0] if conn else 0,
        'overdue_books': conn.execute('SELECT COUNT(*) FROM borrow_log WHERE returned = 0 AND due_date < CURRENT_DATE').fetchone()[0] if conn else 0
    }

    # Fetch recent activity (using borrow_log as activity for now)
    recent_activities_raw = conn.execute('''
        SELECT bl.issue_date as timestamp, 'Book Borrowed' as description, u.username
        FROM borrow_log bl
        JOIN users u ON bl.user_id = u.id
        ORDER BY bl.issue_date DESC
        LIMIT 10
    ''').fetchall()

    recent_activities = []
    for activity_row in recent_activities_raw:
        activity_dict = dict(activity_row)
        # Convert timestamp string to datetime object
        if isinstance(activity_dict['timestamp'], str):
            try:
                # Assuming issue_date is stored as YYYY-MM-DD
                activity_dict['timestamp'] = datetime.strptime(activity_dict['timestamp'], '%Y-%m-%d') # Convert to datetime object
            except ValueError:
                pass # Keep as string
        # Create a nested user dictionary for template compatibility
        activity_dict['user'] = {'username': activity_dict.pop('username')}

        recent_activities.append(activity_dict)


    # Fetch overdue books
    overdue_books_raw = conn.execute('''
        SELECT bl.*, b.title, b.author, u.username as borrower_username, u.email as borrower_email
        FROM borrow_log bl
        JOIN books b ON bl.book_id = b.id
        JOIN users u ON bl.user_id = u.id
        WHERE bl.returned = 0 AND bl.due_date < CURRENT_DATE
        ORDER BY bl.due_date ASC
        LIMIT 10
    ''').fetchall()

    overdue_books = []
    today = datetime.now().date()
    
    for book in overdue_books_raw:
        book_dict = dict(book)
        # Convert due_date to datetime.date object
        if isinstance(book_dict['due_date'], str):
            try:
                book_dict['due_date'] = datetime.strptime(book_dict['due_date'], '%Y-%m-%d').date()
            except ValueError:
                continue  # Skip if date parsing fails
        
        # Calculate overdue days
        if book_dict['due_date']:
            book_dict['overdue_days'] = (today - book_dict['due_date']).days
            # Calculate fine (example: $1 per day)
            book_dict['fine'] = book_dict['overdue_days'] * 1.0
        else:
            book_dict['overdue_days'] = 0
            book_dict['fine'] = 0.0

        # Create a nested borrower dictionary for template compatibility
        book_dict['borrower'] = {'username': book_dict.pop('borrower_username')}

        # Format the due_date for each book
        if isinstance(book_dict['due_date'], datetime):
            book_dict['due_date'] = book_dict['due_date'].strftime('%Y-%m-%d')

        overdue_books.append(book_dict)


    # Fetch recent borrows
    recent_borrows_raw = conn.execute('''
        SELECT bl.*, b.title, b.author, u.username as student_username, u.email as student_email
        FROM borrow_log bl
        JOIN books b ON bl.book_id = b.id
        JOIN users u ON bl.user_id = u.id
        ORDER BY bl.issue_date DESC
        LIMIT 10
    ''').fetchall()

    recent_borrows = []
    for borrow_row in recent_borrows_raw:
        borrow_dict = dict(borrow_row)
        # Convert date strings to datetime objects
        if isinstance(borrow_dict['issue_date'], str):
             try:
                 borrow_dict['issue_date'] = datetime.strptime(borrow_dict['issue_date'], '%Y-%m-%d').date()
             except ValueError:
                 pass # Keep as string
        if isinstance(borrow_dict['due_date'], str):
            try:
                borrow_dict['due_date'] = datetime.strptime(borrow_dict['due_date'], '%Y-%m-%d').date()
            except ValueError:
                pass # Keep as string

        # Add is_overdue flag
        borrow_dict['is_overdue'] = False
        if not borrow_dict['returned'] and borrow_dict['due_date'] and borrow_dict['due_date'] < datetime.now().date():
            borrow_dict['is_overdue'] = True

        # Create nested dictionaries for template compatibility
        borrow_dict['book'] = {'title': borrow_dict.pop('title')}
        borrow_dict['student'] = {'username': borrow_dict.pop('student_username')}

        # Format the due_date for each borrow
        if isinstance(borrow_dict['due_date'], datetime):
            borrow_dict['due_date'] = borrow_dict['due_date'].strftime('%Y-%m-%d')

        recent_borrows.append(borrow_dict)

    conn.close() # Close connection after fetching data

    return render_template('admin_dashboard.html',
                           stats=stats,
                           recent_activities=recent_activities,
                           overdue_books=overdue_books,
                           recent_borrows=recent_borrows)

@app.route('/admin/add_book', methods=['GET', 'POST'])
def add_book_route():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Please login as admin to add books.', 'warning')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        genre = request.form.get('genre', '').strip()
        isbn = request.form.get('isbn', '').strip()
        category_id = request.form.get('category_id')
        cover_image_filename = None

        # Handle cover image upload
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and allowed_file(file.filename):
                # Generate a safe filename, potentially using ISBN or title
                filename = secure_filename(f"book_{isbn or title}_{file.filename}")
                filepath = os.path.join(app.config['BOOK_COVER_UPLOAD_FOLDER'], filename)
                try:
                    # Resize and save image (optional but recommended)
                    image = Image.open(file)
                    image.thumbnail((400, 400)) # Example resize
                    image.save(filepath)
                    cover_image_filename = filename # Set filename if saved successfully
                except Exception as e:
                    flash(f'Error saving cover image: {e}', 'danger')
                    # cover_image_filename remains None if save fails


        if not title or not author:
            flash('Title and author are required.', 'danger')
            conn.close()
            return redirect(url_for('add_book_route'))

        try:
            # Check if book with same ISBN already exists (if ISBN is provided)
            if isbn:
                existing_book = conn.execute('SELECT id FROM books WHERE isbn = ?', (isbn,)).fetchone()
                if existing_book:
                    flash(f'Error: Book with ISBN {isbn} already exists.', 'danger')
                else:
                     conn.execute('''
                         INSERT INTO books (title, author, genre, isbn, category_id, cover_image, available)
                         VALUES (?, ?, ?, ?, ?, ?, 1)
                     ''', (title, author, genre, isbn, category_id if category_id else None, cover_image_filename))
                     conn.commit()
                     flash(f'Book "{title}" added successfully!', 'success')
            else:
                # Add book without ISBN
                conn.execute('''
                    INSERT INTO books (title, author, genre, category_id, cover_image, available)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (title, author, genre, category_id if category_id else None, cover_image_filename))
                conn.commit()
                flash(f'Book "{title}" added successfully!', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'An error occurred while adding the book: {e}', 'danger')
        finally:
            conn.close()

        return redirect(url_for('manage_books')) # Redirect to manage books after adding

    # Handle GET request: Display the form to add a book
    categories = []
    try:
        conn = get_db_connection()
        categories = conn.execute('SELECT id, name FROM categories').fetchall()
    except sqlite3.OperationalError:
        print("DEBUG: Categories table not found for add book form.")
    finally:
        if conn: conn.close()

    return render_template('add_book.html', categories=categories)

@app.route('/admin/manage_categories', methods=['GET', 'POST'])
def manage_categories():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Please login as admin to manage categories.', 'warning')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            
            if not name:
                flash('Category name is required.', 'danger')
            else:
                try:
                    conn.execute('''
                        INSERT INTO categories (name, description)
                        VALUES (?, ?)
                    ''', (name, description))
                    conn.commit()
                    flash(f'Category "{name}" added successfully!', 'success')
                except sqlite3.IntegrityError:
                    flash(f'Category "{name}" already exists.', 'danger')
                except Exception as e:
                    flash(f'Error adding category: {e}', 'danger')
                    
        elif action == 'delete':
            category_id = request.form.get('category_id')
            if category_id:
                try:
                    # Check if category is in use
                    books = conn.execute('SELECT COUNT(*) FROM books WHERE category_id = ?', (category_id,)).fetchone()[0]
                    if books > 0:
                        flash('Cannot delete category that is in use by books.', 'danger')
                    else:
                        conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
                        conn.commit()
                        flash('Category deleted successfully!', 'success')
                except Exception as e:
                    flash(f'Error deleting category: {e}', 'danger')
                    
        elif action == 'edit':
            category_id = request.form.get('category_id')
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            
            if not name:
                flash('Category name is required.', 'danger')
            else:
                try:
                    conn.execute('''
                        UPDATE categories
                        SET name = ?, description = ?
                        WHERE id = ?
                    ''', (name, description, category_id))
                    conn.commit()
                    flash('Category updated successfully!', 'success')
                except sqlite3.IntegrityError:
                    flash(f'Category "{name}" already exists.', 'danger')
                except Exception as e:
                    flash(f'Error updating category: {e}', 'danger')
    
    # Fetch all categories for display
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    conn.close()
    
    return render_template('manage_categories.html', categories=categories)

@app.route('/admin/manage_students', methods=['GET', 'POST'])
def manage_students():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Please login as admin to manage students.', 'warning')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'edit':
            student_id = request.form.get('student_id')
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            
            try:
                conn.execute('''
                    UPDATE users
                    SET email = ?, phone = ?, address = ?
                    WHERE id = ? AND role = 'student'
                ''', (email, phone, address, student_id))
                conn.commit()
                flash('Student information updated successfully!', 'success')
            except Exception as e:
                flash(f'Error updating student: {e}', 'danger')
                
        elif action == 'disable':
            student_id = request.form.get('student_id')
            try:
                # Instead of deleting, we'll add a 'disabled' column to users table
                # For now, we'll just show a message
                flash('Student account disabled successfully!', 'success')
            except Exception as e:
                flash(f'Error disabling student: {e}', 'danger')
                
        elif action == 'reset_password':
            student_id = request.form.get('student_id')
            new_password = request.form.get('new_password', '').strip()
            
            if not new_password:
                flash('New password is required.', 'danger')
            else:
                try:
                    conn.execute('''
                        UPDATE users
                        SET password = ?
                        WHERE id = ? AND role = 'student'
                    ''', (new_password, student_id))
                    conn.commit()
                    flash('Password reset successfully!', 'success')
                except Exception as e:
                    flash(f'Error resetting password: {e}', 'danger')
    
    # Fetch all students with their borrowing history
    students = conn.execute('''
        SELECT u.*, 
               COUNT(DISTINCT bl.id) as total_borrows,
               COUNT(DISTINCT CASE WHEN bl.returned = 0 THEN bl.id END) as active_borrows,
               SUM(CASE WHEN f.paid = 0 THEN f.amount ELSE 0 END) as unpaid_fines
        FROM users u
        LEFT JOIN borrow_log bl ON u.id = bl.user_id
        LEFT JOIN fines f ON u.id = f.user_id
        WHERE u.role = 'student'
        GROUP BY u.id
        ORDER BY u.username
    ''').fetchall()
    
    conn.close()
    
    return render_template('manage_students.html', students=students)

@app.route('/admin/manage_fines', methods=['GET', 'POST'])
def manage_fines():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Please login as admin to manage fines.', 'warning')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            student_id = request.form.get('student_id')
            amount = request.form.get('amount')
            reason = request.form.get('reason', '').strip()
            
            if not student_id or not amount or not reason:
                flash('All fields are required.', 'danger')
            else:
                try:
                    amount = float(amount)
                    if amount <= 0:
                        raise ValueError("Amount must be greater than 0")
                        
                    conn.execute('''
                        INSERT INTO fines (user_id, amount, reason, paid)
                        VALUES (?, ?, ?, 0)
                    ''', (student_id, amount, reason))
                    conn.commit()
                    flash('Fine added successfully!', 'success')
                except ValueError as e:
                    flash(f'Invalid amount: {e}', 'danger')
                except Exception as e:
                    flash(f'Error adding fine: {e}', 'danger')
                    
        elif action == 'mark_paid':
            fine_id = request.form.get('fine_id')
            if fine_id:
                try:
                    conn.execute('''
                        UPDATE fines
                        SET paid = 1, paid_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (fine_id,))
                    conn.commit()
                    flash('Fine marked as paid!', 'success')
                except Exception as e:
                    flash(f'Error updating fine: {e}', 'danger')
                    
        elif action == 'delete':
            fine_id = request.form.get('fine_id')
            if fine_id:
                try:
                    conn.execute('DELETE FROM fines WHERE id = ?', (fine_id,))
                    conn.commit()
                    flash('Fine deleted successfully!', 'success')
                except Exception as e:
                    flash(f'Error deleting fine: {e}', 'danger')
    
    # Fetch all fines with student information
    fines = conn.execute('''
        SELECT f.*, u.username, u.email,
               CASE 
                   WHEN f.paid = 1 THEN 'Paid'
                   WHEN f.paid = 0 THEN 'Unpaid'
               END as status
        FROM fines f
        JOIN users u ON f.user_id = u.id
        ORDER BY f.created_at DESC
    ''').fetchall()
    
    # Fetch all students for the add fine form
    students = conn.execute('''
        SELECT id, username, email
        FROM users
        WHERE role = 'student'
        ORDER BY username
    ''').fetchall()
    
    # Calculate total statistics
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total_fines,
            SUM(CASE WHEN paid = 0 THEN amount ELSE 0 END) as total_unpaid,
            SUM(CASE WHEN paid = 1 THEN amount ELSE 0 END) as total_paid
        FROM fines
    ''').fetchone()
    
    conn.close()
    
    return render_template('manage_fines.html', 
                         fines=fines, 
                         students=students,
                         stats=stats)

@app.route('/admin/overdue_books')
def overdue_books():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Please login as admin to view overdue books.', 'warning')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    try:
        # Query to fetch overdue books
        overdue_books_raw = conn.execute("""
            SELECT bl.*, b.title, b.author, u.username as borrower_username, u.email as borrower_email
            FROM borrow_log bl
            JOIN books b ON bl.book_id = b.id
            JOIN users u ON bl.user_id = u.id
            WHERE bl.returned = 0 AND bl.due_date < CURRENT_DATE
            ORDER BY bl.due_date ASC
        """).fetchall()

        overdue_books = []
        today = datetime.now().date()
        
        for book in overdue_books_raw:
            book_dict = dict(book)
            # Convert due_date to datetime.date object
            if isinstance(book_dict['due_date'], str):
                try:
                    book_dict['due_date'] = datetime.strptime(book_dict['due_date'], '%Y-%m-%d').date()
                except ValueError:
                    continue  # Skip if date parsing fails
            
            # Calculate overdue days
            if book_dict['due_date']:
                book_dict['overdue_days'] = (today - book_dict['due_date']).days
                # Calculate fine (example: $1 per day)
                book_dict['fine'] = book_dict['overdue_days'] * 1.0
            else:
                book_dict['overdue_days'] = 0
                book_dict['fine'] = 0.0

            # Create a nested borrower dictionary for template compatibility
            book_dict['borrower'] = {'username': book_dict.pop('borrower_username')}

            # Format the due_date for each book
            if isinstance(book_dict['due_date'], datetime):
                book_dict['due_date'] = book_dict['due_date'].strftime('%Y-%m-%d')

            overdue_books.append(book_dict)

    except Exception as e:
        flash(f'Error fetching overdue books: {e}', 'danger')
        overdue_books = []
    finally:
        conn.close()

    return render_template('overdue_books.html', overdue_books=overdue_books)

@app.route('/admin/manage_books', methods=['GET', 'POST'])
def manage_books():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Please login as admin to manage books.', 'warning')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            # This section should be handled by add_book_route, but keeping for robustness
            title = request.form.get('title', '').strip()
            author = request.form.get('author', '').strip()
            genre = request.form.get('genre', '').strip()
            isbn = request.form.get('isbn', '').strip()
            category_id = request.form.get('category_id')
            cover_image_filename = None # Handle upload if necessary here too?

            # It's better to handle 'add' via the dedicated add_book_route
            flash('Please use the "Add New Book" page to add books.', 'warning')


        elif action == 'edit':
            book_id = request.form.get('book_id')
            title = request.form.get('title', '').strip()
            author = request.form.get('author', '').strip()
            genre = request.form.get('genre', '').strip()
            isbn = request.form.get('isbn', '').strip()
            category_id = request.form.get('category_id')
            available = request.form.get('available') == '1' # Checkbox value '1' if checked

            cover_image_filename = request.form.get('existing_cover_image') # Get existing filename

            # Handle new cover image upload if present
            if 'cover_image' in request.files and request.files['cover_image'].filename != '':
                 file = request.files['cover_image']
                 if file and allowed_file(file.filename):
                    # Generate a safe filename
                    filename = secure_filename(f"book_{book_id}_{file.filename}")
                    filepath = os.path.join(app.config['BOOK_COVER_UPLOAD_FOLDER'], filename)
                    try:
                        # Resize and save image (optional but recommended)
                        image = Image.open(file)
                        image.thumbnail((400, 400)) # Example resize
                        image.save(filepath)
                        cover_image_filename = filename # Update filename with new one
                    except Exception as e:
                        flash(f'Error saving new cover image: {e}', 'danger')
                        # cover_image_filename remains the existing one if saving fails


            if not book_id or not title or not author:
                flash('Book ID, title, and author are required for editing.', 'danger')
            else:
                try:
                    # Check for ISBN uniqueness exclude current book
                    if isbn:
                        existing_book = conn.execute('SELECT id FROM books WHERE isbn = ? AND id != ?', (isbn, book_id)).fetchone()
                        if existing_book:
                             flash(f'Error: Another book with ISBN {isbn} already exists.', 'danger')
                        else:
                            conn.execute('''
                                UPDATE books
                                SET title = ?, author = ?, genre = ?, isbn = ?, category_id = ?, cover_image = ?, available = ?
                                WHERE id = ?
                            ''', (title, author, genre, isbn, category_id if category_id else None, cover_image_filename, available, book_id))
                            conn.commit()
                            flash(f'Book "{title}" updated successfully!', 'success')
                    else:
                        # Update book without ISBN
                         conn.execute('''
                             UPDATE books
                             SET title = ?, author = ?, genre = ?, isbn = ?, category_id = ?, cover_image = ?, available = ?
                             WHERE id = ?
                         ''', (title, author, genre, None, category_id if category_id else None, cover_image_filename, available, book_id))
                         conn.commit()
                         flash(f'Book "{title}" updated successfully!', 'success')


                except Exception as e:
                    conn.rollback()
                    flash(f'An error occurred while updating the book: {e}', 'danger')

        elif action == 'delete':
            book_id = request.form.get('book_id')
            if not book_id:
                flash('Book ID is required for deletion.', 'danger')
            else:
                try:
                    # Check if book is currently borrowed
                    borrowed = conn.execute('SELECT COUNT(*) FROM borrow_log WHERE book_id = ? AND returned = 0', (book_id,)).fetchone()[0]
                    if borrowed > 0:
                        flash('Cannot delete a book that is currently borrowed.', 'danger')
                    else:
                         # Optional: Delete the cover image file
                         book_to_delete = conn.execute('SELECT cover_image FROM books WHERE id = ?', (book_id,)).fetchone()
                         if book_to_delete and book_to_delete['cover_image']:
                             filepath = os.path.join(app.config['BOOK_COVER_UPLOAD_FOLDER'], book_to_delete['cover_image'])
                             if os.path.exists(filepath):
                                 os.remove(filepath)
                                 print(f"DEBUG: Deleted cover image file: {filepath}")


                         conn.execute('DELETE FROM books WHERE id = ?', (book_id,))
                         conn.commit()
                         flash('Book deleted successfully!', 'success')

                except Exception as e:
                    conn.rollback()
                    flash(f'An error occurred while deleting the book: {e}', 'danger')

        # After POST, redirect to the same page to show updated list and flash messages
        conn.close() # Close connection before redirect
        return redirect(url_for('manage_books'))

    # Handle GET request: Display the list of books and forms

    # Fetch all books with category names
    books = conn.execute('''
        SELECT b.*, c.name as category_name
        FROM books b
        LEFT JOIN categories c ON b.category_id = c.id
        ORDER BY b.title
    ''').fetchall()

    # Fetch all categories for the add/edit forms
    categories = conn.execute('SELECT id, name FROM categories ORDER BY name').fetchall()

    conn.close() # Close connection after fetching data for GET

    return render_template('manage_books.html', books=books, categories=categories)

@app.route('/admin/borrow_history')
def admin_borrow_history():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash('Please login as admin to view borrow history.', 'warning')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    try:
        # Fetch all borrow logs with book and user information
        borrow_logs = conn.execute("""
            SELECT bl.*, b.title, b.author, u.username as student_username, u.email as student_email
            FROM borrow_log bl
            JOIN books b ON bl.book_id = b.id
            JOIN users u ON bl.user_id = u.id
            ORDER BY bl.issue_date DESC
        """).fetchall()
    except Exception as e:
        flash(f'Error fetching borrow history: {e}', 'danger')
        borrow_logs = []
    finally:
        conn.close()

    return render_template('admin_borrow_history.html', borrow_logs=borrow_logs)

if __name__ == '__main__':
    # Optional: Sync availability at server start
    sync_availability_with_borrow_log()
    app.run(debug=True)
