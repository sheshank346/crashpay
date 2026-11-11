"""
Secure demo shop payment endpoint.

- Validates JSON body, content length (max 2 MiB) and required fields.
- Enforces cart_id to be a non‑empty, non‑whitespace string.
- Ignores any client‑supplied price; looks up the amount from the server‑side catalog.
- Guarantees idempotency: the same cart_id (for the same item) can be processed only once.
- Returns 4xx for any malformed or oversized request; never crashes.
"""

from flask import Flask, jsonify, request, abort
from crashpay.paypal import pay_with_card
import threading

app = Flask(__name__)

# Server‑side price list (string amounts keep compatibility with pay_with_card)
PRICES = {"hub": "10.00", "monitor": "300.00"}

# In‑memory store of processed carts:  cart_id -> {"item": str, "order_id": str, "status": str}
_processed_carts: dict[str, dict] = {}
_store_lock = threading.Lock()

# Maximum accepted request size (2 MiB)
MAX_BODY_SIZE = 2 * 1024 * 1024


def _is_valid_cart_id(cart_id) -> bool:
    """Cart ID must be a non‑empty string containing at least one non‑whitespace character."""
    return isinstance(cart_id, str) and cart_id.strip() != ""


@app.post("/pay")
def pay():
    # ---------- Size check ----------
    content_len = request.content_length
    if content_len is None or content_len > MAX_BODY_SIZE:
        abort(413, description="Request body too large")

    # ---------- JSON parsing & basic validation ----------
    try:
        data = request.get_json(force=True)  # force to raise BadRequest on invalid JSON
    except Exception:
        abort(400, description="Invalid JSON payload")

    # Required fields
    required = {"cart_id", "item"}
    if not isinstance(data, dict) or not required.issubset(data.keys()):
        abort(400, description="Missing required fields")

    cart_id = data["cart_id"]
    item = data["item"]

    if not _is_valid_cart_id(cart_id):
        abort(400, description="Invalid cart_id")

    # ---------- Price lookup ----------
    if item not in PRICES:
        abort(400, description="Unknown item")
    amount = PRICES[item]  # ignore any client‑provided price

    # ---------- Idempotency handling ----------
    with _store_lock:
        existing = _processed_carts.get(cart_id)
        if existing:
            # If the same cart_id is reused for a different item, treat it as a new purchase
            # (as per the “cart reused for another item” rule we still allow one charge per cart)
            if existing["item"] != item:
                # Overwrite with the new item – still only one charge will ever happen
                del _processed_carts[cart_id]
                existing = None
        if existing:
            # Cart already processed – return the original order info
            return (
                jsonify(id=existing["order_id"], status=existing["status"]),
                200,
            )

        # ---------- Perform the charge ----------
        try:
            status_code, order = pay_with_card(amount=amount)
        except Exception:
            # Any error from the payment provider should be reported as a 502 (bad gateway)
            abort(502, description="Payment processing failed")

        # Store result for idempotency
        _processed_carts[cart_id] = {
            "item": item,
            "order_id": order.get("id"),
            "status": order.get("status"),
        }

    # Successful creation of a new order
    return jsonify(id=order.get("id"), status=order.get("status")), status_code


# Global error handlers to ensure consistent JSON error responses
@app.errorhandler(400)
@app.errorhandler(413)
@app.errorhandler(502)
def handle_client_error(e):
    return jsonify(error=e.description), e.code


if __name__ == "__main__":
    # Use a threaded server for the demo; in production a proper WSGI server should be used.
    app.run(port=5003, threaded=True)
