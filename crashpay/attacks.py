from crashpay.paypal import get_order


def count_charges(order_ids):
    unique = set(order_ids)
    return sum(1 for i in unique if get_order(i)["status"] == "COMPLETED")


def retry_after_timeout(pay):
    first = pay()
    second = pay()
    charges = count_charges([first["id"], second["id"]])
    return {"charges": charges, "defended": charges == 1}


ATTACKS = {"retry after a timeout": retry_after_timeout}