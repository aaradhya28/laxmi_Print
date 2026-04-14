from flask import Flask, abort, render_template, redirect, request, session, url_for, flash
import sqlite3
import os
import secrets
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "local.env"))

app = Flask(__name__)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "database.db")
)
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME']  = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")

app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

app.config["SECRET_KEY"] = (
    os.getenv("SECRET_KEY")
    or os.getenv("FLASK_SECRET_KEY")
    or secrets.token_hex(32)
)

if not os.getenv("SECRET_KEY") and not os.getenv("FLASK_SECRET_KEY"):
    print("WARNING: SECRET_KEY is not set. Using a temporary generated key.")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(os.getenv("RENDER"))
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": generate_csrf_token}


@app.before_request
def protect_post_routes():
    if request.method != "POST":
        return

    session_token = session.get("_csrf_token")
    form_token = request.form.get("csrf_token")

    if not session_token or not form_token:
        abort(400)

    if not secrets.compare_digest(session_token, form_token):
        abort(400)


def allowed_file(filename):
    _, extension = os.path.splitext(filename)
    return extension.lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(file_storage):
    if not file_storage or not file_storage.filename:
        raise ValueError("Please select an image to upload.")

    if not allowed_file(file_storage.filename):
        raise ValueError("Only PNG, JPG, JPEG, GIF, and WEBP files are allowed.")

    if file_storage.mimetype and not file_storage.mimetype.startswith("image/"):
        raise ValueError("Uploaded file must be an image.")

    safe_name = secure_filename(file_storage.filename)
    _, extension = os.path.splitext(safe_name)
    unique_name = f"{secrets.token_hex(12)}{extension.lower()}"
    file_storage.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
    return unique_name


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        image TEXT,
        specifications TEXT,
        price TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contacts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        message TEXT,
        phone TEXT,
        is_read INTEGER DEFAULT 0
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    ''')

    conn.commit()
    conn.close()


def seed_admin_from_env():
    if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
        print("WARNING: ADMIN_USERNAME or ADMIN_PASSWORD_HASH is not set. Admin bootstrap skipped.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    username = ADMIN_USERNAME
    password_hash = ADMIN_PASSWORD_HASH

    
    existing = cursor.execute(
        "SELECT id FROM admin WHERE username=?",
        (username,)
    ).fetchone()
    if existing:
        cursor.execute(
            "UPDATE admin SET password=? WHERE username=?",
            (password_hash, username),
        )
    else:
        cursor.execute(
            "INSERT INTO admin (username, password) VALUES (?, ?)",
            (username, password_hash),
        )

    conn.commit()
    conn.close()

init_db()
seed_admin_from_env()



@app.route("/")
def home():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("home.html", products=products)

@app.route("/products")
def product_page():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("products.html", products=products)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        try:
            name = request.form.get("name")
            email = request.form.get("email")
            phone = request.form.get("phone")
            message = request.form.get("message")

           
            if not phone or not phone.isdigit() or len(phone) != 10:
                flash("Phone number must be 10 digits")
                return redirect("/contact")

            
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO contacts (name,email,message,phone) VALUES (?,?,?,?)",
                (name, email, message, phone)
            )
            conn.commit()
            conn.close()

            
            try:
                logo_url = url_for(
                    'static',
                    filename='uploads/logofinal-removebg-preview.png',
                    _external=True
                )
            except:
                logo_url = ""

            
            if app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'):

                try:
                    msg = Message(
                        subject="New Contact Form Submission",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[app.config['MAIL_USERNAME']]
                    )

                    msg.html = f"""
                    <h2>New Contact Form</h2>
                    <p><b>Name:</b> {name}</p>
                    <p><b>Email:</b> {email}</p>
                    <p><b>Phone:</b> {phone}</p>
                    <p><b>Message:</b> {message}</p>
                    """

                    mail.send(msg)

                except Exception as e:
                    print("Admin mail error:", e)

                try:
                    reply = Message(
                        subject="Thank You",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[email]
                    )

                    reply.html = f"""
                    <h3>Hello {name}</h3>
                    <p>Thanks for contacting us.</p>
                    """

                    mail.send(reply)

                except Exception as e:
                    print("User mail error:", e)

            else:
                print("Mail config missing")

            flash("Message sent successfully!", "success")

        except Exception as e:
            print("CONTACT ERROR:", e)
            flash("Something went wrong. Try again.", "danger")

        return redirect("/contact")

    return render_template("contact.html")

@app.route("/product_details/<int:id>")
def product_details(id):
    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE id=?", (id,)
    ).fetchone()
    conn.close()

    return render_template("product_details.html", product=product)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if 'admin' not in session:
        return redirect('/login')

    conn = get_db_connection()

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        specifications = request.form["specifications"]
        price = request.form["price"]
        file = request.files["image"]
        try:
            filename = save_uploaded_image(file)
        except ValueError as e:
            flash(str(e), "danger")
            conn.close()
            return redirect("/admin")

        conn.execute(
            "INSERT INTO products (name, description, image, specifications, price) VALUES (?, ?, ?, ?, ?)",
            (name, description, filename, specifications, price)
        )
        conn.commit()

    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()

    return render_template("admin.html", products=products)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_product(id):
    if 'admin' not in session:
        return redirect('/login')

    conn = get_db_connection()

    
    product = conn.execute(
        "SELECT image FROM products WHERE id=?", (id,)
    ).fetchone()

    if product:
        image_filename = product["image"]

       
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

        
        conn.execute("DELETE FROM products WHERE id=?", (id,))
        conn.commit()

    conn.close()
    return redirect('/admin')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if 'admin' not in session:
        return redirect('/login')

    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        specifications = request.form['specifications']
        price = request.form['price']
        file = request.files['image']

        
        old_product = conn.execute(
            "SELECT image FROM products WHERE id=?", (id,)
        ).fetchone()

        old_image = old_product["image"]

        if file and file.filename:
            try:
                filename = save_uploaded_image(file)
            except ValueError as e:
                flash(str(e), "danger")
                conn.close()
                return redirect(f"/edit/{id}")

            old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image)
            if os.path.exists(old_path):
                os.remove(old_path)

            conn.execute("""
                UPDATE products
                SET name=?, description=?, image=?, specifications=?, price=?
                WHERE id=?
            """, (name, description, filename, specifications, price, id))

        else:
            
            conn.execute("""
                UPDATE products
                SET name=?, description=?, specifications=?, price=?
                WHERE id=?
            """, (name, description, specifications, price, id))

        conn.commit()
        conn.close()

        return redirect('/admin')

    
    product = conn.execute(
        "SELECT * FROM products WHERE id=?", (id,)
    ).fetchone()

    conn.close()
    return render_template('edit.html', product=product)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM admin WHERE username=?", (username,)).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session["admin"] = True
            return redirect("/admin")
        else:
            flash("Invalid credentials", "danger")

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

@app.route("/admin/messages")
def admin_messages():
    if 'admin' not in session:
        return redirect("/login")

    conn = get_db_connection()
    messages = conn.execute("SELECT * FROM contacts").fetchall()
    conn.close()

    return render_template("admin_messages.html", messages=messages)

@app.route("/delete_message/<int:id>", methods=['POST'])
def delete_message(id):
    if 'admin' not in session:
        return redirect("/login")

    conn = get_db_connection()

    conn.execute("DELETE FROM contacts WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/messages")

@app.route("/mark-read/<int:id>", methods=['POST'])
def mark_read(id):
    if 'admin' not in session:
        return redirect("/login")

    conn = get_db_connection()

    conn.execute("UPDATE contacts SET is_read=1 WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/messages")


if __name__ == "__main__":
     port = int(os.environ.get("PORT", 10000))
     app.run(host="0.0.0.0", port=port)


