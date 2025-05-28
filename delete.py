import sqlite3

conn = sqlite3.connect('books.db')
cursor = conn.cursor()

# Delete all existing books
cursor.execute("DELETE FROM books")

# Reset auto-increment counter for 'books' table
cursor.execute("DELETE FROM sqlite_sequence WHERE name='books'")

conn.commit()
conn.close()

print("Deleted all books and reset auto-increment counter.")
