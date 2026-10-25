from crashpay.attacks import ATTACKS
from crashpay.targets import TARGETS


def run():
    rows = []
    for target, url in TARGETS.items():
        for attack, fn in ATTACKS.items():
            result = fn(url)
            rows.append((target, attack, result["detail"], result["defended"]))
    return rows


if __name__ == "__main__":
    for target, attack, detail, defended in run():
        status = "PASS" if defended else "FAIL"
        print(f"{status}  {target:<16} {attack:<24} {detail}")