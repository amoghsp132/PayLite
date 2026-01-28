from fastapi import requests
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, ValidationError
from sqlalchemy import Float, create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
import os
import time
from datetime import datetime
import requests
import qrcode
import qrcode
import io
import base64
from urllib.parse import quote
from flask import Flask, request, jsonify
import sqlite3, re
from flask_cors import CORS
import sqlite3
import uuid




from flask import (
    Flask, render_template, redirect, url_for, request,
    send_from_directory, flash, abort
)
from flask_login import (
    login_user, current_user, logout_user, login_required
)
import os
from flask import send_file
from flask import session




# ----------------- Flask Setup -----------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "porsche911"
CORS(app)

# ----------------- Database Setup -----------------
basedir = os.path.abspath(os.path.dirname(__file__))
if not os.path.exists(os.path.join(basedir, "database")):
    os.makedirs(os.path.join(basedir, "database"))

# DB paths
users_db = f"sqlite:///{os.path.join(basedir, 'database', 'users.db')}"
bank_db = f"sqlite:///{os.path.join(basedir, 'database', 'bank.db')}"
txn_db = f"sqlite:///{os.path.join(basedir, 'database', 'transactions.db')}"
inventory_db = f"sqlite:///{os.path.join(basedir, 'database', 'inventory.db')}"

# Engines
engine_users = create_engine(users_db, echo=True, future=True)
engine_bank = create_engine(bank_db, echo=True, future=True)
engine_txn = create_engine(txn_db, echo=True, future=True)
engine_inventory = create_engine(inventory_db, echo=True, future=True)

# Base classes
BaseUser = declarative_base()
BaseBank = declarative_base()
BaseTxn = declarative_base()
BaseInventory = declarative_base()

# Sessions
SessionUser = scoped_session(sessionmaker(bind=engine_users, expire_on_commit=False))
SessionBank = scoped_session(sessionmaker(bind=engine_bank, expire_on_commit=False))
SessionTxn = scoped_session(sessionmaker(bind=engine_txn, expire_on_commit=False))
SessionInventory = scoped_session(sessionmaker(bind=engine_inventory, expire_on_commit=False))

# ----------------- Models -----------------
class User(BaseUser, UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    fname = Column(String(50))
    lname = Column(String(50))
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(128), nullable=False)
    category = Column(String(20))  # "user" or "merchant"
    

class Inventory(BaseInventory):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    sku = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)
    qty = Column(Integer, nullable=False)

    __table_args__ = (
        # merchant-wise unique SKU
        {'sqlite_autoincrement': True},
    )

@app.route("/api/inventory", methods=["GET"])
@login_required
def get_inventory():
    session = SessionInventory()

    items = (
        session.query(Inventory)
        .order_by(Inventory.name)
        .all()
    )

    data = [
        {
            "name": i.name,
            "sku": i.sku,
            "price": i.price,
            "qty": i.qty
        }
        for i in items
    ]

    session.close()
    return jsonify(data)

@app.route("/api/inventory", methods=["POST"])
@login_required
def add_or_update_inventory():

    if current_user.category != "merchant":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json or {}

    required = ["name", "sku", "price", "qty"]
    if not all(data.get(k) for k in required):
        return jsonify({"error": "Missing fields"}), 400

    session = SessionInventory()

    item = (
        session.query(Inventory)
        .filter(
            Inventory.merchant_email == current_user.email,
            Inventory.sku == data["sku"]
        )
        .first()
    )

    if item:
        item.name = data["name"]
        item.price = float(data["price"])
        item.qty += int(data["qty"])
    else:
        item = Inventory(
            name=data["name"],
            sku=data["sku"],
            price=float(data["price"]),
            qty=int(data["qty"])
        )
        session.add(item)

    session.commit()
    session.close()

    return jsonify({"ok": True})

@app.route("/api/inventory/<sku>", methods=["DELETE"])
@login_required
def delete_inventory_item(sku):

    session = SessionInventory()

    session.query(Inventory).filter(
        Inventory.merchant_email == current_user.email,
        Inventory.sku == sku
    ).delete()

    session.commit()
    session.close()

    return jsonify({"deleted": True})


class Transaction(BaseTxn):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)

    txn_id = Column(String(40), unique=True, nullable=False)
    order_id = Column(String(40), nullable=False)

    sender_account = Column(String(30), nullable=False)
    receiver_account = Column(String(30), nullable=False)

    sender_email = Column(String(120), nullable=False)
    merchant_email = Column(String(120), nullable=False)

    amount = Column(Float, nullable=False)
    method = Column(String(10))   # card / upi
    status = Column(String(15))   # success / failed

    created_at = Column(String(25), nullable=False)



