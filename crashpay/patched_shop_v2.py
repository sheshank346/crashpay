# shop.py
from flask import Flask, jsonify, request, abort
from decimal import Decimal
from threading import Lock

# Simulated PayPal client (replace with real implementation)
from crashpay.paypal import pay_with_card

# Fixed catalogue – values stored as Decimal for safe arithmetic
PRICES = {
    "hub": Decimal("10.00"),
    "monitor": Decimal("300.00"),
}

app = Flask(__name__)

# In‑memory store for idempotency (for demo only)
processed_carts = set()
store_lock = Lock()


def get_price(item: str) -> Decimal:
    """Return the catalog price for a given item or raise 400."""
    try:
        return PRICES[item]
    except KeyError:
        abort(400, description=f"Unknown item '{item}'.")


def _expect_dict(payload):
    """Ensure the JSON payload is a dict; abort with 400 otherwise."""
    if not isinstance(payload, dict):
        abort(400, description="JSON payload must be an object.")
    return payload


def _require_str_field(data, field_name):
    """Ensure a field exists and is a string (or other hashable scalar)."""
    value = data.get(field_name)
    if value is None:
        abort(400, description=f"Missing field: {field_name}")
    if not isinstance(value, (str, int)):
        # Accept ints for convenience but reject complex types like list/dict.
        abort(400, description=f"Field '{field_name}' must be a string or integer.")
    return str(value)


@app.post("/pay")
def pay():
    # Force JSON parsing but be tolerant of empty bodies.
    raw = request.get_json(silent=True)
    if raw is None:
        abort(400, description="Invalid or missing JSON payload.")

    data = _expect_dict(raw)

    # Required fields
    item = _require_str_field(data, "item")
    cart_id = _require_str_field(data, "cart_id")

    # Idempotency check – reject or return previous result
    with store_lock:
        if cart_id in processed_carts:
            # In a real system you'd return the original order info.
            return jsonify(error="Duplicate cart_id"), 409  # Conflict
        # Mark as processed *before* charging to avoid race conditions
        processed_carts.add(cart_id)

    # Server‑side price determination (ignore any client‑supplied price)
    try:
        price = get_price(item)
    except Exception as e:
        # Clean up the cart_id entry on failure
        with store_lock:
            processed_carts.discard(cart_id)
        abort(400, description=str(e))

    # Convert Decimal to string as required by PayPal SDK
    amount_str = f"{price:.2f}"

    # Perform the payment
    status, order = pay_with_card(amount=amount_str)

    # If PayPal returned an error we should also roll back the cart_id
    if status >= 400:
        with store_lock:
            processed_carts.discard(cart_id)

    return jsonify(id=order.get("id"), status=order.get("status")), status


if __name__ == "__main__":
    # Debug mode is off for security; bind to localhost only.
    app.run(host="127.0.0.1", port=5003, debug=False)
