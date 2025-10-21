from dataclasses import field
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length
from sqlalchemy import Float, create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
import os
import time
from wtforms.validators import ValidationError


# ----------------- Flask Setup -----------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "porsche911"

# ----------------- Database Setup -----------------
basedir = os.path.abspath(os.path.dirname(__file__))
if not os.path.exists(os.path.join(basedir, "database")):
    os.makedirs(os.path.join(basedir, "database"))

# User and Bank DB paths
users_db = f"sqlite:///{os.path.join(basedir, 'database', 'users.db')}"
bank_db = f"sqlite:///{os.path.join(basedir, 'database', 'bank.db')}"
txn_db = f"sqlite:///{os.path.join(basedir, 'database', 'transactions.db')}"
# Engines
engine_users = create_engine(users_db, echo=True, future=True)
engine_bank = create_engine(bank_db, echo=True, future=True)
engine_txn = create_engine(txn_db, echo=True, future=True)

# Base classes
BaseUser = declarative_base()
BaseBank = declarative_base()
BaseTxn = declarative_base()

# Sessions
SessionUser = scoped_session(sessionmaker(bind=engine_users, expire_on_commit=False))
SessionBank = scoped_session(sessionmaker(bind=engine_bank, expire_on_commit=False))
SessionTxn = scoped_session(sessionmaker(bind=engine_txn, expire_on_commit=False))

# ----------------- Models -----------------
class User(BaseUser, UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    fname = Column(String(50))
    lname = Column(String(50))
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(128), nullable=False)
    category = Column(String(20))  # "user" or "merchant"

class Bank(BaseBank):
    __tablename__ = "bank"
    id = Column(Integer, primary_key=True)
    fname = Column(String(50))
    lname = Column(String(50))
    account_no = Column(String(30))
    card_no = Column(String(30))
    ifsc = Column(String(20))
    upi_id = Column(String(50))
    cvv = Column(String(10))
    expiry = Column(String(10))
    
class Transaction(BaseBank):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer)
    receiver_id = Column(Integer)
    amount = Column(Float)
    status = Column(String(20))  # "Success", "Pending", "Failed"
    date = Column(String(20))
    time = Column(String(20))
    
    

# Create tables if not exist
BaseUser.metadata.create_all(engine_users)
BaseBank.metadata.create_all(engine_bank)


# ----------------- Forms -----------------
class RegisterForm(FlaskForm):
    fname = StringField("First Name", validators=[DataRequired()])
    lname = StringField("Last Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    is_merchant = BooleanField("Register as Merchant")
    submit = SubmitField("Sign Up")

    def validate_email(self, field):
        session = SessionUser()
        user = session.query(User).filter_by(email=field.data).first()
        session.close()
        if "@" not in field.data or "." not in field.data:
            flash("Invalid email address.", "danger")
            raise ValidationError("Invalid email address.", "danger")
        elif user:
            flash("Email already registered. Please log in.", "danger")
            raise ValidationError("Email already registered. Please log in.", "danger")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")

# ----------------- Flask-Login -----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    with SessionUser() as session:
        return session.get(User, int(user_id))

# ----------------- Routes -----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        session = SessionUser()
        user = session.query(User).filter_by(email=form.email.data).first()
        if user:
            flash("User already exists! Please login.", "danger")  # Use flash
            return redirect(url_for("login"))
        else:
            category = "merchant" if form.is_merchant.data else "user"
            new_user = User(
                fname=form.fname.data,
                lname=form.lname.data,
                email=form.email.data,
                password=generate_password_hash(
                    form.password.data,
                    method='pbkdf2:sha256',
                    salt_length=16
                ),
                category=category
            )
            session.add(new_user)
            session.commit()
            flash("Registration successful!\nPlease log in.", "success")  # Use flash
            return redirect(url_for("login"))
    return render_template("signup.html", form=form)



@app.route("/login", methods=["GET", "POST"])
def login():
    
    
    
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        with SessionUser() as session:
            user = session.query(User).filter_by(email=form.email.data).first()
            if user and check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid email or password", "danger")
                return redirect(url_for("login"))
                

    return render_template("login.html", form=form)

@app.route("/dashboard")
@login_required
def dashboard():
    
    weeks = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    income = [120, 150, 180, 90, 200, 170, 220]
    percentage = 75
    transactions = [
        {"id": 1, "amount": 150.00, "status": "Success", "date": "2024-10-01", "time": "10:30 AM"},
        {"id": 2, "amount": 200.00, "status": "Pending", "date": "2024-10-02", "time": "09:45 AM"},
        {"id": 3, "amount": 120.00, "status": "Failed", "date": "2024-10-03", "time": "11:15 AM"},
        {"id": 4, "amount": 300.00, "status": "Success", "date": "2024-10-04", "time": "02:20 PM"},
        {"id": 5, "amount": 250.00, "status": "Success", "date": "2024-10-05", "time": "01:10 PM"},
        {"id": 6, "amount": 180.00, "status": "Pending", "date": "2024-10-06", "time": "03:30 PM"},
        {"id": 7, "amount": 220.00, "status": "Success", "date": "2024-10-07", "time": "12:00 PM"},
    ]
    
    if current_user.category == "merchant":
        return render_template("merchantD.html", user=current_user, weeks=weeks, income=income, percentage=percentage, transactions=transactions, merchant_name=current_user.fname + " " + current_user.lname)
    return render_template("userD.html", user=current_user, weeks=weeks, income=income, percentage=percentage, transactions=transactions, user_name=current_user.fname + " " + current_user.lname)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/widget")
def widget():
    return render_template("widget.html")

# ----------------- Placeholder APIs -----------------
@app.route("/upi_sender", methods=["POST"])
def upi_sender():
    return {"status": "UPI payment sent"}

@app.route("/upi_receiver", methods=["POST"])
def upi_receiver():
    return {"status": "UPI payment received"}

@app.route("/chatbot", methods=["POST"])
def chatbot():
    return {"response": "Chatbot reply goes here"}

@app.route("/analytics")
def analytics():
    return {"status": "Analytics generated"}

# ----------------- Run -----------------
if __name__ == "__main__":
    app.run(debug=True)
