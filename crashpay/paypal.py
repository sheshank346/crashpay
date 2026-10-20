import os

import requests
from dotenv import load_dotenv

load_dotenv()
BASE = "https://api-m.sandbox.paypal.com"


def get_token():
    r = requests.post(
        f"{BASE}/v1/oauth2/token",
        auth=(os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_CLIENT_SECRET"]),
        data={"grant_type": "client_credentials"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]

def create_order(amount="10.00"):
    r = requests.post(
        f"{BASE}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {get_token()}"},
        json={
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": "USD", "value": amount}}],
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

def capture_order(order_id):
    r = requests.post(
        f"{BASE}/v2/checkout/orders/{order_id}/capture",
        headers={"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json"},
        timeout=15,
    )
    return r.status_code, r.json()