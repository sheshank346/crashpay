import collections
import sys

from crashpay.attacks import ATTACKS
from crashpay.targets import TARGETS

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
