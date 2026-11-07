import json
import os
import sys
import uuid

from crashpay.attacks import buy, count_charges
from crashpay.targets import TARGETS

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "..", "restart_state.json")

phase, shop = sys.argv[1], sys.argv[2]
url = TARGETS[shop]

if phase == "replay":
    cart = str(uuid.uuid4())
    first = buy(url, "hub", "10.00", cart)
    second = buy(url, "hub", "10.00", cart)
    print("first:", first, "| second:", second, "| same order:", bool(first) and first == second)
elif phase == "buy":
    cart = str(uuid.uuid4())
    first = buy(url, "hub", "10.00", cart)
    with open(STATE, "w") as f:
        json.dump({"cart": cart, "first": first}, f)
    print("bought:", first)
elif phase == "again":
    with open(STATE) as f:
        state = json.load(f)
    second = buy(url, "hub", "10.00", state["cart"])
    charges = count_charges([state["first"], second])
    print("second reply:", second, "| charges:", charges, "| defended:", charges == 1)