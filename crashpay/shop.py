import sys

from flask import Flask, jsonify, request

from crashpay.paypal import pay_with_card

PRICES = {"hub": "10.00", "monitor": "300.00"}


def create_app(vulnerable):
    """Demo shop for testing Crashpay. Deliberately buggy when vulnerable. Sandbox only."""
    app = Flask(__name__)

    @app.post("/pay")
    def pay():
        data = request.get_json()
        if data.get("item") not in PRICES:
            return jsonify(error="unknown item"), 400
        if vulnerable:
            amount, key = data["price"], None
        else:
            amount, key = PRICES[data["item"]], data["cart_id"]
        status, order = pay_with_card(amount=amount, request_id=key)
        return jsonify(id=order.get("id"), status=order.get("status")), status

    return app


if __name__ == "__main__":
    vulnerable = sys.argv[1] == "vulnerable"
    create_app(vulnerable).run(port=5001 if vulnerable else 5002)