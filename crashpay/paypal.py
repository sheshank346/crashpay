import os
import uuid

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

def create_setup_token():
    r = requests.post(
        f"{BASE}/v3/vault/setup-tokens",
        headers={
            "Authorization": f"Bearer {get_token()}",
            "PayPal-Request-Id": str(uuid.uuid4()),
        },
        json={
            "payment_source": {
                "paypal": {
                    "usage_type": "MERCHANT",
                    "usage_pattern": "IMMEDIATE",
                    "customer_type": "CONSUMER",
                    "experience_context": {
                        "return_url": "https://example.com/return",
                        "cancel_url": "https://example.com/cancel",
                    },
                }
            }
        },
        timeout=15,
    )
    return r.status_code, r.json()

def pay_with_card(number="4012888888881881", amount="10.00", request_id=None):
    r = requests.post(
        f"{BASE}/v2/checkout/orders",
        headers={
            "Authorization": f"Bearer {get_token()}",        
            "PayPal-Request-Id": request_id or str(uuid.uuid4()),
        },
        json={
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": "USD", "value": amount}}],
            "payment_source": {
                "card": {
                    "number": number,
                    "expiry": "2030-12",
                    "security_code": "123",
                    "name": "Test Buyer",
                    "billing_address": {
                        "address_line_1": "2211 N First St",
                        "admin_area_2": "San Jose",
                        "admin_area_1": "CA",
                        "postal_code": "95131",
                        "country_code": "US",
                    },
                }
            },
        },
        timeout=15,
    )
    return r.status_code, r.json()

def get_order(order_id):
    r = requests.get(
        f"{BASE}/v2/checkout/orders/{order_id}",
        headers={"Authorization": f"Bearer {get_token()}"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()