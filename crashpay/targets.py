import uuid

from crashpay.paypal import pay_with_card


def naive_pay():
    return pay_with_card()[1]


def make_safe_pay():
    key = str(uuid.uuid4())
    return lambda: pay_with_card(request_id=key)[1]


TARGETS = {
    "naive payment": lambda: naive_pay,
    "same-key payment": make_safe_pay,
}