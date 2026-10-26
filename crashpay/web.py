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
    runs = max(1, min(int(data.get("runs", 1)), 10))
    fn, url = ATTACKS[data["attack"]], TARGETS[data["target"]]
    results = [fn(url) for _ in range(runs)]
    return jsonify(
        passed=sum(1 for r in results if r["defended"]),
        runs=runs,
        detail=results[-1]["detail"],
    )


if __name__ == "__main__":
    app.run(port=5000)