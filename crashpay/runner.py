from crashpay.attacks import ATTACKS
from crashpay.targets import TARGETS


def run():
    rows = []
    for target_name, make_pay in TARGETS.items():
        for attack_name, attack in ATTACKS.items():
            result = attack(make_pay())
            rows.append((target_name, attack_name, result["charges"], result["defended"]))
    return rows


if __name__ == "__main__":
    for target, attack, charges, defended in run():
        status = "PASS" if defended else "FAIL"
        print(f"{status}  {target:<18} {attack:<24} charges={charges}")