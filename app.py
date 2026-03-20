from flask import Flask, render_template, redirect, request, session, url_for, flash
import sqlite3
import os
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ✅ Secure config (use environment variables)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME']  = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")

app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

app.secret_key = os.environ.get("SECRET_KEY")

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ Database connection (Render safe)
def get_db_connection():
    DB_PATH = os.path.join(os.getcwd(), "database.db")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ✅ Initialize DB
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

# ✅ Create admin if not exists
def create_admin():
    conn = get_db_connection()
    cursor = conn.cursor()

    username = "admin"
    password = generate_password_hash("1234")

    try:
        cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", (username, password))
    except:
        pass

    conn.commit()
    conn.close()

init_db()
create_admin()

# ---------------- ROUTES ---------------- #

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
        msg = Message(
            subject="New Contact Form Submission",
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']]
        )
        msg.body = f"""<h2 style="color:#333;">New Contact Form Submission</h2>

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
        mail.send(msg)

        
        reply = Message(
            subject="✅ Thank You for Contacting LaxmiPrint",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]   # user email
        )

        reply.html = f"""
            <h2 style="color:#333;">Hello {name}, 👋</h2>

            <p>Thank you for contacting <b>LaxmiPrint</b>.</p>

            <p>We have received your inquiry and our team will get back to you within <b>24 hours</b>.</p>

            <hr>

            <h4>Your Message:</h4>
            <p style="background:#f4f4f4; padding:10px; border-radius:5px;">
            {message}
            </p>

            <br>

            <p>📞 If urgent, feel free to contact us directly.</p>

            <p style="color:gray;">
            Regards,<br>
            <b>LaxmiPrint Team</b>
            </p>
            """

        mail.send(reply)
        flash("✅ Your message has been sent successfully!")
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

    # Get image name
    product = conn.execute(
        "SELECT image FROM products WHERE id=?", (id,)
    ).fetchone()

    if product:
        image_filename = product["image"]

        # Delete image file
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

        # Delete from DB
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

        # Get old image
        old_product = conn.execute(
            "SELECT image FROM products WHERE id=?", (id,)
        ).fetchone()

        old_image = old_product["image"]

        if file and file.filename:
            # Delete old image
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image)
            if os.path.exists(old_path):
                os.remove(old_path)

            # Save new image
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            conn.execute("""
                UPDATE products
                SET name=?, description=?, image=?, specifications=?, price=?
                WHERE id=?
            """, (name, description, filename, specifications, price, id))

        else:
            # No new image
            conn.execute("""
                UPDATE products
                SET name=?, description=?, specifications=?, price=?
                WHERE id=?
            """, (name, description, specifications, price, id))

        conn.commit()
        conn.close()

        return redirect('/admin')

    # GET request
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
    app.run(debug=True)



# from flask import Flask,render_template,redirect,request,session,url_for
# import sqlite3
# import os
# from flask_mail import Mail,Message
# from flask import flash
# from werkzeug.security import generate_password_hash, check_password_hash

# from werkzeug.utils import secure_filename

# app = Flask(__name__)
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USERNAME'] = 'chandiwadeaaradhya@gmail.com'
# app.config['MAIL_PASSWORD'] = 'zayvmpzaxzslqazk'

# mail = Mail(app)

# app.secret_key = os.environ.get("SECRET_KEY")
# UPLOAD_FOLDER='static/uploads'
# app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER

# def init_db():
#     conn = sqlite3.connect('database.db')
#     cursor = conn.cursor()

#     cursor.execute('''
#     CREATE TABLE IF NOT EXISTS products (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         name TEXT,
#         description TEXT,
#         image TEXT
#     )
#     ''')

#     conn.commit()
#     conn.close()

# def update_db():

#     conn = sqlite3.connect("database.db")
#     cursor = conn.cursor()

#     cursor.execute("ALTER TABLE products ADD COLUMN specifications TEXT")
#     cursor.execute("ALTER TABLE products ADD COLUMN price TEXT")

#     conn.commit()
#     conn.close()

# # update_db()


# def contact_db():
#     conn = sqlite3.connect("database.db")
#     cursor = conn.cursor()

#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS contacts(
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT,
#     email TEXT,
#     message TEXT
#     )
#     """)

#     conn.commit()
#     conn.close()

# init_db()
# contact_db()
# def update_contact_db():
#     conn = sqlite3.connect("database.db")
#     cursor = conn.cursor()

#     cursor.execute("ALTER TABLE contacts ADD COLUMN phone TEXT")

#     conn.commit()
#     conn.close()

# # def update_contact_status():
# #     conn = sqlite3.connect("database.db")
# #     cursor = conn.cursor()

# #     cursor.execute("ALTER TABLE contacts ADD COLUMN is_read INTEGER DEFAULT 0")

# #     conn.commit()
# #     conn.close()
# def add_is_read_column():
#     conn = sqlite3.connect("database.db")
#     cursor = conn.cursor()

#     cursor.execute("ALTER TABLE contacts ADD COLUMN is_read INTEGER DEFAULT 0")

