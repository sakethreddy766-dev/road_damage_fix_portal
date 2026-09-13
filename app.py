import os
import sqlite3
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# --------------------------------------------------
# FLASK APP
# --------------------------------------------------

app = Flask(__name__)

app.secret_key = "roadfix_secret_key_change_this"


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATABASE = os.path.join(BASE_DIR, "database.db")

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "uploads"
)

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Maximum image size = 5 MB
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# Create upload folder if it does not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db():

    db = sqlite3.connect(DATABASE)

    # Allows us to access columns by name
    db.row_factory = sqlite3.Row

    return db


# --------------------------------------------------
# CREATE DATABASE TABLES
# --------------------------------------------------

def create_tables():

    db = get_db()

    # Users table
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            is_admin INTEGER DEFAULT 0

        )
    """)


    # Reports table
    db.execute("""
        CREATE TABLE IF NOT EXISTS reports (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            location TEXT NOT NULL,

            damage_type TEXT NOT NULL,

            description TEXT NOT NULL,

            image TEXT,

            status TEXT DEFAULT 'Pending',

            admin_remark TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
            REFERENCES users(id)

        )
    """)


    # --------------------------------------------------
    # CREATE DEFAULT ADMIN
    # --------------------------------------------------

    admin = db.execute(
        "SELECT * FROM users WHERE email = ?",
        ("admin@gmail.com",)
    ).fetchone()


    if admin is None:

        admin_password = generate_password_hash(
            "admin123"
        )

        db.execute("""
            INSERT INTO users
            (name, email, password, is_admin)
            VALUES (?, ?, ?, ?)
        """, (
            "Administrator",
            "admin@gmail.com",
            admin_password,
            1
        ))


    db.commit()

    db.close()


# --------------------------------------------------
# ALLOWED FILE CHECK
# --------------------------------------------------

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# --------------------------------------------------
# LOGIN REQUIRED
# --------------------------------------------------

def login_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash("Please login first.")

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return decorated_function


# --------------------------------------------------
# ADMIN REQUIRED
# --------------------------------------------------

def admin_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash("Please login first.")

            return redirect(
                url_for("login")
            )


        if session.get("is_admin") != 1:

            flash("Admin access required.")

            return redirect(
                url_for("dashboard")
            )

        return function(*args, **kwargs)

    return decorated_function


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        # Basic validation
        if not name or not email or not password:

            flash(
                "Please fill all fields."
            )

            return redirect(
                url_for("register")
            )


        db = get_db()


        # Check if email already exists
        existing_user = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()


        if existing_user:

            db.close()

            flash(
                "Email is already registered."
            )

            return redirect(
                url_for("register")
            )


        # Hash password
        hashed_password = generate_password_hash(
            password
        )


        # Insert user
        db.execute("""
            INSERT INTO users
            (name, email, password, is_admin)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            email,
            hashed_password,
            0
        ))


        db.commit()

        db.close()


        flash(
            "Registration successful. Please login."
        )

        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html"
    )


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        db = get_db()


        user = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()


        db.close()


        if user and check_password_hash(
            user["password"],
            password
        ):

            # Store user information in session
            session["user_id"] = user["id"]

            session["name"] = user["name"]

            session["email"] = user["email"]

            session["is_admin"] = user["is_admin"]


            flash(
                "Login successful."
            )


            # Admin goes to admin dashboard
            if user["is_admin"] == 1:

                return redirect(
                    url_for("admin")
                )


            # Normal user goes to dashboard
            return redirect(
                url_for("dashboard")
            )


        flash(
            "Invalid email or password."
        )


    return render_template(
        "login.html"
    )


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out."
    )

    return redirect(
        url_for("index")
    )


