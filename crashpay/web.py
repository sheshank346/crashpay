from flask import Flask, jsonify, request

from crashpay.attacks import ATTACKS
from crashpay.targets import TARGETS

app = Flask(__name__)


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/plan")
def plan():
    return jsonify(targets=list(TARGETS), attacks=list(ATTACKS))


@app.post("/api/attack")
def attack():
    data = request.get_json()
    result = ATTACKS[data["attack"]](TARGETS[data["target"]])
    return jsonify(result)


if __name__ == "__main__":
    app.run(port=5000)