#     conn.commit()
#     conn.close()



# def reset_read_status():
#     conn = sqlite3.connect("database.db")
#     cursor = conn.cursor()

#     cursor.execute("UPDATE contacts SET is_read = 0")

#     conn.commit()
#     conn.close()
# init_db()
# contact_db()

# def create_admin_table():
#     conn = sqlite3.connect("database.db")
#     cursor = conn.cursor()

#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS admin(
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         username TEXT UNIQUE,
#         password TEXT
#     )
#     """)

#     conn.commit()
#     conn.close()
# def create_admin():
#     conn = sqlite3.connect("database.db")
#     cursor = conn.cursor()

#     username = "admin"
#     password = generate_password_hash("1234")  # encrypted

#     try:
#         cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", (username, password))
#     except:
#         pass  # already exists

#     conn.commit()
#     conn.close()
# # create_admin()
# # create_admin_table()
# # add_is_read_column()
# # reset_read_status()
# # update_contact_db()
# # products = [
# #     {
# #         "id": 1,
# #         "name": "Business Cards",
# #         "description": "Premium quality visiting cards",
# #         "image": "sample.jpg"
# #     },
# #     {
# #         "id": 2,
# #         "name": "Flyers",
# #         "description": "Attractive promotional flyers",
# #         "image": "sample.jpg"
# #     },
# #     {
# #         "id": 3,
# #         "name": "Brochures",
# #         "description": "Professional brochure printing",
# #         "image": "sample.jpg"
# #     }
# # ]



# @app.route("/")
# def home():
#     conn = sqlite3.connect("database.db")
#     cursor = conn.cursor()

#     cursor.execute("SELECT * FROM products")
#     products = cursor.fetchall()

#     conn.close()

#     return render_template("home.html", products=products)

# @app.route("/products")
# def product_page():
#     conn = sqlite3.connect('database.db')
#     cursor = conn.cursor()

#     cursor.execute("SELECT * FROM products")
#     products = cursor.fetchall()

#     conn.close()    
#     return render_template("products.html",products=products)

# @app.route("/about")
# def about():
#     return render_template("about.html")

# @app.route("/contact",methods=["GET","POST"])
# def contact():
#     if request.method=="POST":
#         name=request.form["name"]
#         email=request.form["email"]
#         phone=request.form["phone"]
#         message=request.form["message"]

#         if not phone.isdigit() or len(phone) != 10:
#                return "Phone number must be 10 digits"

#         conn = sqlite3.connect("database.db")
#         cursor = conn.cursor()

#         cursor.execute(
#         "INSERT INTO contacts (name,email,message,phone) VALUES (?,?,?,?)",
#         (name,email,message,phone)
#         )

#         conn.commit()
#         conn.close()
#         msg = Message(
#             subject="New Contact Form Submission",
#             sender=app.config['MAIL_USERNAME'],
#             recipients=["chandiwadeaaradhya@gmail.com"]
#         )

#         msg.html = f"""
#         <h2 style="color:#333;">New Contact Form Submission</h2>

#         <table style="border-collapse: collapse; width: 100%; font-family: Arial;">
#         <tr>
#             <td style="padding:8px; border:1px solid #ddd;"><b>Name</b></td>
#             <td style="padding:8px; border:1px solid #ddd;">{name}</td>
#         </tr>

#         <tr>
#             <td style="padding:8px; border:1px solid #ddd;"><b>Email</b></td>
#             <td style="padding:8px; border:1px solid #ddd;">{email}</td>
#         </tr>

#         <tr>
#             <td style="padding:8px; border:1px solid #ddd;"><b>Phone</b></td>
#             <td style="padding:8px; border:1px solid #ddd;">{phone}</td>
#         </tr>

#         <tr>
#             <td style="padding:8px; border:1px solid #ddd;"><b>Message</b></td>
#             <td style="padding:8px; border:1px solid #ddd;">{message}</td>
#         </tr>
#         </table>

#         <br>

#         <p style="color:gray;">
#         This message was sent from your website contact form.
#         </p>
#         """

#         mail.send(msg)

#         reply = Message(
#             subject="✅ Thank You for Contacting LaxmiPrint",
#             sender=app.config['MAIL_USERNAME'],
#             recipients=[email]   # user email
#         )

#         reply.html = f"""
#             <h2 style="color:#333;">Hello {name}, 👋</h2>

#             <p>Thank you for contacting <b>LaxmiPrint</b>.</p>

#             <p>We have received your inquiry and our team will get back to you within <b>24 hours</b>.</p>

#             <hr>

#             <h4>Your Message:</h4>
#             <p style="background:#f4f4f4; padding:10px; border-radius:5px;">
#             {message}
#             </p>

#             <br>

#             <p>📞 If urgent, feel free to contact us directly.</p>

#             <p style="color:gray;">
#             Regards,<br>
#             <b>LaxmiPrint Team</b>
#             </p>
#             """

#         mail.send(reply)
#         flash("✅ Your message has been sent successfully!")
#         return redirect("/contact")  # better UX after submit

