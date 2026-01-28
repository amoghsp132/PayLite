import requests

BASE = "http://127.0.0.1:5000"

payload = {
    "cvv": "456",
    "card_no": "4222222222222222",
    "exp_date": "11/27",
    "upi_id": "paylite@upi",
    "bank_account_no": "MERCH10001"
}

s = requests.Session()

# Login first (merchant user)
s.post(f"{BASE}/login", data={
    "email": "merchant@email.com",
    "password": "merchantpassword"
})

r = s.post(f"{BASE}/api/account/verify", json=payload)
print(r.json())
