from flask import Flask, render_template, redirect, request, session, url_for, flash
import sqlite3
import os
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "local.env"))

app = Flask(__name__)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "scrypt:32768:8:1$umEQs7nwfTWE45dj$d8e3e804e8df7b61a577121b3128af70cd254f75861bf2e8cec1cf44c20480311788b59e85309d2dc923a020c77325b7937eab057202653078954a532482319b"


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME']  = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")

app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def get_db_connection():
    DB_PATH = os.path.join(os.getcwd(), "database.db")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


def create_admin():
    conn = get_db_connection()
    cursor = conn.cursor()

    
    if ADMIN_PASSWORD_HASH == "<PASTE_PASSWORD_HASH_HERE>":
        raise RuntimeError(
            "ADMIN_PASSWORD_HASH is not set. Generate a password hash and paste it into app.py."
        )

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
create_admin()



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
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        message = request.form["message"]

        if not phone.isdigit() or len(phone) != 10:
            flash("Phone number must be 10 digits")
            return redirect("/contact")

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO contacts (name,email,message,phone) VALUES (?,?,?,?)",
            (name, email, message, phone)
        )
        conn.commit()
        conn.close()

        # Send email
        logo_url = url_for(
            'static',
            filename='uploads/logofinal-removebg-preview.png',
            _external=True
        )

        msg = Message(
            subject="New Contact Form Submission",
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']]
        )
        msg.html = f"""
        <div style="margin-bottom:18px;">
          <img src="{{ url_for('static', filename='uploads/logofinal-removebg-preview.png') }}" alt="LaxmiPrint" style="height:60px; width:auto; display:block;">
        </div>
        <h2 style="color:#333; margin-top:0;">New Contact Form Submission</h2>

        <table style="border-collapse: collapse; width: 100%; font-family: Arial;">
        <tr>
            <td style="padding:8px; border:1px solid #ddd;"><b>Name</b></td>
            <td style="padding:8px; border:1px solid #ddd;">{name}</td>
        </tr>

        <tr>
            <td style="padding:8px; border:1px solid #ddd;"><b>Email</b></td>
            <td style="padding:8px; border:1px solid #ddd;">{email}</td>
        </tr>

        <tr>
            <td style="padding:8px; border:1px solid #ddd;"><b>Phone</b></td>
            <td style="padding:8px; border:1px solid #ddd;">{phone}</td>
        </tr>

        <tr>
            <td style="padding:8px; border:1px solid #ddd;"><b>Message</b></td>
            <td style="padding:8px; border:1px solid #ddd;">{message}</td>
        </tr>
        </table>

        <br>

        <p style="color:gray;">
        This message was sent from your website contact form.
        </p>
        """
        
        reply = Message(
            subject="✅ Thank You for Contacting LaxmiDigitalPrint",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]   # user email
        )

        reply.html = f"""
            <div style="margin-bottom:18px;">
              <img src="{logo_url}" alt="LaxmiPrint" style="height:60px; width:auto; display:block;">
            </div>
            <h2 style="color:#333; margin-top:0;">Hello {name}, 👋</h2>

            <p>Thank you for contacting <b>LaxmiPrint</b>.</p>

            <p>We have received your inquiry and our team will get back to you within <b>24 hours</b>.</p>

            <hr>

            <h4>Your Message:</h4>
            <p style="background:#f4f4f4; padding:10px; border-radius:5px;">
            {message}
            </p>

            <br>

            <p>If urgent, feel free to contact us directly.</p>

            <p>
            <i class="bi bi-telephone-fill me-2 text-success"></i>
            +91 9702115408 / 7710977432 / 8169265622
            </p>

            <p>
            <i class="bi bi-envelope-fill me-2 text-primary"></i>
            printwork.laxmi@gmail.com
            </p>

            <p>
            <i class="bi bi-geo-alt-fill me-2 text-danger"></i>
            Shubh Ranjani Co Housing Society, Flat No C9, Sector 3, Airoli, Navi Mumbai 400708
            </p>

            <p style="color:gray;">
            Regards,<br>
            <b>LaxmiPrint Team</b>
            </p>
            """

        try:
            mail.send(msg)      # admin mail
            mail.send(reply)    # user mail
            flash("✅ Your message has been sent successfully!", "success")
        except Exception as e:
            print("Mail error:", e)  
            flash("Message saved, but email could not be sent right now.", "warning")
    
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

        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn.execute(
            "INSERT INTO products (name, description, image, specifications, price) VALUES (?, ?, ?, ?, ?)",
            (name, description, filename, specifications, price)
        )
        conn.commit()

    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()

    return render_template("admin.html", products=products)

@app.route('/delete/<int:id>')
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
           
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image)
            if os.path.exists(old_path):
                os.remove(old_path)

            
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

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

@app.route("/delete_message/<int:id>")
def delete_message(id):
    if 'admin' not in session:
        return redirect("/login")

    conn = get_db_connection()

    conn.execute("DELETE FROM contacts WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/messages")

@app.route("/mark-read/<int:id>")
def mark_read(id):
    if 'admin' not in session:
        return redirect("/login")

    conn = get_db_connection()

    conn.execute("UPDATE contacts SET is_read=1 WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/messages")


if __name__ == "__main__":
    app.run()