# Create tables
BaseUser.metadata.create_all(engine_users)
BaseBank.metadata.create_all(engine_bank)
BaseTxn.metadata.create_all(engine_txn)
BaseInventory.metadata.create_all(engine_inventory)

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
            raise ValidationError("Invalid email address.")
        elif user:
            flash("Email already registered. Please log in.", "danger")
            raise ValidationError("Email already registered. Please log in.")

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
            flash("User already exists! Please login.", "danger")
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
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("signup.html", form=form)



@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("post_login_redirect"))

    form = LoginForm()
    if form.validate_on_submit():
        with SessionUser() as session:
            user = session.query(User).filter_by(email=form.email.data).first()

            if user and check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for("post_login_redirect"))

            flash("Invalid email or password", "danger")
            return redirect(url_for("login"))

    return render_template("login.html", form=form)

@app.route("/post-login")
@login_required
def post_login_redirect():

    # Normal users → dashboard
    if current_user.category != "merchant":
        return redirect(url_for("dashboard"))

    # Merchant → check KYC
    conn = db()
    c = conn.cursor()
    c.execute("""
        SELECT kyc_verified
        FROM accounts
        WHERE LOWER(fname)=LOWER(?) AND LOWER(lname)=LOWER(?)
        LIMIT 1
    """, (current_user.fname, current_user.lname))

    row = c.fetchone()
    conn.close()

    if row and row["kyc_verified"] == 1:
        return redirect(url_for("dashboard"))

    return redirect(url_for("verifyaccount"))


@app.route("/verify")
@login_required
def verifyaccount():

    # 🚫 Non-merchants never see KYC
    if current_user.category != "merchant":
        return redirect(url_for("dashboard"))

    conn = db()
    c = conn.cursor()

    c.execute("""
        SELECT kyc_verified
        FROM accounts
        WHERE LOWER(fname)=LOWER(?) AND LOWER(lname)=LOWER(?)
        LIMIT 1
    """, (current_user.fname, current_user.lname))

    row = c.fetchone()
    conn.close()

    # ✅ Already verified → dashboard
    if row and row["kyc_verified"] == 1:
        return redirect(url_for("dashboard"))

    # ❗ Not verified → show KYC page
    return render_template("verify.html")

@app.route("/dashboard")
@login_required
def dashboard():

    weeks = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    session_txn = SessionTxn()

    try:
        # -------------------------------
        # FILTER TRANSACTIONS BY ROLE
        # -------------------------------
        if current_user.category == "merchant":
            txns = (
                session_txn.query(Transaction)
                .filter(Transaction.merchant_email == current_user.email)
                .order_by(Transaction.id.desc())
                .limit(50)
                .all()
            )
            baseline = 100000
        else:
            txns = (
                session_txn.query(Transaction)
                .filter(Transaction.sender_email == current_user.email)
                .order_by(Transaction.id.desc())
                .limit(50)
                .all()
            )
            baseline = 50000

        # -------------------------------
        # PROCESS DATA
        # -------------------------------
        total_amount = sum(t.amount for t in txns if t.status == "success")

        percentage = min(100, round((total_amount / baseline) * 100, 2))

        transactions_data = []
        for t in txns:
            dt = datetime.strptime(t.created_at, "%Y-%m-%d %H:%M:%S")
            transactions_data.append({
                "txn_id": t.txn_id,
                "order_id": t.order_id,
                "amount": t.amount,
                "status": t.status,
                "date": dt.strftime("%Y-%m-%d"),
                "time": dt.strftime("%H:%M:%S")
            })

        income_data = [t.amount for t in txns if t.status == "success"][:7]

        while len(income_data) < 7:
            income_data.append(0)

        # -------------------------------
        # RENDER
        # -------------------------------
        if current_user.category == "merchant":
            return render_template(
                "merchantD.html",
                merchant_name=f"{current_user.fname} {current_user.lname}",
                weeks=weeks,
                income=income_data,
                percentage=percentage,
                transactions=transactions_data
            )

        return render_template(
            "userD.html",
            user_name=f"{current_user.fname} {current_user.lname}",
            weeks=weeks,
            income=income_data,
            percentage=percentage,
            transactions=transactions_data
        )

    finally:
        session_txn.close()



