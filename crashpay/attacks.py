import uuid
from concurrent.futures import ThreadPoolExecutor

import requests

from crashpay.paypal import get_order


def buy(url, item, price, cart_id):
    r = requests.post(
        f"{url}/pay",
        json={"item": item, "price": price, "cart_id": cart_id},
        timeout=40,
    )
    return r.json().get("id")


def was_charged(order):
    captures = order["purchase_units"][0].get("payments", {}).get("captures", [])
    return any(c["status"] == "COMPLETED" for c in captures)


def count_charges(order_ids):
    ids = {i for i in order_ids if i}
    return sum(1 for i in ids if was_charged(get_order(i)))


def retry_after_timeout(url):
    cart = str(uuid.uuid4())
    charges = count_charges([buy(url, "hub", "10.00", cart) for _ in range(2)])
    return {"detail": f"{charges} charge(s)", "defended": charges == 1}


def double_submit(url):
    cart = str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: buy(url, "hub", "10.00", cart), range(2)))
    charges = count_charges(results)
    return {"detail": f"{charges} charge(s)", "defended": charges == 1}


def price_tampering(url):
    order_id = buy(url, "monitor", "0.01", str(uuid.uuid4()))
    if not order_id:
        return {"detail": "request refused", "defended": True}
    order = get_order(order_id)
    paid = order["purchase_units"][0]["amount"]["value"]
    return {"detail": f"monitor sold for {paid}", "defended": paid == "300.00"}


def malformed_input(url):
    bodies = [
        {},
        {"item": "hub"},
        {"cart_id": str(uuid.uuid4())},
        {"item": "nope", "cart_id": str(uuid.uuid4())},
    ]
    codes = [requests.post(f"{url}/pay", json=b, timeout=40).status_code for b in bodies]
    broken = requests.post(
        f"{url}/pay",
        data="{not json",
        headers={"Content-Type": "application/json"},
        timeout=40,
    )
    codes.append(broken.status_code)
    return {"detail": f"status codes {codes}", "defended": all(400 <= c < 500 for c in codes)}


ATTACKS = {
    "retry after a timeout": retry_after_timeout,
    "double submit": double_submit,
    "price tampering": price_tampering,
    "malformed input": malformed_input,
}