# --------------------------------------------------
# USER DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():

    db = get_db()


    reports = db.execute("""
        SELECT *
        FROM reports
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (
        session["user_id"],
    )).fetchall()


    db.close()


    return render_template(
        "dashboard.html",
        reports=reports
    )


# --------------------------------------------------
# REPORT ROAD DAMAGE
# --------------------------------------------------

@app.route("/report", methods=["GET", "POST"])
@login_required
def report_damage():

    if request.method == "POST":

        location = request.form.get(
            "location",
            ""
        ).strip()

        damage_type = request.form.get(
            "damage_type",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()


        # Validate required fields
        if not location or not damage_type or not description:

            flash(
                "Please fill all required fields."
            )

            return redirect(
                url_for("report_damage")
            )


        image = request.files.get(
            "image"
        )


        filename = None


        # --------------------------------------------------
        # IMAGE UPLOAD
        # --------------------------------------------------

        if image and image.filename:

            if not allowed_file(
                image.filename
            ):

                flash(
                    "Invalid image format. Use PNG, JPG, JPEG or GIF."
                )

                return redirect(
                    url_for("report_damage")
                )


            # Secure filename
            original_filename = secure_filename(
                image.filename
            )


            # Create unique filename
            import uuid

            filename = (
                str(uuid.uuid4())
                + "_"
                + original_filename
            )


            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )


        # --------------------------------------------------
        # SAVE REPORT
        # --------------------------------------------------

        db = get_db()


        db.execute("""
            INSERT INTO reports
            (
                user_id,
                location,
                damage_type,
                description,
                image,
                status,
                admin_remark
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            location,
            damage_type,
            description,
            filename,
            "Pending",
            None
        ))


        db.commit()

        db.close()


        flash(
            "Road damage report submitted successfully."
        )


        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "report_damage.html"
    )


# --------------------------------------------------
# REPORT DETAILS
# --------------------------------------------------

@app.route("/report/<int:report_id>")
@login_required
def report_details(report_id):

    db = get_db()


    report = db.execute("""
        SELECT
            reports.*,
            users.name,
            users.email

        FROM reports

        JOIN users
        ON reports.user_id = users.id

        WHERE reports.id = ?
        AND reports.user_id = ?
    """, (
        report_id,
        session["user_id"]
    )).fetchone()


    db.close()


    if report is None:

        flash(
            "Report not found."
        )

        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "report_details.html",
        report=report
    )


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/admin")
@admin_required
def admin():

    db = get_db()


    reports = db.execute("""
        SELECT
            reports.*,
            users.name,
            users.email

        FROM reports

        JOIN users
        ON reports.user_id = users.id

        ORDER BY reports.created_at DESC
    """).fetchall()


    db.close()


    return render_template(
        "admin.html",
        reports=reports
    )


# --------------------------------------------------
# UPDATE REPORT
# --------------------------------------------------

@app.route(
    "/admin/update/<int:report_id>",
    methods=["POST"]
)
@admin_required
def update_report(report_id):

    # --------------------------------------------------
    # IMPORTANT FIX
    # --------------------------------------------------
    # .get() prevents KeyError if the field is missing.

    status = request.form.get(
        "status",
        "Pending"
    )


    remark = request.form.get(
        "remark",
        ""
    ).strip()


    # Only allow valid statuses
    allowed_statuses = {
        "Pending",
        "In Progress",
        "Repaired"
    }


    if status not in allowed_statuses:

        status = "Pending"


    db = get_db()


    # Check whether report exists
    report = db.execute(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    ).fetchone()


    if report is None:

        db.close()

        flash(
            "Report not found."
        )

        return redirect(
            url_for("admin")
        )


    # Update report
    db.execute("""
        UPDATE reports

        SET
            status = ?,
            admin_remark = ?

        WHERE id = ?
    """, (
        status,
        remark,
        report_id
    ))


    db.commit()

    db.close()


    flash(
        "Report updated successfully."
    )


    return redirect(
        url_for("admin")
    )


# --------------------------------------------------
# DELETE REPORT
# --------------------------------------------------

@app.route(
    "/admin/delete/<int:report_id>"
)
@admin_required
def delete_report(report_id):

    db = get_db()


    # Get report first so we can delete its image
    report = db.execute(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    ).fetchone()


    if report is None:

        db.close()

        flash(
            "Report not found."
        )

        return redirect(
            url_for("admin")
        )


    # Delete image from uploads folder
    if report["image"]:

        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            report["image"]
        )


        if os.path.exists(image_path):

            os.remove(
                image_path
            )


    # Delete report
    db.execute(
        "DELETE FROM reports WHERE id = ?",
        (report_id,)
    )


    db.commit()

    db.close()


    flash(
        "Report deleted successfully."
    )


    return redirect(
        url_for("admin")
    )


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------
create_tables()
if __name__ == "__main__":

    

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )