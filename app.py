from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
import os
import datetime

SECRET_KEY = os.environ["SECRET_KEY"]


app = Flask(__name__)
app.secret_key = SECRET_KEY   # Needed for session

# MongoDB connection
client = MongoClient("mongodb+srv://omrathod856_db_user:pcsUeuFye0EQRGFu@cluster0.8sevinr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",tls=True, tlsAllowInvalidCertificates=True)
db = client["health_advisor_db"]
users = db["users"]

bcrypt = Bcrypt(app)

# Home route
@app.route("/")
def home():
    return redirect(url_for("login"))

# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check if user exists
        if users.find_one({"username": username}):
            flash("Username already exists!", "error")
            return redirect(url_for("register"))

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        users.insert_one({"username": username, "password": hashed_pw})
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users.find_one({"username": username})
        if user and bcrypt.check_password_hash(user["password"], password):
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password", "error")

    return render_template("login.html")

# Dashboard
@app.route("/dashboard")
def dashboard():
    if "username" in session:
        # Fetch user from MongoDB
        user = users.find_one({"username": session["username"]})
        profile = user.get('profile', {}) if user else {}
        return render_template("dashboard.html", username=session["username"], profile=profile)
    return redirect(url_for("login"))


# Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# Profile
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "username" not in session:
        return redirect(url_for("login"))

    user = users.find_one({"username": session["username"]})
    if request.method == "POST":
        # Collect form data
        age = int(request.form["age"])
        height = float(request.form["height"])
        weight = float(request.form["weight"])
        gender = request.form["gender"]
        activity_level = request.form["activity_level"]
        diet_preference = request.form["diet_preference"]

        # Calculate BMI
        height_m = height / 100  # cm -> m
        bmi = round(weight / (height_m ** 2), 2)

        # Categorize BMI
        if bmi < 18.5:
            category = "Underweight"
        elif 18.5 <= bmi < 24.9:
            category = "Normal"
        elif 25 <= bmi < 29.9:
            category = "Overweight"
        else:
            category = "Obese"

        # Prepare profile data for DB
        profile_data = {
            "age": age,
            "height": height,
            "weight": weight,
            "gender": gender,
            "activity_level": activity_level,
            "diet_preference": diet_preference,
            "last_bmi": {
                "value": bmi,
                "category": category,
                "date": datetime.datetime.combine(datetime.date.today(), datetime.time())
            }
        }

        # Save profile (overwrite existing profile field)
        users.update_one(
            {"username": session["username"]},
            {"$set": {"profile": profile_data}}
        )

        # Save BMI history (append to array)
        users.update_one(
            {"username": session["username"]},
            {"$push": {
                "bmi_history": {
                    "value": bmi,
                    "category": category,
                    "date": datetime.datetime.combine(datetime.date.today(), datetime.time())
                }
            }}
        )

        flash("Profile updated and BMI calculated!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port=5000,debug=True)


