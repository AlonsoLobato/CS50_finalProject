import os, re

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
db = SQL("sqlite:///database.db")


@app.route("/", methods = ["GET", "POST"])
@login_required
def index():

    """List of active projects of logged user"""

    if request.method == "GET":

        rows = db.execute("SELECT projectId, projectName, clientName, year, month, status, price \
                           FROM projects \
                           WHERE userId = :userId AND status != 'Paid' AND status != 'Waiting for payment'",
                           userId=session["id"])

        projects = []
        for row in rows:
            projects.append({"ID":row["projectId"],"Project":row["projectName"], "Client":row["clientName"],
                             "Year":row["year"], "Month":row["month"], "Status":row["status"],
                             "Price":row["price"]})

        return render_template("index.html", projects = projects)

    else:

        db.execute("UPDATE projects SET status = :status \
                    WHERE userId = :userId AND projectId = :projectId",
                    userId = session["id"],
                    projectId = request.form.get("projectId"),
                    status = request.form.get("status"))

        flash("Project updated successfully!")
        return redirect("/")


@app.route("/waiting", methods = ["GET", "POST"])
@login_required
def waiting():

    """List of projects waiting for payment"""

    if request.method == "GET":

        rows = db.execute("SELECT projectId, projectName, clientName, year, month, status, price \
                           FROM projects WHERE userId = :userId and status = 'Waiting for payment'",
                           userId = session["id"])

        projects = []
        for row in rows:
            projects.append({"ID":row["projectId"], "Project":row["projectName"], "Client":row["clientName"],
                             "Year":row["year"], "Month":row["month"], "Status":row["status"],
                             "Price":row["price"]})

        return render_template("waiting.html", projects = projects)

    else:

        db.execute("UPDATE projects SET status = :status \
                    WHERE userId = :userId AND projectId = :projectId",
                    userId = session["id"],
                    projectId = request.form.get("projectId"),
                    status = request.form.get("status"))

        flash("Project updated successfully!")
        return redirect("/waiting")


@app.route("/finished")
@login_required
def finished():

    """List of finished (paid) projects of logged user"""

    rows = db.execute("SELECT projectId, projectName, clientName, year, month, status, price \
                       FROM projects WHERE userId = :userId and status = 'Paid'",
                       userId = session["id"])

    projects = []
    for row in rows:
        projects.append({"ID":row["projectId"], "Project":row["projectName"], "Client":row["clientName"],
                         "Year":row["year"], "Month":row["month"], "Status":row["status"],
                         "Price":row["price"]})

    return render_template("finished.html", projects = projects)


@app.route("/new", methods = ["GET", "POST"])
@login_required
def new():

    """Add new project to the portfolio"""

    if request.method == "GET":
        return render_template("new.html")

    else:
        # Check for invalid inputs
        if not request.form.get("projectName") or not request.form.get("clientName") or not request.form.get("year") or not request.form.get("month") or not request.form.get("status"):
            return apology("please fill up all the fields", 403)

        if not request.form.get("price") or int(request.form.get("price")) <= 0:
            return apology("price must be more than 0", 403)

        # Insert new project into project portfolio of current user
        db.execute ("INSERT INTO projects (userId, projectName, clientName, year, month, status, price) \
                     VALUES(:userId, :projectName, :clientName, :year, :month, :status, :price)",
                     userId = session["id"],
                     projectName = request.form.get("projectName"),
                     clientName = request.form.get("clientName"),
                     year = request.form.get("year"),
                     month = request.form.get("month"),
                     status = request.form.get("status"),
                     price = "$" + " " + request.form.get("price"))

        flash("Project created successfully!")
        return redirect("/")


@app.route("/summary")
@login_required
def summary():

    """List of all projects (active and finished) of logged user"""

    rows = db.execute("SELECT projectId, projectName, clientName, year, month, status, price \
                       FROM projects \
                       WHERE userId = :userId",
                       userId = session["id"])

    projects = []
    for row in rows:
        projects.append({"ID":row["projectId"], "Project":row["projectName"], "Client":row["clientName"],
                         "Year":row["year"], "Month":row["month"], "Status":row["status"],
                         "Price":row["price"]})

    return render_template("summary.html", projects = projects)


@app.route("/login", methods = ["GET", "POST"])
def login():

    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username and password are submitted
        if not request.form.get("userName"):
            return apology("You must provide an username", 403)
        elif not request.form.get("password"):
            return apology("You must provide a password", 403)

        # Query database for username and ensure it exist and password is correct
        rows = db.execute("SELECT * FROM users WHERE userName = :userName",
                          userName=request.form.get("userName"))

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid username and/or password", 403)

        # Remember which user has logged in
        session["id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():

    """Log user out"""

    # Forget any user_id
    session.clear()

    return redirect("/login")


@app.route("/register", methods = ["GET", "POST"])
def register():

    """Register new user"""

    if request.method == "GET":
        return render_template("register.html")

    else:
        # Check for invalid inputs and if name is already in use
        if not request.form.get("userName"):
            return apology("You must provide an username", 403)

        name_in_use = db.execute("SELECT * FROM users WHERE userName = :userName",
                                  userName = request.form.get("userName"))

        if len(name_in_use) != 0:
            return apology("Sorry, the username is already taken", 403)

        if not request.form.get("password"):
            return apology("You must provide a password", 403)

        if not request.form.get("confirmation"):
            return apology("You must provide a password confirmation", 403)

        if request.form.get("confirmation") != request.form.get("password"):
            return apology("Sorry, password and confirmation don't match", 403)

        if not request.form.get("fullName") or not request.form.get("email"):
            return apology("You must provide full name and email address", 403)

        # Hash password before saving it into database
        hashed_password = generate_password_hash(request.form.get("password"))

        # Add new user to database
        db.execute("INSERT INTO users (userName, hash, fullName, email)\
                    VALUES (:userName, :hashed_password, :fullName, :email)",
                    userName = request.form.get("userName"),
                    hashed_password = hashed_password,
                    fullName = request.form.get("fullName"),
                    email = request.form.get("email"))

        flash("Registered successfully!")
        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)