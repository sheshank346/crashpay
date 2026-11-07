import collections
import sys

from crashpay.attacks import ATTACKS as BASE
from crashpay.attacks2 import EXTRA
from crashpay.targets import TARGETS

ATTACKS = {**BASE, **EXTRA}

shop, attack, runs = sys.argv[1], sys.argv[2], int(sys.argv[3])
counts = collections.Counter()
for _ in range(runs):
    try:
        result = ATTACKS[attack](TARGETS[shop])
        counts[(result["detail"], result["defended"])] += 1
    except Exception as e:
        counts[("error: " + type(e).__name__, False)] += 1
for outcome, n in counts.items():
    print(n, outcome)
