import re
import sys
from threading import Lock

from flask import Flask, jsonify, request

from crashpay.paypal import pay_with_card

PRICES = {"hub": "10.00", "monitor": "300.00"}


def create_app(vulnerable):
    """Demo shop for testing Crashpay. Deliberately buggy when vulnerable. Sandbox only."""
    app = Flask(__name__)
    carts = {}
    guard = Lock()

    def pay_vulnerable():
        data = request.get_json()
        if data.get("item") not in PRICES:
            return jsonify(error="unknown item"), 400
        status, order = pay_with_card(amount=data["price"])
        return jsonify(id=order.get("id"), status=order.get("status")), status

    def pay_fixed():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get("item"), str) or data["item"] not in PRICES:
            return jsonify(error="invalid item"), 400
        cart_id = data.get("cart_id")
        if not isinstance(cart_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", cart_id):
            return jsonify(error="cart_id required"), 400
        with guard:
            cart = carts.setdefault(cart_id, {"lock": Lock(), "reply": None})
        with cart["lock"]:
            if cart["reply"] is None:
                amount = PRICES[data["item"]]
                status, order = pay_with_card(amount=amount, request_id=cart_id)
                if status >= 400:
                    return jsonify(error="payment failed"), status
                cart["reply"] = (order.get("id"), order.get("status"), status)
            order_id, order_status, status = cart["reply"]
        return jsonify(id=order_id, status=order_status), status

    handler = pay_vulnerable if vulnerable else pay_fixed
    if not vulnerable:
        app.config["MAX_CONTENT_LENGTH"] = 100 * 1024
    app.add_url_rule("/pay", view_func=handler, methods=["POST"])
    return app


if __name__ == "__main__":
    vulnerable = sys.argv[1] == "vulnerable"
    create_app(vulnerable).run(port=5001 if vulnerable else 5002)