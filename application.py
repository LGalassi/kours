import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///kours.db")


@app.route("/")
@login_required
def index():

    schools = db.execute("SELECT schools.id AS school_id, schools.name, schools.icon, courses.id, courses.status, SUM(CASE WHEN courses.status = 'todo' THEN 1 ELSE 0 END) AS todo_total, SUM(CASE WHEN courses.status = 'doing' THEN 1 ELSE 0 END) AS doing_total, SUM(CASE WHEN courses.status = 'done' THEN 1 ELSE 0 END) AS done_total FROM schools LEFT JOIN courses ON schools.id = courses.school_id WHERE user_id = :id GROUP BY 2 ORDER BY 2",
                         id=session["user_id"])

    for row in schools:
        total = row["todo_total"] + row["doing_total"] + row["done_total"]

        if total == 0:
            row["todo_percent"] = 0
            row["doing_percent"] = 0
            row["done_percent"] = 0
        else:
            row["todo_percent"] = row["todo_total"] / total * 100
            row["doing_percent"] = row["doing_total"] / total * 100
            row["done_percent"] = row["done_total"] / total * 100

    name = db.execute("SELECT first_name, last_name FROM users WHERE id = :id", id=session["user_id"])

    return render_template("index.html", schools=schools, name=name)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("you must provide a username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("you must provide a password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("your username and/or password are wrong", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/main")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("you must provide a username")

        if not request.form.get("password") or not request.form.get("confirm"):
            return apology("you must provide a password")

        if not request.form.get("first") or not request.form.get("last"):
            return apology("you must provide your name")

        if not request.form.get("password"):
            return apology("you must provide your country")

        if not request.form.get("username"):
            return apology("you must provide your state")

        if not request.form.get("password"):
            return apology("you must provide your city")

        if not request.form.get("reminder"):
            return apology("you must provide a password reminder")


        # Check if the username already exist
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        if len(rows) != 0:
            return apology("that username is already taken")

        # Check if the passwords match
        if request.form.get("password") != request.form.get("confirm"):
            return apology("the passwords don't match")

        # Register the user in the database
        db.execute(
            "INSERT INTO users (username, hash, first_name, last_name, country, state, city, password_reminder) VALUES (:username, :hash, :first, :last, :country, :state, :city, :reminder)",
            username=request.form.get("username"), hash=generate_password_hash(request.form.get("password")), first=request.form.get("first"),
            last=request.form.get("last"), country=request.form.get("country"), state=request.form.get("state"), city=request.form.get("city"),
            reminder=request.form.get("reminder"))

        # Redirect to the main page
        return redirect("/main")
    else:
        return render_template("register.html")


@app.route("/forgot", methods=["GET", "POST"])
def forgot():

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("you must provide a username")

        if request.method == "POST":
            rows = db.execute("SELECT password_reminder FROM users WHERE username = :username", username=request.form.get("username"))

        if len(rows) != 1:
                return apology("that username doesn't exist")

        return render_template("reminder.html", reminder=rows[0]["password_reminder"])

    else:
        return render_template("remember.html")


@app.route("/add-school", methods=["GET", "POST"])
@login_required
def addschool():

    if request.method == "POST":
        db.execute("INSERT INTO schools (user_id, name, icon) VALUES (:id, :name, :icon)",
        id=session["user_id"], name=request.form.get("name"), icon=request.form.get("icon"))

        return redirect("/")
    else:
        return render_template("addschool.html")

@app.route("/courses/<id>")
@login_required
def courses(id):

    todo = db.execute("SELECT * FROM courses WHERE school_id = :id AND status = :status ORDER BY name", id=id, status="todo")
    doing = db.execute("SELECT * FROM courses WHERE school_id = :id AND status = :status ORDER BY name", id=id, status="doing")
    done = db.execute("SELECT * FROM courses WHERE school_id = :id AND status = :status ORDER BY name", id=id, status="done")

    school = db.execute("SELECT name, id FROM schools WHERE id = :id", id=id)

    return render_template("courses.html", todo=todo, doing=doing, done=done, school=school)

@app.route("/add-course/<id>", methods=["POST"])
@login_required
def addcourse(id):

        db.execute("INSERT INTO courses (school_id, name) VALUES (:id, :name)", id=id, name=request.form.get("new-course"))

        return redirect("/courses/" + id)

@app.route("/change-status/<school_id>/<status>/<id>")
@login_required
def changestatus(school_id, status, id):

        db.execute("UPDATE courses SET status = :status WHERE id = :id", status=status, id=id)

        return redirect("/courses/" + school_id)

@app.route("/delete-course/<school_id>/<id>")
@login_required
def deletecourse(school_id, id):

        db.execute("DELETE FROM courses WHERE id = :id", id=id)

        return redirect("/courses/" + school_id)

@app.route("/delete-school/<id>")
@login_required
def deleteschool(id):

        db.execute("DELETE FROM courses WHERE school_id = :id", id=id)
        db.execute("DELETE FROM schools WHERE id = :id", id=id)

        return redirect("/")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

@app.route("/main")
def main():

    return render_template("main.html")

# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)