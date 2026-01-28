import requests

BASE = "http://127.0.0.1:5000"

accounts = [
    {
        "fname": "Amogh",
        "lname": "User",
        "cvv": "123",
        "card_no": "4111111111111111",
        "exp_date": "12/26",
        "upi_id": "amogh@upi",
        "bank_account_no": "ACC10001",
        "balance": 5000
    },
    {
        "fname": "Paylite",
        "lname": "Merchant",
        "cvv": "456",
        "card_no": "4222222222222222",
        "exp_date": "11/27",
        "upi_id": "paylite@upi",
        "bank_account_no": "MERCH10001",
        "balance": 0
    }
]

for acc in accounts:
    r = requests.post(f"{BASE}/api/account/create", json=acc)
    print(r.json())
