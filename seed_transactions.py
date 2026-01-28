import sqlite3
import uuid
import random
from datetime import datetime, timedelta

DB_PATH = "database/transactions.db"

MERCHANTS = [
    "merchant@paylite",
    "shop@paylite",
    "amoghpatil132@gmail.com",
]

USERS = [
    "user1@paylite",
    "user2@paylite",
    "guest@paylite",
    "user@gmail.com"
]

METHODS = ["card", "upi", "manual"]
STATUSES = ["success", "failed", "pending"]

def generate_txn_id():
    return f"TXN-{uuid.uuid4().hex[:16].upper()}"

def generate_order_id():
    ts = datetime.now().strftime("%Y%m%d")
    rand = uuid.uuid4().hex[:6].upper()
    return f"ORD-{ts}-{rand}"

def random_date(days_back=14):
    dt = datetime.now() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("⚙️ Populating transactions.db ...")

    rows = []

    for _ in range(80):  # 👈 TOTAL TRANSACTIONS
        txn_id = generate_txn_id()
        order_id = generate_order_id()

        sender = random.choice(USERS)
        merchant = random.choice(MERCHANTS)

        rows.append((
            txn_id,
            order_id,
            f"ACC-{random.randint(1000,9999)}",
            f"MERCH-{random.randint(1000,9999)}",
            sender,
            merchant,
            round(random.uniform(49, 4999), 2),
            random.choice(METHODS),
            random.choice(STATUSES),
            random_date()
        ))

    c.executemany("""
        INSERT INTO transactions (
            txn_id,
            order_id,
            sender_account,
            receiver_account,
            sender_email,
            merchant_email,
            amount,
            method,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    conn.close()

    print(f"✅ Inserted {len(rows)} transactions successfully!")

if __name__ == "__main__":
    main()
