"""
Secure demo shop payment endpoint.

- Strictly validates JSON body, content length (max 2 MiB) and required fields.
- Enforces cart_id to be a non‑empty, non‑whitespace string.
- Enforces item to be a non‑empty string.
- Ignores any client‑supplied price; looks up the amount from the server‑side catalog.
- Guarantees idempotency: the same cart_id (for the same item) can be processed only once.
  Re‑using a cart_id for a different item is rejected with 400.
- Returns 4xx for any malformed, oversized or type‑confused request; never crashes.
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
MAX_BODY_SIZE = 2 * 1024 * 1024  # 2 MiB


def _is_valid_cart_id(cart_id) -> bool:
    """Cart ID must be a non‑empty string containing at least one non‑whitespace character."""
    return isinstance(cart_id, str) and cart_id.strip() != ""


def _is_valid_item(item) -> bool:
    """Item must be a non‑empty string."""
    return isinstance(item, str) and item != ""


@app.post("/pay")
def pay():
    # --------------------------------------------------------------------- #
    # 1️⃣  Enforce size limit – read the raw body first.
    # --------------------------------------------------------------------- #
    raw_body = request.get_data(cache=True)  # cache=True lets us parse JSON later
    if len(raw_body) > MAX_BODY_SIZE:
        abort(413, description="Request body too large")

    # --------------------------------------------------------------------- #
    # 2️⃣  Parse JSON and validate basic structure.
    # --------------------------------------------------------------------- #
    try:
        data = request.get_json(force=False)  # raise BadRequest on invalid JSON
    except Exception:
        abort(400, description="Invalid JSON payload")

    if not isinstance(data, dict):
        abort(400, description="JSON payload must be an object")

    required = {"cart_id", "item"}
    if not required.issubset(data.keys()):
        abort(400, description="Missing required fields")

    cart_id = data["cart_id"]
    item = data["item"]

    # --------------------------------------------------------------------- #
    # 3️⃣  Strict type validation (no lists, objects, null, etc.).
    # --------------------------------------------------------------------- #
    if not _is_valid_cart_id(cart_id):
        abort(400, description="Invalid cart_id")
    if not _is_valid_item(item):
        abort(400, description="Invalid item")

    # --------------------------------------------------------------------- #
    # 4️⃣  Business validation – known item only.
    # --------------------------------------------------------------------- #
    if item not in PRICES:
        abort(400, description="Unknown item")
    amount = PRICES[item]  # ignore any client‑provided price

    # --------------------------------------------------------------------- #
    # 5️⃣  Idempotency & cart‑reuse handling.
    # --------------------------------------------------------------------- #
    with _store_lock:
        existing = _processed_carts.get(cart_id)

        if existing:
            # Same cart_id used again.
            if existing["item"] != item:
                # Rule: a cart reused for a different item must be rejected.
                abort(400, description="Cart ID already used for a different item")
            # Idempotent repeat – return the original order information.
            return jsonify(id=existing["order_id"], status=existing["status"]), 200

        # ----------------------------------------------------------------- #
        # 6️⃣  Perform the charge (only once per cart_id).
        # ----------------------------------------------------------------- #
        try:
            status_code, order = pay_with_card(amount=amount)
        except Exception as exc:
            # Propagate provider errors as 502.
            abort(502, description="Payment processing failed")

        # Store for future idempotent calls.
        _processed_carts[cart_id] = {
            "item": item,
            "order_id": order.get("id"),
            "status": order.get("status"),
        }

    # --------------------------------------------------------------------- #
    # 7️⃣  Return the provider response.
    # --------------------------------------------------------------------- #
    return jsonify(id=order.get("id"), status=order.get("status")), status_code


# --------------------------------------------------------------------- #
# Consistent JSON error responses for the relevant client‑error codes.
# --------------------------------------------------------------------- #
@app.errorhandler(400)
@app.errorhandler(413)
@app.errorhandler(502)
def handle_client_error(e):
    return jsonify(error=e.description), e.code


# Optional: catch‑all for unexpected server errors – still returns JSON.
@app.errorhandler(500)
def handle_unexpected_error(e):
    return jsonify(error="Internal server error"), 500


if __name__ == "__main__":
    # Use a threaded server for the demo; in production a proper WSGI server should be used.
    app.run(port=5003, threaded=True)
