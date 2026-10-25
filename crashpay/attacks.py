import uuid

import requests

from crashpay.paypal import get_order


def buy(url, item, price, cart_id):
    r = requests.post(
        f"{url}/pay",
        json={"item": item, "price": price, "cart_id": cart_id},
        timeout=40,
    )
    return r.json()["id"]


def was_charged(order):
    captures = order["purchase_units"][0].get("payments", {}).get("captures", [])
    return any(c["status"] == "COMPLETED" for c in captures)


def retry_after_timeout(url):
    cart = str(uuid.uuid4())
    ids = {buy(url, "hub", "10.00", cart) for _ in range(2)}
    charges = sum(1 for i in ids if was_charged(get_order(i)))
    return {"detail": f"{charges} charge(s)", "defended": charges == 1}


def price_tampering(url):
    order = get_order(buy(url, "monitor", "0.01", str(uuid.uuid4())))
    paid = order["purchase_units"][0]["amount"]["value"]
    return {"detail": f"monitor sold for {paid}", "defended": paid == "300.00"}


ATTACKS = {
    "retry after a timeout": retry_after_timeout,
    "price tampering": price_tampering,
}