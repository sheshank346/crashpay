from flask import Flask, jsonify, request

from crashpay.paypal import pay_with_card

PRICES = {"hub": "10.00", "monitor": "300.00"}

app = Flask(__name__)


@app.post("/pay")
def pay():
    data = request.get_json()
    status, order = pay_with_card(amount=data["price"])
    return jsonify(id=order.get("id"), status=order.get("status")), status


if __name__ == "__main__":
    app.run(port=5003)