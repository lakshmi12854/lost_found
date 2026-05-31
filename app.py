import os  
from flask import Flask, render_template, request, redirect, session, send_from_directory
from werkzeug.utils import secure_filename
import sqlite3
from flask_mail import Mail, Message
from difflib import SequenceMatcher

app = Flask(__name__)
# Uses environment variable if found, otherwise falls back to your string
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key")

# ================= MAIL CONFIG =================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME", "anjulakshmi48@gmail.com")
# Using environment variable for security, falling back to your app password
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD", "nncr ibfd fwxv kevx")
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("MAIL_USERNAME", "anjulakshmi48@gmail.com")

mail = Mail(app)

# ================= UPLOAD =================
UPLOAD_FOLDER = '/tmp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect('/tmp/users.db')   
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            password TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            description TEXT,
            contact TEXT,
            image TEXT,
            user_email TEXT
        )
    ''')

    conn.commit()
    conn.close()

# Initialize tables automatically on launch
init_db()


# ================= SIMILARITY =================
def is_similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() > 0.6


# ================= HOME =================
@app.route('/')
def home():
    return render_template('index.html')


# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('/tmp/users.db')
        cur = conn.cursor()

        cur.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                    (name, email, password))

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('/tmp/users.db')
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=? AND password=?",
                    (email, password))

        user = cur.fetchone()
        conn.close()

        if user:
            session['user'] = email

            try:
                msg = Message("Login Alert", recipients=[email])
                msg.body = "You have successfully logged in."
                mail.send(msg)
            except Exception as e:
                print("Login Email Error:", e)

            return redirect('/items')

        return "Invalid Credentials ❌"

    return render_template('login.html')


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ================= ADD ITEM =================
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        item_name = request.form['item_name']
        description = request.form['description']
        contact = request.form['contact']
        user_email = session['user']

        image = request.files.get('image')
        filename = None

        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = sqlite3.connect('/tmp/users.db')
        cur = conn.cursor()

        cur.execute("SELECT item_name, description, user_email FROM items")
        existing_items = cur.fetchall()

        matched_users = []

        for db_name, db_desc, db_email in existing_items:
            if is_similar(item_name, db_name) or is_similar(description, db_desc):
                matched_users.append(db_email)

        cur.execute("""
            INSERT INTO items (item_name, description, contact, image, user_email)
            VALUES (?, ?, ?, ?, ?)
        """, (item_name, description, contact, filename, user_email))

        conn.commit()
        conn.close()

        try:
            msg = Message("Item Posted", recipients=[user_email])
            msg.body = f"Your item '{item_name}' has been posted."
            mail.send(msg)
        except Exception as e:
            print("Email Error:", e)

        for email in set(matched_users):
            if email != user_email:
                try:
                    alert = Message("Similar Item Found!", recipients=[email])
                    alert.body = f"A new item '{item_name}' matches your previous post."
                    mail.send(alert)
                except Exception as e:
                    print("Alert Error:", e)

        return redirect('/items')

    return render_template('add_item.html')


# ================= VIEW ITEMS =================
@app.route('/items')
def items():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('/tmp/users.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM items")
    data = cur.fetchall()

    conn.close()

    return render_template('items.html', items=data)


# ================= DELETE ALL ITEMS =================
@app.route('/delete_all')
def delete_all():
    conn = sqlite3.connect('/tmp/users.db')   
    cur = conn.cursor()

    cur.execute("DELETE FROM items")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='items'")

    conn.commit()
    conn.close()

    return redirect('/items')


# ================= IMAGE =================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ================= TEST EMAIL =================
@app.route('/test_email')
def test_email():
    try:
        msg = Message("Test Email", recipients=[session.get('user')])
        msg.body = "Test successful"
        mail.send(msg)
        return "Email Sent ✅"
    except Exception as e:
        return str(e)


# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)
