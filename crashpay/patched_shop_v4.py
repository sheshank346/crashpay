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
    """Return the catalog price for a given item or abort with 400."""
    try:
        return PRICES[item]
    except KeyError:
        abort(400, description=f"Unknown item '{item}'.")


def _expect_dict(payload):
    """Ensure the JSON payload is a dict; abort with 400 otherwise."""
    if not isinstance(payload, dict):
        abort(400, description="JSON payload must be an object.")
    return payload


def _require_str_field(data, field_name, allow_blank=False):
    """
    Ensure a field exists and is a **string** (no int/float/bool).  If
    ``allow_blank`` is False, the string must contain at least one
    non‑whitespace character.
    """
    value = data.get(field_name)
    if value is None:
        abort(400, description=f"Missing field: {field_name}")

    # Reject anything that is not a plain str (bool is subclass of int, so check explicitly)
    if not isinstance(value, str):
        abort(400, description=f"Field '{field_name}' must be a non‑empty string.")

    if not allow_blank and not value.strip():
        abort(400, description=f"Field '{field_name}' cannot be empty or whitespace only.")

    return value  # already a string


@app.post("/pay")
def pay():
    # Force JSON parsing but be tolerant of empty bodies.
    raw = request.get_json(silent=True)
    if raw is None:
        abort(400, description="Invalid or missing JSON payload.")

    data = _expect_dict(raw)

    # Required fields – cart_id must be a non‑blank string
    item = _require_str_field(data, "item")
    cart_id = _require_str_field(data, "cart_id", allow_blank=False)

    # Idempotency check – reject duplicates
    with store_lock:
        if cart_id in processed_carts:
            return jsonify(error="Duplicate cart_id"), 409  # Conflict
        processed_carts.add(cart_id)

    # Server‑side price determination (ignore any client‑supplied price)
    try:
        price = get_price(item)
    except Exception as e:
        # Clean up the cart_id entry on failure and report the error
        with store_lock:
            processed_carts.discard(cart_id)
        abort(400, description=str(e))

    # Convert Decimal to the string format expected by the PayPal SDK
    amount_str = f"{price:.2f}"

    # Perform the payment – any unexpected exception should be caught
    try:
        status, order = pay_with_card(amount=amount_str)
    except Exception:
        # Roll back idempotency entry on internal error
        with store_lock:
            processed_carts.discard(cart_id)
        abort(500, description="Payment processing failed.")  # 5xx for internal errors

    # If PayPal returned an error we roll back the cart_id
    if status >= 400:
        with store_lock:
            processed_carts.discard(cart_id)

    return jsonify(id=order.get("id"), status=order.get("status")), status


# Global error handler to guarantee a JSON 4xx/5xx response instead of an HTML page
@app.errorhandler(400)
@app.errorhandler(409)
@app.errorhandler(500)
def _json_error(error):
    response = jsonify(error=getattr(error, "description", str(error)))
    response.status_code = getattr(error, "code", 500)
    return response


if __name__ == "__main__":
    # Debug mode is off for security; bind to localhost only.
    app.run(host="127.0.0.1", port=5003, debug=False)
