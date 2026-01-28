# seed_inventory.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import Inventory, BaseInventory  # 👈 change filename
import os
import random

# ---------------- CONFIG ----------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "inventory.db")
ENGINE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(ENGINE_URL, future=True)
Session = sessionmaker(bind=engine)

# Ensure table exists
BaseInventory.metadata.create_all(engine)

# ---------------- SAMPLE DATA ----------------
products = [
    ("Rice 1kg", "G001", 60),
    ("Wheat Flour 1kg", "G002", 45),
    ("Sugar 1kg", "G003", 42),
    ("Salt 1kg", "G004", 20),
    ("Cooking Oil 1L", "G005", 160),
    ("Milk 1L", "D001", 56),
    ("Curd 500g", "D002", 35),
    ("Butter 100g", "D003", 55),
    ("Paneer 200g", "D004", 85),
    ("Cheese Slice", "D005", 90),
    ("Tea Powder 250g", "B001", 120),
    ("Coffee Powder 200g", "B002", 150),
    ("Soft Drink 750ml", "B003", 40),
    ("Soft Drink 2L", "B004", 95),
    ("Biscuits", "S001", 20),
    ("Potato Chips", "S002", 30),
    ("Namkeen", "S003", 50),
    ("Chocolate Bar", "S004", 25),
    ("Instant Noodles", "S005", 14),
    ("Bread", "BREAD01", 30),
    ("Eggs 6-pack", "E001", 42),
    ("Eggs 12-pack", "E002", 78),
    ("Tomato Ketchup", "C001", 65),
    ("Mayonnaise", "C002", 95),
    ("Jam 200g", "C003", 80),
    ("Toothpaste", "H001", 90),
    ("Soap", "H002", 35),
    ("Shampoo 100ml", "H003", 120),
    ("Detergent 1kg", "H004", 140),
    ("Handwash", "H005", 75),
]

# ---------------- INSERT ----------------
session = Session()

for name, sku, price in products:
    item = Inventory(
        name=name,
        sku=sku,
        price=price,
        qty=random.randint(10, 80)  # random stock
    )
    session.add(item)

session.commit()
session.close()

print("✅ Inventory seeded with 30 items")