#     return render_template("contact.html")

# @app.route("/product_details/<int:id>")
# def product_details(id):
#     conn = sqlite3.connect('database.db')
#     cursor = conn.cursor()

#     cursor.execute("SELECT * FROM products WHERE id=?", (id,))
#     product = cursor.fetchone()

#     conn.close()

#     return render_template("product_details.html",product=product)

# @app.route("/admin",methods=["GET","POST"])
# def admin():
#     if 'admin' not in session:
#         return redirect('/login')
#     conn = sqlite3.connect('database.db')
#     cursor = conn.cursor()
#     if request.method=="POST":
#         name=request.form["name"]
#         description=request.form["description"]
#         file=request.files["image"]
#         specifications = request.form['specifications']
#         price = request.form['price']

#         filename = secure_filename(file.filename)
#         file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        

#         cursor.execute("INSERT INTO products (name, description, image,specifications,price) VALUES (?, ?, ?, ?, ?)",
#                        (name, description, filename,specifications,price))

#         conn.commit()
#     cursor.execute("SELECT * FROM products")
#     products = cursor.fetchall()
#     conn.close()
#             # return redirect("/products")
#     return render_template("admin.html",products=products)

# @app.route('/delete/<int:id>')
# def delete_product(id):
#     if 'admin' not in session:
#         return redirect('/login')

#     conn = sqlite3.connect('database.db')
#     cursor = conn.cursor()

#     # Get image name first
#     cursor.execute("SELECT image FROM products WHERE id=?", (id,))
#     product = cursor.fetchone()

#     if product:
#         image_filename = product[0]

#         # Delete image file
#         image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
#         if os.path.exists(image_path):
#             os.remove(image_path)

#         # Delete from database
#         cursor.execute("DELETE FROM products WHERE id=?", (id,))
#         conn.commit()

#     conn.close()

#     return redirect('/products')

# @app.route('/edit/<int:id>', methods=['GET', 'POST'])
# def edit_product(id):
#     if 'admin' not in session:
#         return redirect('/login')

#     conn = sqlite3.connect('database.db')
#     cursor = conn.cursor()

#     if request.method == 'POST':

#         name = request.form['name']
#         description = request.form['description']
#         file = request.files['image']
#         specifications = request.form['specifications']
#         price = request.form['price']

#         # Get old image first
#         cursor.execute("SELECT image FROM products WHERE id=?", (id,))
#         old_product = cursor.fetchone()
#         old_image = old_product[0]

#         if file and file.filename != "":
#             # Delete old image
#             old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image)
#             if os.path.exists(old_path):
#                 os.remove(old_path)

#             # Save new image
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

#             cursor.execute("""
#                 UPDATE products
#                 SET name=?, description=?, image=?,specifications=?,price=?
#                 WHERE id=?
#             """, (name, description, filename,specifications, price, id))

#         else:
#             # If no new image uploaded
#             cursor.execute("""
#                 UPDATE products
#                 SET name=?, description=?,specifications=?,price=?
#                 WHERE id=?
#             """, (name, description,specifications, price, id))

#         conn.commit()
#         conn.close()

#         return redirect('/admin')

#     # GET request
#     cursor.execute("SELECT * FROM products WHERE id=?", (id,))
#     product = cursor.fetchone()
#     conn.close()

#     return render_template('edit.html', product=product)

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == "POST":
#         username = request.form["username"]
#         password = request.form["password"]

#         conn = sqlite3.connect("database.db")
#         cursor = conn.cursor()

#         cursor.execute("SELECT * FROM admin WHERE username=?", (username,))
#         admin = cursor.fetchone()

#         conn.close()

#         if admin and check_password_hash(admin[2], password):
#             session["admin"] = True
#             return redirect("/admin")
#         else:
#             flash("Invalid credentials", "danger")

#     return render_template("login.html")
# @app.route('/logout')
# def logout():
#     session.pop('admin', None)
#     return redirect('/')

# @app.route("/admin/messages")
# def admin_messages():

#     conn = sqlite3.connect("database.db")
#     cursor = conn.cursor()

#     cursor.execute("SELECT * FROM contacts")
#     messages = cursor.fetchall()

#     conn.close()

#     return render_template("admin_messages.html", messages=messages)

# @app.route("/delete_message/<int:id>")
# def delete_message(id):

#     conn = sqlite3.connect("database.db")
#     cursor = conn.cursor()

#     cursor.execute("DELETE FROM contacts WHERE id=?", (id,))

#     conn.commit()
#     conn.close()

#     return redirect("/admin/messages")
# @app.route("/mark-read/<int:id>")
# def mark_read(id):
#     if 'admin' not in session:
#         return redirect("/login")

#     conn = sqlite3.connect("database.db")
#     cursor = conn.cursor()

#     cursor.execute("UPDATE contacts SET is_read=1 WHERE id=?", (id,))

#     conn.commit()
#     conn.close()

#     return redirect("/admin/messages")

# if __name__=="__main__":
#     app.run(debug=True)