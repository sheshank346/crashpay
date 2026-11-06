CART = "fuzz-cart"

BODIES = [
    # not an object
    [],
    [1, 2, 3],
    "text",
    42,
    True,
    [{"item": "hub", "cart_id": CART}],
    # missing or empty fields
    {},
    {"item": "hub"},
    {"cart_id": CART},
    {"item": "", "cart_id": CART},
    {"item": "hub", "cart_id": ""},
    # wrong types for item
    {"item": None, "cart_id": CART},
    {"item": 5, "cart_id": CART},
    {"item": ["hub"], "cart_id": CART},
    {"item": {"name": "hub"}, "cart_id": CART},
    {"item": True, "cart_id": CART},
    # wrong types for cart_id
    {"item": "hub", "cart_id": None},
    {"item": "hub", "cart_id": ["x"]},
    {"item": "hub", "cart_id": {"a": 1}},
    # odd item strings
    {"item": "nope", "cart_id": CART},
    {"item": "HUB", "cart_id": CART},
    {"item": " hub", "cart_id": CART},
    {"item": "hub" * 5000, "cart_id": CART},
    {"item": "../../etc/passwd", "cart_id": CART},
    {"item": "<script>alert(1)</script>", "cart_id": CART},
    {"item": "hub'; DROP TABLE orders;--", "cart_id": CART},
    # odd cart ids with an unknown item
    {"item": "nope", "cart_id": "x" * 100000},
    {"item": "nope", "cart_id": chr(0x1F4B3) * 50},
    {"item": "nope", "cart_id": "a" + chr(0) + "b"},
    # extra fields
    {"item": "nope", "cart_id": CART, "price": "-5"},
    {"item": "nope", "cart_id": CART, "extra": {"deep": [[[[1]]]]}},
    # cart ids that are not usable strings
    {"item": "hub", "cart_id": True},
    {"item": "hub", "cart_id": 0},
    {"item": "hub", "cart_id": 1.5},
    {"item": "hub", "cart_id": "   "},
]