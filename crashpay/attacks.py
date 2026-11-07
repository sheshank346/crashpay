import uuid
from concurrent.futures import ThreadPoolExecutor

import requests

from crashpay.cases import BODIES
from crashpay.paypal import get_order


def buy(url, item, price, cart_id):
    r = requests.post(
        f"{url}/pay",
        json={"item": item, "price": price, "cart_id": cart_id},
        timeout=40,
    )
    try:
        return r.json().get("id")
    except ValueError:
        return None


def post_status(url, body):
    try:
        return requests.post(f"{url}/pay", json=body, timeout=40).status_code
    except requests.RequestException:
        return 0


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


def simultaneous(url, n):
    cart = str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=n) as pool:
        results = list(pool.map(lambda _: buy(url, "hub", "10.00", cart), range(n)))
    charges = count_charges(results)
    return {"detail": f"{charges} charge(s) from {n} requests", "defended": charges == 1}


def double_submit(url):
    return simultaneous(url, 2)


def burst_submit(url):
    return simultaneous(url, 8)


def price_tampering(url):
    order_id = buy(url, "monitor", "0.01", str(uuid.uuid4()))
    if not order_id:
        return {"detail": "request refused", "defended": True}
    order = get_order(order_id)
    paid = order["purchase_units"][0]["amount"]["value"]
    return {"detail": f"monitor sold for {paid}", "defended": paid == "300.00"}


def status_codes(url, bodies):
    codes = [post_status(url, b) for b in bodies]
    return {"detail": f"status codes {codes}", "defended": all(400 <= c < 500 for c in codes)}


def malformed_input(url):
    bodies = [
        {},
        {"item": "hub"},
        {"cart_id": str(uuid.uuid4())},
        {"item": "nope", "cart_id": str(uuid.uuid4())},
    ]
    result = status_codes(url, bodies)
    broken = requests.post(
        f"{url}/pay",
        data="{not json",
        headers={"Content-Type": "application/json"},
        timeout=40,
    )
    codes = result["detail"] + f" + {broken.status_code}"
    return {"detail": codes, "defended": result["defended"] and 400 <= broken.status_code < 500}


def type_confusion(url):
    cart = str(uuid.uuid4())
    bodies = [
        {"item": ["hub"], "cart_id": cart},
        {"item": {"a": 1}, "cart_id": cart},
        {"item": None, "cart_id": cart},
        {"item": "hub", "cart_id": ["x"]},
        [1, 2, 3],
    ]
    return status_codes(url, bodies)


def fuzz_input(url):
    codes = [post_status(url, b) for b in BODIES]
    refused = sum(1 for c in codes if 400 <= c < 500)
    crashed = sum(1 for c in codes if c == 0 or c >= 500)
    accepted = len(codes) - refused - crashed
    detail = f"{refused} refused, {crashed} crashed, {accepted} accepted of {len(codes)}"
    return {"detail": detail, "defended": refused == len(codes)}


def legit_purchases(url):
    carts = [str(uuid.uuid4()) for _ in range(6)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        ids = list(pool.map(lambda c: buy(url, "hub", "10.00", c), carts))
    charges = count_charges(ids)
    return {"detail": f"{charges} of 6 legitimate purchases charged", "defended": charges == 6}


ODD_CART_IDS = [
    "line\nbreak",
    "carriage\r\nreturn",
    "tab\there",
    " leading space",
    "trailing space ",
    "emoji-" + chr(0x1F4B3),
    "rtl-" + chr(0x202E),
    "long-" + "x" * 300,
]


def odd_cart_ids(url):
    suffix = uuid.uuid4().hex[:8]
    bodies = [{"item": "hub", "price": "10.00", "cart_id": f"{c}-{suffix}"} for c in ODD_CART_IDS]
    codes = [post_status(url, b) for b in bodies]
    crashed = sum(1 for c in codes if c == 0 or c >= 500)
    return {"detail": f"status codes {codes}", "defended": crashed == 0}


ATTACKS = {
    "retry after a timeout": retry_after_timeout,
    "double submit": double_submit,
    "burst submit (8)": burst_submit,
    "price tampering": price_tampering,
    "malformed input": malformed_input,
    "type confusion": type_confusion,
    f"fuzz ({len(BODIES)} bad bodies)": fuzz_input,
    "legit purchases (control)": legit_purchases,
    "odd cart ids (valid item)": odd_cart_ids,
}