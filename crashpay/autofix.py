
import re
import subprocess
import sys
import time

import requests

from crashpay.attacks import ATTACKS as BASE
from crashpay.attacks2 import EXTRA
from crashpay.rules import RULES

ATTACKS = {**BASE, **EXTRA}
ALLOWED = {"flask", "werkzeug", "decimal", "threading", "uuid", "re", "json", "time", "crashpay"}


def rule_for(name):
    for key, rule in RULES.items():
        if name.startswith(key):
            return rule
    return "The shop must defend this attack."


def run_attacks(url):
    failures = []
    for name, fn in ATTACKS.items():
        try:
            result = fn(url)
        except Exception as e:
            result = {"detail": f"attack error: {type(e).__name__}", "defended": False}
        if not result["defended"]:
            failures.append((name, result["detail"]))
    return failures


def describe(failures):
    lines = [f"- {name}: {detail}. Rule: {rule_for(name)}" for name, detail in failures]
    return "\n".join(lines)


def bad_imports(code):
    found = re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", code, re.M)
    return sorted({m for m in found if m not in ALLOWED})

def free_port():
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_shop(path, port):
    module = path.replace("\\", "/").rsplit("/", 1)[-1][:-3]
    code = f"from crashpay.{module} import app; app.run(port={port})"
    proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(30):
        time.sleep(0.5)
        try:
            requests.get(url, timeout=1)
            return proc, url
        except requests.RequestException:
            continue
    proc.terminate()
    return None, url


def loop(start_path, rounds=4, auto=False):
    from crashpay.fixer import fix_shop
    log = []
    path = start_path
    url = None
    proc = None
    port = free_port()
    proc, url = start_shop(path, port)
    if proc is None:
        print("could not start", path)
        return
    failures = run_attacks(url)
    proc.terminate()
    best = len(failures)
    print(f"round 0 ({path}): {len(ATTACKS) - len(failures)} of {len(ATTACKS)} defended")
    log.append(f"round 0: {path}, failures {[f[0] for f in failures]}")
    for n in range(1, rounds + 1):
        if not failures:
            print("all attacks defended")
            break
        out = f"crashpay/auto_v{n}.py"
        ok = fix_shop("autofix", describe(failures), path=path, out=out)
        if not ok:
            print(f"round {n}: the model returned no code block")
            break
        code = open(out, encoding="utf-8").read()
        extra = bad_imports(code)
        if extra:
            print(f"round {n}: patch imports {extra}, refusing to run it")
            break
        if not auto:
            if input(f"round {n}: patch saved to {out}. Read it, then type y to run it: ").strip().lower() != "y":
                print("stopped")
                break
        port = free_port()
        proc, url = start_shop(out, port)
        if proc is None:
            print(f"round {n}: the patch did not start")
            break
        failures = run_attacks(url)
        proc.terminate()
        defended = len(ATTACKS) - len(failures)
        print(f"round {n} ({out}): {defended} of {len(ATTACKS)} defended")
        log.append(f"round {n}: {out}, failures {[f[0] for f in failures]}")
        path = out
        if len(failures) >= best:
            print("no improvement, stopping")
            break
        best = len(failures)
    with open("autofix_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    loop(args[0], auto="--auto" in args)