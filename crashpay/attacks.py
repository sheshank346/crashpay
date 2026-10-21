from crashpay.paypal import get_order


def count_charges(order_ids):
    unique = set(order_ids)
    return sum(1 for i in unique if get_order(i)["status"] == "COMPLETED")


def retry_without_key(pay):
    first = pay()
    second = pay()
    charges = count_charges([first["id"], second["id"]])
    return {
        "name": "retry without idempotency key",
        "charges": charges,
        "defended": charges == 1,
    }