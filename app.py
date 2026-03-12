from flask import Flask,render_template,redirect,request,session,url_for
import sqlite3
import os

from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key="supersecretkey"
UPLOAD_FOLDER='static/uploads'
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        image TEXT
    )
    ''')

    conn.commit()
    conn.close()

def update_db():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE products ADD COLUMN specifications TEXT")
    cursor.execute("ALTER TABLE products ADD COLUMN price TEXT")

    conn.commit()
    conn.close()

# update_db()


def contact_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contacts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    message TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()
contact_db()
def update_contact_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE contacts ADD COLUMN phone TEXT")

    conn.commit()
    conn.close()
# update_contact_db()
# products = [
#     {
#         "id": 1,
#         "name": "Business Cards",
#         "description": "Premium quality visiting cards",
#         "image": "sample.jpg"
#     },
#     {
#         "id": 2,
#         "name": "Flyers",
#         "description": "Attractive promotional flyers",
#         "image": "sample.jpg"
#     },
#     {
#         "id": 3,
#         "name": "Brochures",
#         "description": "Professional brochure printing",
#         "image": "sample.jpg"
#     }
# ]



@app.route("/")
def home():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    conn.close()

    return render_template("home.html", products=products)

@app.route("/products")
def product_page():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    conn.close()    
    return render_template("products.html",products=products)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact",methods=["GET","POST"])
def contact():
    if request.method=="POST":
        name=request.form["name"]
        email=request.form["email"]
        phone=request.form["phone"]
        message=request.form["message"]

        if not phone.isdigit() or len(phone) != 10:
               return "Phone number must be 10 digits"

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
        "INSERT INTO contacts (name,email,message,phone) VALUES (?,?,?,?)",
        (name,email,message,phone)
        )

        conn.commit()
        conn.close()

    return render_template("contact.html")

@app.route("/product_details/<int:id>")
def product_details(id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE id=?", (id,))
    product = cursor.fetchone()

    conn.close()

    return render_template("product_details.html",product=product)

@app.route("/admin",methods=["GET","POST"])
def admin():
    if 'admin' not in session:
        return redirect('/login')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    if request.method=="POST":
        name=request.form["name"]
        description=request.form["description"]
        file=request.files["image"]
        specifications = request.form['specifications']
        price = request.form['price']

        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        

        cursor.execute("INSERT INTO products (name, description, image,specifications,price) VALUES (?, ?, ?, ?, ?)",
                       (name, description, filename,specifications,price))

        conn.commit()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
            # return redirect("/products")
    return render_template("admin.html",products=products)

@app.route('/delete/<int:id>')
def delete_product(id):
    if 'admin' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Get image name first
    cursor.execute("SELECT image FROM products WHERE id=?", (id,))
    product = cursor.fetchone()

    if product:
        image_filename = product[0]

        # Delete image file
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

        # Delete from database
        cursor.execute("DELETE FROM products WHERE id=?", (id,))
        conn.commit()

    conn.close()

    return redirect('/products')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if 'admin' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        name = request.form['name']
        description = request.form['description']
        file = request.files['image']
        specifications = request.form['specifications']
        price = request.form['price']

        # Get old image first
        cursor.execute("SELECT image FROM products WHERE id=?", (id,))
        old_product = cursor.fetchone()
        old_image = old_product[0]

        if file and file.filename != "":
            # Delete old image
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image)
            if os.path.exists(old_path):
                os.remove(old_path)

            # Save new image
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            cursor.execute("""
                UPDATE products
                SET name=?, description=?, image=?,specifications=?,price=?
                WHERE id=?
            """, (name, description, filename,specifications, price, id))

        else:
            # If no new image uploaded
            cursor.execute("""
                UPDATE products
                SET name=?, description=?,specifications=?,price=?
                WHERE id=?
            """, (name, description,specifications, price, id))

        conn.commit()
        conn.close()

        return redirect('/admin')

    # GET request
    cursor.execute("SELECT * FROM products WHERE id=?", (id,))
    product = cursor.fetchone()
    conn.close()

    return render_template('edit.html', product=product)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method=="POST":
        username=request.form["username"]
        password=request.form["password"]

        if username=="admin" and password=="1234":
            session["admin"]=True
            return redirect("/admin")
        else:
            return "Invalid Credentials"
    return render_template("login.html")
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

@app.route("/admin/messages")
def admin_messages():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM contacts")
    messages = cursor.fetchall()

    conn.close()

    return render_template("admin_messages.html", messages=messages)

@app.route("/delete_message/<int:id>")
def delete_message(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM contacts WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/admin/messages")

if __name__=="__main__":
    app.run(debug=True)