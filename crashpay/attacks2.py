import uuid
from concurrent.futures import ThreadPoolExecutor

from crashpay.attacks import buy, count_charges, post_status
from crashpay.paypal import get_order


def replay_returns_original(url):
    cart = str(uuid.uuid4())
    first = buy(url, "hub", "10.00", cart)
    second = buy(url, "hub", "10.00", cart)
    if first and first == second:
        return {"detail": "same order returned", "defended": True}
    if second is None:
        return {"detail": "repeat refused, no order returned", "defended": False}
    return {"detail": "a second order was created", "defended": False}


def cart_reuse_other_item(url):
    cart = str(uuid.uuid4())
    first = buy(url, "hub", "10.00", cart)
    second = buy(url, "monitor", "300.00", cart)
    charges = count_charges([first, second])
    return {"detail": f"{charges} charge(s) for one cart used for two items", "defended": charges == 1}


def cart_reuse_race(url):
    cart = str(uuid.uuid4())
    jobs = [("hub", "10.00"), ("monitor", "300.00")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda j: buy(url, j[0], j[1], cart), jobs))
    charges = count_charges(ids)
    return {"detail": f"{charges} charge(s) from 2 items sent at once", "defended": charges == 1}


def many_carts_at_once(url):
    carts = [str(uuid.uuid4()) for _ in range(3)]
    jobs = [c for c in carts for _ in range(4)]
    with ThreadPoolExecutor(max_workers=12) as pool:
        ids = list(pool.map(lambda c: buy(url, "hub", "10.00", c), jobs))
    charges = count_charges(ids)
    return {"detail": f"{charges} charge(s) from 12 requests on 3 carts", "defended": charges == 3}


PRICES_TO_TRY = ["0.02", "1.00", "150.00", "299.99", "300.01", "9999.00", "0.50", "100.00"]


def price_field_fuzz(url):
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda p: buy(url, "monitor", p, str(uuid.uuid4())), PRICES_TO_TRY))
    paid = [get_order(i)["purchase_units"][0]["amount"]["value"] for i in ids if i]
    wrong = [a for a in paid if a != "300.00"]
    return {"detail": f"{len(paid)} order(s) created, wrong amounts: {wrong}", "defended": not wrong}


def poisoned_cart(url):
    cart = str(uuid.uuid4())
    refused = post_status(url, {"item": "nope", "cart_id": cart})
    order = buy(url, "hub", "10.00", cart)
    charges = count_charges([order])
    ok = 400 <= refused < 500 and charges == 1
    return {"detail": f"bad request got {refused}, then the cart was charged {charges} time(s)", "defended": ok}


def oversized_body(url):
    body = {"item": "hub", "price": "10.00", "cart_id": str(uuid.uuid4()), "note": "x" * 2000000}
    code = post_status(url, body)
    return {"detail": f"status {code} for a 2 MB body", "defended": 400 <= code < 500}


EXTRA = {
    "replay returns original order": replay_returns_original,
    "cart reused for another item": cart_reuse_other_item,
    "cart reuse race (2 items)": cart_reuse_race,
    "3 carts x 4 requests": many_carts_at_once,
    "price field fuzz (8 values)": price_field_fuzz,
    "refused request poisons cart": poisoned_cart,
    "oversized body (2 MB)": oversized_body,
}