import sqlite3

conn = sqlite3.connect('books.db')
cursor = conn.cursor()

# List of 50 books (title, author, genre, available)
books = [
    ('Introduction to Algorithms', 'Thomas H. Cormen', 'Computer Science', 'Yes'),
    ('Physics for Scientists and Engineers', 'Raymond A. Serway', 'Physics', 'Yes'),
    ('Organic Chemistry', 'Paula Yurkanis Bruice', 'Chemistry', 'Yes'),
    ('Engineering Mathematics', 'B.S. Grewal', 'Mathematics', 'Yes'),
    ('Signals and Systems', 'Alan V. Oppenheim', 'Electronics', 'Yes'),
    ('Data Structures and Algorithms in Python', 'Michael T. Goodrich', 'Computer Science', 'Yes'),
    ('Mechanics of Materials', 'Ferdinand P. Beer', 'Mechanical', 'Yes'),
    ('The Art of Electronics', 'Paul Horowitz', 'Electronics', 'Yes'),
    ('Environmental Engineering', 'Howard S. Peavy', 'Civil Engineering', 'Yes'),
    ('Fundamentals of Thermodynamics', 'Richard E. Sonntag', 'Mechanical', 'Yes'),
    ('Operating System Concepts', 'Abraham Silberschatz', 'Computer Science', 'Yes'),
    ('Linear Algebra and Its Applications', 'Gilbert Strang', 'Mathematics', 'Yes'),
    ('Strength of Materials', 'S.S. Bhavikatti', 'Civil Engineering', 'Yes'),
    ('Computer Networks', 'Andrew S. Tanenbaum', 'Computer Science', 'Yes'),
    ('Introduction to Machine Learning', 'Ethem Alpaydin', 'AI/ML', 'Yes'),

    # Additional 35 books
    ('Digital Logic and Computer Design', 'Morris Mano', 'Computer Engineering', 'Yes'),
    ('Thermodynamics: An Engineering Approach', 'Yunus A. Çengel', 'Mechanical', 'Yes'),
    ('Probability and Statistics for Engineers', 'Richard L. Scheaffer', 'Statistics', 'Yes'),
    ('Database System Concepts', 'Abraham Silberschatz', 'Computer Science', 'Yes'),
    ('Control Systems Engineering', 'Norman S. Nise', 'Electrical', 'Yes'),
    ('Artificial Intelligence: A Modern Approach', 'Stuart Russell', 'AI/ML', 'No'),
    ('Electrical Machinery Fundamentals', 'Stephen J. Chapman', 'Electrical', 'Yes'),
    ('Discrete Mathematics and Its Applications', 'Kenneth H. Rosen', 'Mathematics', 'Yes'),
    ('Data Mining: Concepts and Techniques', 'Jiawei Han', 'Computer Science', 'Yes'),
    ('Concrete Technology', 'M.S. Shetty', 'Civil Engineering', 'Yes'),
    ('Software Engineering', 'Ian Sommerville', 'Computer Science', 'Yes'),
    ('Fluid Mechanics', 'Frank M. White', 'Mechanical', 'No'),
    ('Computer Architecture: A Quantitative Approach', 'John L. Hennessy', 'Computer Engineering', 'Yes'),
    ('Engineering Economics', 'Leland Blank', 'Engineering', 'Yes'),
    ('Introduction to Quantum Mechanics', 'David J. Griffiths', 'Physics', 'Yes'),
    ('Structural Analysis', 'Russell C. Hibbeler', 'Civil Engineering', 'Yes'),
    ('Power System Analysis', 'Hadi Saadat', 'Electrical', 'Yes'),
    ('Compiler Design', 'Alfred V. Aho', 'Computer Science', 'Yes'),
    ('Heat and Mass Transfer', 'J.P. Holman', 'Mechanical', 'Yes'),
    ('Principles of Communication Systems', 'Herbert Taub', 'Electronics', 'Yes'),
    ('Embedded Systems Design', 'Peter Marwedel', 'Computer Engineering', 'Yes'),
    ('Environmental Chemistry', 'Stanley E. Manahan', 'Chemistry', 'Yes'),
    ('Machine Learning', 'Tom M. Mitchell', 'AI/ML', 'No'),
    ('Civil Engineering Materials', 'Shashi K. Gupta', 'Civil Engineering', 'Yes'),
    ('Neural Networks and Deep Learning', 'Michael Nielsen', 'AI/ML', 'Yes'),
    ('Advanced Engineering Mathematics', 'Erwin Kreyszig', 'Mathematics', 'Yes'),
    ('Modern Control Engineering', 'Katsuhiko Ogata', 'Electrical', 'Yes'),
    ('Software Testing: Principles and Practices', 'Srinivasan Desikan', 'Computer Science', 'Yes'),
    ('Principles of Electrical Machines', 'P.S. Bimbhra', 'Electrical', 'Yes'),
    ('Structural Dynamics', 'Mario Paz', 'Civil Engineering', 'Yes'),
    ('Computer Vision: Algorithms and Applications', 'Richard Szeliski', 'Computer Science', 'Yes'),
    ('Robotics: Control, Sensing, Vision, and Intelligence', 'K.S. Fu', 'Mechanical', 'Yes'),
    ('Optics', 'Eugene Hecht', 'Physics', 'Yes'),
    ('Renewable Energy Engineering', 'Rufus K. Ahulu', 'Engineering', 'Yes'),
    ('Cybersecurity and Cyberwar', 'P.W. Singer', 'Computer Science', 'Yes'),
]

cursor.executemany("INSERT INTO books (title, author, genre, available) VALUES (?, ?, ?, ?)", books)

conn.commit()
conn.close()

print("50 books added successfully with auto-incremented IDs starting from 1!")