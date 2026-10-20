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