@app.route("/localMart")
def localMart():
    return render_template("localMart.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

#fetch database values
# ---------- user.db helpers (add this) ----------
def userdb():
    conn = sqlite3.connect("user.db")
    conn.row_factory = sqlite3.Row
    return conn

def fetch_logged_user_row(
    log_id=None, upi_id=None, bank_account_no=None, fname=None, lname=None
):
    q = "SELECT * FROM logged_users"
    clauses, params = [], []

    if log_id:
        clauses.append("id = ?")
        params.append(int(log_id))
    if upi_id:
        clauses.append("LOWER(TRIM(upi_id)) = LOWER(TRIM(?))")
        params.append(upi_id)
    if bank_account_no:
        clauses.append("TRIM(bank_account_no) = TRIM(?)")
        params.append(bank_account_no)
    if fname and lname:
        clauses.append("LOWER(TRIM(fname)) = LOWER(TRIM(?))")
        clauses.append("LOWER(TRIM(lname)) = LOWER(TRIM(?))")
        params.extend([fname, lname])

    if clauses:
        q += " WHERE " + " AND ".join(clauses)

    q += " ORDER BY id DESC LIMIT 1"

    conn = userdb()
    row = conn.execute(q, params).fetchone()
    conn.close()
    return dict(row) if row else None

def init_order_seq():
    conn = userdb()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_seq (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
    """)
    conn.commit()
    conn.close()

def next_order_id():
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = uuid.uuid4().hex[:6].upper()
    return f"ORD-{ts}-{rand}"

def generate_intent_id():
    return f"INTENT-{uuid.uuid4().hex[:12].upper()}"

def generate_txn_id():
    return f"TXN-{uuid.uuid4().hex[:16].upper()}"


@app.route("/widget_preview", methods=["GET"])
def widget_preview():
    """
    Simple preview page for the UPI QR widget.
    """
    return render_template("widget_preview.html")


def log_dashboard_transaction(
    txn_id,                 # 🔥 ADD THIS
    sender_acc,
    receiver_acc,
    amount,
    method,
    status,
    order_id,
    sender_email,
    merchant_email
):
    session_txn = SessionTxn()
    session_txn.add(Transaction(
        txn_id=txn_id,           # ✅ USE PASSED ID
        order_id=order_id,
        sender_account=sender_acc,
        receiver_account=receiver_acc,
        sender_email=sender_email,
        merchant_email=merchant_email,
        amount=amount,
        method=method,
        status=status,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    session_txn.commit()
    session_txn.close()


@app.route("/api/widget/manual-result", methods=["POST"])
def widget_manual_result():

    data = request.json or {}

    status    = data.get("status")          # success | failed | pending
    amount    = float(data.get("amount", 0))
    order_id  = data.get("order_id")
    payee_upi = data.get("payee_upi")

    # -------------------------------
    # Validate status
    # -------------------------------
    if status not in ("success", "failed", "pending"):
        return jsonify({"ok": False, "error": "Invalid status"}), 400

    # -------------------------------
    # FINAL STATE PROTECTION
    # -------------------------------
    if status in ("success", "failed") and session.get("finalized"):
        return jsonify({"ok": False, "error": "Payment already finalized"}), 409

    # -------------------------------
    # Dummy accounts (test flow)
    # -------------------------------
    sender_acc   = "TEST-SENDER"
    receiver_acc = payee_upi or "TEST-MERCHANT"

    now = datetime.now()
    created_at = now.strftime("%Y-%m-%d %H:%M:%S")

    txn_id = generate_txn_id()

    # -------------------------------
    # Log transaction
    # -------------------------------
    session_txn = SessionTxn()
    session_txn.add(Transaction(
        txn_id=txn_id,
        order_id=order_id or "MANUAL",
        sender_account=sender_acc,
        receiver_account=receiver_acc,
        sender_email=(
            current_user.email
            if current_user.is_authenticated
            else "guest@paylite"
        ),
        merchant_email=(
            current_user.email
            if current_user.is_authenticated and current_user.category == "merchant"
            else "merchant@paylite"
        ),
        amount=amount,
        method="manual",
        status=status,
        created_at=created_at
    ))
    session_txn.commit()
    session_txn.close()

    # -------------------------------
    # Mark finalized ONLY if final
    # -------------------------------
    if status in ("success", "failed"):
        session["finalized"] = True

        # cleanup payment session
        session.pop("order_id", None)
        session.pop("amount", None)
        session.pop("intent_id", None)
        session.pop("payee_upi", None)

    # -------------------------------
    # Response
    # -------------------------------
    return jsonify({
        "ok": True,
        "status": status,
        "txn_id": txn_id,
        "amount": amount,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S")
    })



#--------------------------------------------------------------default qr code settings
# --------------------------------------------------------------
# DEFAULT MERCHANT PAYMENT DETAILS (AUTO-FILL FOR DOCS / TEST PAGE)
# --------------------------------------------------------------
@app.route("/api/merchant/payment-defaults")
@login_required
def merchant_payment_defaults():

    if current_user.category != "merchant":
        return jsonify({"error": "Unauthorized"}), 403

    conn = db()
    c = conn.cursor()

    c.execute("""
        SELECT upi_id, fname, lname
        FROM accounts
        WHERE LOWER(fname)=LOWER(?) AND LOWER(lname)=LOWER(?)
        LIMIT 1
    """, (current_user.fname, current_user.lname))

    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Merchant bank account not found"}), 404

    return jsonify({
        "pa": row["upi_id"],                      # Payee UPI
        "pn": f"{row['fname']} {row['lname']}",  # Payee Name
        "cu": "INR"
    })

#--------------------------------------------------------------@app.route("/widget", methods=["GET"])

@app.route("/widget", methods=["GET"])
def widget():
    # ----------------------------
    # PAYMENT INTENT (PRE-TXN)
    # ----------------------------
    session.pop("finalized", None)

    intent_id = session.get("intent_id")
    if not intent_id:
        intent_id = generate_intent_id()
        session["intent_id"] = intent_id

    """
    Universal widget renderer.
    Supports:
    - Full UPI query params (pa, pn, tn, tr, mc, cu, am)
    - Logged-in merchant auto-fill
    - Safe fallback to DB
    """

    # ----------------------------
    # 1️⃣ READ QUERY PARAMS (DOCS / TEST MODE)
    # ----------------------------
    pa = request.args.get("pa", "").strip().lower()      # Payee UPI
    pn = request.args.get("pn", "").strip()              # Payee Name
    tn = request.args.get("tn", "").strip() or "Payment" # Note
    tr = request.args.get("tr", "").strip()              # Txn Ref
    mc = request.args.get("mc", "").strip()              # MCC
    cu = request.args.get("cu", "INR").strip()
    am = request.args.get("amount") or request.args.get("am")

    # normalize amount
    try:
        am = f"{float(am):.2f}" if am else ""
    except:
        am = ""

    # ----------------------------
    # 2️⃣ FALLBACK TO LOGGED USER DB
    # ----------------------------
    row = None
    if not pa:
        row = fetch_logged_user_row(
            log_id=request.args.get("id"),
            upi_id=request.args.get("upi_id"),
            bank_account_no=request.args.get("bank_account_no")
        )

        if not row and current_user.is_authenticated:
            row = fetch_logged_user_row(
                fname=current_user.fname,
                lname=current_user.lname
            )

        if not row:
            return abort(404, description="No matching merchant found")

        pa = row["upi_id"].lower()
        pn = pn or f"{row['fname']} {row['lname']}".strip()

    # ----------------------------
    # 3️⃣ ORDER ID (SAFE + UNIQUE)
    # ----------------------------
    order_id = session.get("order_id")
    if not order_id:
        order_id = next_order_id()

        session["order_id"] = order_id
    order_id = request.args.get("order_id") or session.get("order_id")
    if not order_id:
        order_id = next_order_id()
        session["order_id"] = order_id

    # ----------------------------
    # 4️⃣ BUILD UPI URI (STANDARD COMPLIANT)
    # ----------------------------
    parts = [
        f"pa={pa}",
        f"pn={quote(pn)}",
        f"tn={quote(tn)}",
        f"cu={cu}"
    ]

    if am:
        parts.insert(3, f"am={am}")

    if tr:
        parts.append(f"tr={quote(tr)}")

    if mc:
        parts.append(f"mc={quote(mc)}")

    upi_uri = "upi://pay?" + "&".join(parts)

    # ----------------------------
    # 5️⃣ GENERATE QR
    # ----------------------------
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(upi_uri)
    qr.make(fit=True)
    img = qr.make_image()

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode()

    # ----------------------------
    # 6️⃣ STORE SESSION FOR PAYMENT API
    # ----------------------------
    session["payee_upi"] = pa
    session["amount"] = am

    # ----------------------------
    # 7️⃣ RENDER
    # ----------------------------
    return render_template(
    "widget.html",
    qr_code=f"data:image/png;base64,{qr_base64}",
    upi_uri=upi_uri,
    upi_id=pa,
    payee_name=pn,
    amount=am,
    note=tn,
    order_id=order_id,
    payee_upi=pa,
    intent_id=intent_id   # 🔥 ADD THIS
    )   


def get_merchant_account_no(user):
    conn = db()
    c = conn.cursor()
    c.execute("""
        SELECT bank_account_no
        FROM accounts
        WHERE LOWER(upi_id) = (
            SELECT LOWER(upi_id)
            FROM accounts
            WHERE LOWER(fname)=LOWER(?) AND LOWER(lname)=LOWER(?)
            LIMIT 1
        )
        LIMIT 1
    """, (user.fname, user.lname))
    row = c.fetchone()
    conn.close()
    return row["bank_account_no"] if row else None

@app.route("/ecom")
def ecommerce_testing():
    return render_template("ecommerce_testing.html")

#card_-------------------------------------------------------------------------------------------------
@app.route("/api/widget/pay", methods=["POST"])
def widget_pay():
    import time

    data = request.json or {}

    # -----------------------------
    # INPUT NORMALIZATION
    # -----------------------------
    method   = (data.get("method") or "").lower()
    amount   = data.get("amount") or session.get("amount") or "0"
    to_upi   = (data.get("to_upi") or session.get("payee_upi") or "").strip().lower()
    order_id = data.get("order_id") or session.get("order_id")

    try:
        amount = float(amount)
    except:
        return jsonify({"ok": False, "error": "Invalid amount"}), 400

    if amount <= 0:
        return jsonify({"ok": False, "error": "Amount must be > 0"}), 400
    if not to_upi:
        return jsonify({"ok": False, "error": "Missing payee UPI"}), 400
    if method not in ("card", "upi"):
        return jsonify({"ok": False, "error": f"Unsupported method '{method}'"}), 400

    # -----------------------------
    # SQLITE RETRY LOOP (LOCK SAFE)
    # -----------------------------
    attempts = 5
    delay = 0.2

    for _ in range(attempts):
        conn = None
        try:
            conn = bank_conn()
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")

            # -----------------------------
            # RECEIVER
            # -----------------------------
            c.execute(
                "SELECT bank_account_no FROM accounts WHERE LOWER(TRIM(upi_id)) = ?",
                (to_upi,)
            )
            rec = c.fetchone()
            if not rec:
                raise ValueError("Receiver not found")

            # -----------------------------
            # SENDER
            # -----------------------------
            if method == "card":
                card_no = re.sub(r"\D", "", data.get("card_no", ""))
                cvv     = (data.get("cvv") or "").strip()
                exp     = (data.get("exp_date") or "").strip()

                c.execute("""
                    SELECT bank_account_no, balance
                    FROM accounts
                    WHERE REPLACE(card_no, ' ', '') = ?
                      AND TRIM(cvv) = ?
                      AND TRIM(exp_date) = ?
                """, (card_no, cvv, exp))
            else:
                from_upi = (data.get("from_upi") or "").strip().lower()
                c.execute("""
                    SELECT bank_account_no, balance
                    FROM accounts
                    WHERE LOWER(TRIM(upi_id)) = ?
                """, (from_upi,))

            sender = c.fetchone()
            if not sender:
                raise ValueError("Sender not found / invalid credentials")

            # -----------------------------
            # ATOMIC BALANCE UPDATE
            # -----------------------------
            c.execute("""
                UPDATE accounts
                SET balance = balance - ?
                WHERE bank_account_no = ?
                  AND balance >= ?
            """, (amount, sender["bank_account_no"], amount))

            if c.rowcount != 1:
                raise ValueError("Insufficient balance")

            c.execute("""
                UPDATE accounts
                SET balance = balance + ?
                WHERE bank_account_no = ?
            """, (amount, rec["bank_account_no"]))

            # -----------------------------
            # BANK TRANSACTION LOG
            # -----------------------------
            c.execute("""
                INSERT INTO transactions
                (from_account, to_account, amount, transaction_type, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                sender["bank_account_no"],
                rec["bank_account_no"],
                amount,
                method,
                f"success:{order_id}"
            ))

            # -----------------------------
            # DASHBOARD TRANSACTION LOG
            # -----------------------------
            txn_uid = generate_txn_id()

            log_dashboard_transaction(
                txn_id=txn_uid,   # 🔥 SAME ID EVERYWHERE
                sender_acc=sender["bank_account_no"],
                receiver_acc=rec["bank_account_no"],
                amount=amount,
                method=method,
                status="success",
                order_id=order_id,
                sender_email=(
                    current_user.email
                    if current_user.is_authenticated
                    else "guest@paylite"
                ),
                merchant_email="merchant@paylite"
            )

            conn.commit()

            return jsonify({
                "ok": True,
                "txn_id": txn_uid,
                "order_id": order_id
            }), 200


        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                if conn:
                    conn.rollback()
                time.sleep(delay)
                delay *= 1.5
                continue
            if conn:
                conn.rollback()
            return jsonify({"ok": False, "error": str(e)}), 400

        except Exception as e:
            if conn:
                conn.rollback()
            return jsonify({"ok": False, "error": str(e)}), 400

        finally:
            if conn:
                conn.close()

    return jsonify({"ok": False, "error": "Database busy, please retry"}), 503



    #https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=upi://pay?pa=9964043633@ybl&pn=Paylite&am=99&cu=INR&tn=Payment%20for%20services or https://quickchart.io/qr?text=upi://pay?pa=9964043633@ybl&pn=Paylite&am=99&cu=INR&tn=Payment%20for%20services&size=250
#------------------------IMAGE GEN------------------------------
@app.route("/api/qr.png")
def api_qr_png():
    upi_id = request.args.get("upi_id")
    if not upi_id:
        # allow selecting by id or account no
        row = fetch_logged_user_row(
            log_id=request.args.get("id"),
            bank_account_no=request.args.get("bank_account_no")
        )
        if not row:
            return abort(400, description="Provide upi_id or a valid id/bank_account_no")
        upi_id = row["upi_id"]

    payee_name = request.args.get("name", "Payee")
    note = request.args.get("note", "Payment")
    amount = request.args.get("amount", "")

    try:
        amount = f"{float(amount):.2f}"
    except Exception:
        amount = ""

    parts = [f"pa={upi_id}", f"pn={quote(payee_name)}", f"tn={quote(note)}", "cu=INR"]
    if amount:
        parts.insert(3, f"am={amount}")

    uri = "upi://pay?" + "&".join(parts)

    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image()

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", as_attachment=False, download_name="upi_qr.png")

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


#Bank
def init_db():
    conn = sqlite3.connect('bank.db')
    c = conn.cursor()

    # ACCOUNTS
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fname TEXT,
            lname TEXT,
            cvv TEXT,
            card_no TEXT UNIQUE,
            exp_date TEXT,
            upi_id TEXT UNIQUE,
            bank_account_no TEXT UNIQUE,
            balance REAL DEFAULT 0.0,
            kyc_verified INTEGER DEFAULT 0
        )
    ''')

    # TRANSACTIONS
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_account TEXT,
            to_account TEXT,
            amount REAL,
            transaction_type TEXT,
            status TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def db():
    conn = sqlite3.connect("bank.db")
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------
# VALIDATIONS
# --------------------------
def validate_card(card):
    return card.isdigit() and len(card) == 16

def validate_cvv(cvv):
    return cvv.isdigit() and len(cvv) == 3

def validate_upi(upi):
    return bool(re.match(r'^[\w.-]+@[\w.-]+$', upi))


# --------------------------
# ROUTES
# --------------------------

# CREATE ACCOUNT
@app.route("/api/account/create", methods=["POST"])
def create_account():
    data = request.json

    required = ["fname","lname","cvv","card_no","exp_date","upi_id","bank_account_no"]
    for f in required:
        if f not in data:
            return jsonify({"error":f"{f} missing"}), 400

    if not validate_card(data["card_no"]):
        return jsonify({"error":"Invalid card number"}), 400

    if not validate_cvv(data["cvv"]):
        return jsonify({"error":"Invalid CVV"}), 400

    if not validate_upi(data["upi_id"]):
        return jsonify({"error":"Invalid UPI ID"}), 400

    try:
        conn = db()
        c = conn.cursor()

        c.execute("""
            INSERT INTO accounts
            (fname,lname,cvv,card_no,exp_date,upi_id,bank_account_no,balance)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            data["fname"], data["lname"], data["cvv"], data["card_no"],
            data["exp_date"], data["upi_id"], data["bank_account_no"],
            data.get("balance", 0.0)
        ))

        conn.commit()
        return jsonify({"message":"Account created"})

    except sqlite3.IntegrityError:
        return jsonify({"error":"Card/UPI/Acc already exists"}), 409

    finally:
        conn.close()


# GET ALL ACCOUNTS
@app.route("/api/accounts/all")
def all_accounts():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM accounts")
    data = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(data)


# ADD MONEY
@app.route("/api/account/addmoney", methods=["POST"])
def add_money():
    data = request.json
    account_no = data.get("account_no")
    amount = float(data.get("amount",0))

    conn = db()
    c = conn.cursor()

    c.execute("UPDATE accounts SET balance = balance + ? WHERE bank_account_no = ?", (amount, account_no))
    conn.commit()
    conn.close()

    return jsonify({"message":"Money added", "amount":amount})


# NORMAL TRANSFER
@app.route("/api/transaction/transfer", methods=["POST"])
def transfer():
    data = request.json

    from_acc = data["from_account"]
    to_acc = data["to_account"]
    amount = float(data["amount"])

    conn = db()
    c = conn.cursor()

    # Check sender
    c.execute("SELECT balance FROM accounts WHERE bank_account_no=?", (from_acc,))
    sender = c.fetchone()
    if not sender:
        return jsonify({"error":"Sender not found"}), 404

    if sender["balance"] < amount:
        return jsonify({"error":"Insufficient balance"}), 400

    # Check receiver
    c.execute("SELECT id FROM accounts WHERE bank_account_no=?", (to_acc,))
    if not c.fetchone():
        return jsonify({"error":"Receiver not found"}), 404

    # Process
    c.execute("UPDATE accounts SET balance = balance - ? WHERE bank_account_no=?", (amount, from_acc))
    c.execute("UPDATE accounts SET balance = balance + ? WHERE bank_account_no=?", (amount, to_acc))

    # Log
    c.execute("""
        INSERT INTO transactions (from_account,to_account,amount,transaction_type,status)
        VALUES (?,?,?,?,?)
    """, (from_acc,to_acc,amount,"transfer","success"))

    txn_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"message":"Transfer OK", "transaction_id":txn_id})


# UPI TRANSFER
@app.route("/api/transaction/upi", methods=["POST"])
def upi_pay():
    data = request.json
    from_upi = data["from_upi"]
    to_upi = data["to_upi"]
    amount = float(data["amount"])

    conn = db()
    c = conn.cursor()

    # Sender
    c.execute("SELECT bank_account_no,balance FROM accounts WHERE upi_id=?", (from_upi,))
    sender = c.fetchone()
    if not sender:
        return jsonify({"error":"Sender UPI not found"}), 404

    if sender["balance"] < amount:
        return jsonify({"error":"Insufficient funds"}), 400

    # Receiver
    c.execute("SELECT bank_account_no FROM accounts WHERE upi_id=?", (to_upi,))
    receiver = c.fetchone()
    if not receiver:
        return jsonify({"error":"Receiver UPI not found"}), 404

    # Process
    c.execute("UPDATE accounts SET balance = balance - ? WHERE upi_id=?", (amount, from_upi))
    c.execute("UPDATE accounts SET balance = balance + ? WHERE upi_id=?", (amount, to_upi))

    c.execute("""
        INSERT INTO transactions (from_account,to_account,amount,transaction_type,status)
        VALUES (?,?,?,?,?)
    """, (sender["bank_account_no"], receiver["bank_account_no"], amount, "upi", "success"))

    txn_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"message":"UPI Success", "transaction_id":txn_id})


# GET TRANSACTIONS
@app.route("/api/transactions/<acc>")
def get_txns(acc):
    conn = db()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM transactions
        WHERE from_account=? OR to_account=?
        ORDER BY timestamp DESC LIMIT 50
    """, (acc,acc))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/health")
def health():
    return jsonify({"status":"bank ok"})




#kyc
@app.route("/api/account/verify", methods=["POST"])
@login_required
def verify_account():

    # -------------------------------
    # MERCHANT ONLY
    # -------------------------------
    if current_user.category != "merchant":
        return jsonify({"verified": False, "error": "Unauthorized"}), 403

    data = request.json or {}

    # -------------------------------
    # REQUIRED FIELDS
    # -------------------------------
    required = ["cvv", "card_no", "exp_date", "upi_id", "bank_account_no"]
    for f in required:
        if not data.get(f):
            return jsonify({"verified": False, "error": f"{f} missing"}), 400

    # -------------------------------
    # NORMALIZATION
    # -------------------------------
    cvv = data["cvv"].strip()
    card_no = re.sub(r"\D", "", data["card_no"])  # digits only
    upi_id = data["upi_id"].strip().lower()
    bank_account_no = data["bank_account_no"].strip()

    exp_raw = data["exp_date"].strip()
    exp_mm_yy = exp_raw[:5] if "/" in exp_raw else exp_raw
    exp_mm_yyyy = None

    if "/" in exp_raw:
        m, y = exp_raw.split("/")
        if len(y) == 2:
            exp_mm_yyyy = f"{m.zfill(2)}/20{y}"
        elif len(y) == 4:
            exp_mm_yyyy = exp_raw

    # -------------------------------
    # DATABASE MATCH
    # -------------------------------
    conn = db()
    c = conn.cursor()

    c.execute("""
        SELECT id, fname, lname, balance, kyc_verified, exp_date
        FROM accounts
        WHERE
            REPLACE(card_no, ' ', '') = ?
        AND TRIM(cvv) = ?
        AND LOWER(TRIM(upi_id)) = ?
        AND TRIM(bank_account_no) = ?
        AND (
            TRIM(exp_date) = ?
            OR TRIM(exp_date) = ?
        )
        LIMIT 1
    """, (
        card_no,
        cvv,
        upi_id,
        bank_account_no,
        exp_mm_yy,
        exp_mm_yyyy
    ))

    row = c.fetchone()

    # -------------------------------
    # DEBUG LOG (SAFE)
    # -------------------------------
    if not row:
        print("[KYC FAILED]")
        print("INPUT →", {
            "cvv": cvv,
            "card_no": card_no[-4:],
            "upi": upi_id,
            "exp": exp_raw,
            "bank_acc": bank_account_no
        })

        c.execute("SELECT card_no, cvv, exp_date, upi_id FROM accounts")
        print("DB →", c.fetchall())

        conn.close()
        return jsonify({"verified": False}), 200

    # -------------------------------
    # SET KYC ONLY ONCE
    # -------------------------------
    if row["kyc_verified"] == 0:
        c.execute(
            "UPDATE accounts SET kyc_verified = 1 WHERE id = ?",
            (row["id"],)
        )
        conn.commit()
        print(f"[KYC ACTIVATED] Account ID {row['id']}")

    conn.close()

    # -------------------------------
    # SUCCESS RESPONSE
    # -------------------------------
    return jsonify({
        "verified": True,
        "kyc_verified": True,
        "balance": row["balance"]
    })




# ADD THIS ENDPOINT TO server.py
@app.route("/api/log_user", methods=["POST"])
def log_user():
    data = request.json
    conn = sqlite3.connect("user.db")
    c = conn.cursor()
    c.execute("""
CREATE TABLE IF NOT EXISTS logged_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fname TEXT,
    lname TEXT,
    card_no TEXT,
    cvv TEXT,
    exp_date TEXT,
    upi_id TEXT,
    bank_account_no TEXT,
    timestamp TEXT,
    kyc_verified INTEGER DEFAULT 0
)
""")

    c.execute("""INSERT INTO logged_users 
                 (fname, lname, card_no, cvv, exp_date, upi_id, bank_account_no, timestamp, kyc_verified)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (data.get("fname"), data.get("lname"), data.get("card_no"), data.get("cvv"),
               data.get("exp_date"), data.get("upi_id"), data.get("bank_account_no"),
               data.get("timestamp", "unknown"), data.get("kyc_verified", 0)))
    conn.commit()
    conn.close()
    return jsonify({"status": "logged"}), 200

# ----------------- Run -----------------

def bank_conn():
    conn = sqlite3.connect("bank.db", timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")  # 10s
    return conn

def tune_bank_sqlite():
    with sqlite3.connect("bank.db") as conn:
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL")      # better concurrency
        c.execute("PRAGMA synchronous=NORMAL")    # sane durability/perf
        c.execute("PRAGMA busy_timeout=5000")     # wait up to 5s for locks
        conn.commit()
@app.route("/bank")
def bank():
    return render_template("dbank.html")
# call it early in __main__
if __name__ == "__main__":
    init_db()
    tune_bank_sqlite()
    #init_order_seq()
    app.run(debug=True, use_reloader=False)  # <— disable reloader to avoid double-process locks
