from crashpay.paypal import get_order


def was_charged(order):
    captures = order["purchase_units"][0].get("payments", {}).get("captures", [])
    return any(c["status"] == "COMPLETED" for c in captures)


def count_charges(order_ids):
    unique = set(order_ids)
    return sum(1 for i in unique if was_charged(get_order(i)))


def retry_after_timeout(pay):
    first = pay()
    second = pay()
    charges = count_charges([first["id"], second["id"]])
    return {"charges": charges, "defended": charges == 1}


ATTACKS = {"retry after a timeout": retry_after_timeout}