"""Benchmark: key-migration fraction on membership change + load uniformity.

Compares naive modulo, classic consistent hashing, and bounded-load consistent
hashing on real BLAKE2b hashing of many keys with heterogeneous node capacities
(the dissertation's 3 strong / 4 medium / 3 weak profile).
"""
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ach_proto import (AnchorHashRouter, BoundedLoadRing, ConsistentHashRing,
                       MaglevRouter, ModuloRouter, gini)

CAPS = [("n%02d" % i, w) for i, w in
        enumerate([1.0, 1.0, 1.0, 0.55, 0.55, 0.55, 0.55, 0.25, 0.25, 0.25])]
WEIGHTS = dict(CAPS)


def build(router):
    for node, w in CAPS:
        router.add_node(node, w)
    return router


def assign_list(router, keys):
    if hasattr(router, "assign"):
        out, load = router.assign(keys)
        return [out[k] for k in keys], load
    lst = router.route_batch(keys)
    return lst, dict(Counter(lst))


def util_imbalance(load):
    u = [load.get(n, 0) / WEIGHTS[n] for n in WEIGHTS]
    mean = sum(u) / len(u)
    return max(u) / mean if mean else float("nan")


def migration(a0, a1):
    return sum(1 for x, y in zip(a0, a1) if x != y) / len(a0)


def evaluate(name, factory, keys):
    r = build(factory())
    t = time.perf_counter()
    a0, load = assign_list(r, keys)
    route_s = time.perf_counter() - t
    imb = util_imbalance(load)
    g = gini([load.get(n, 0) for n, _ in CAPS])

    r.add_node("n10", 1.0)
    a_add, _ = assign_list(r, keys)
    mig_add = migration(a0, a_add)

    r2 = build(factory())
    base, _ = assign_list(r2, keys)
    r2.remove_node("n04")            # drop a medium node
    a_rm, _ = assign_list(r2, keys)
    mig_rm = migration(base, a_rm)

    print(f"{name:<26} util_imbal={imb:6.3f}  gini={g:5.3f}  "
          f"mig_add={mig_add:6.2%}  mig_remove={mig_rm:6.2%}  ({route_s*1000:4.0f} ms/pass)")


def main():
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 80000
    keys = [f"key:{i}" for i in range(K)]
    print(f"== migration benchmark: {K:,} keys, {len(CAPS)} weighted nodes ==")
    print("(util_imbal=max/mean of load/capacity, 1.0=ideal; mig=fraction of keys that moved)\n")
    evaluate("Modulo hash(key)%N", ModuloRouter, keys)
    evaluate("Consistent hashing", lambda: ConsistentHashRing(vnodes_per_unit=200), keys)
    evaluate("Bounded-load CH (eps=0.25)", lambda: BoundedLoadRing(epsilon=0.25, vnodes_per_unit=200), keys)
    evaluate("Maglev", lambda: MaglevRouter(table_size=65537), keys)
    evaluate("AnchorHash", lambda: AnchorHashRouter(capacity=256), keys)


if __name__ == "__main__":
    main()
