import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ach_proto import BoundedLoadRing, ConsistentHashRing, ModuloRouter

NODES = [("a", 1.0), ("b", 1.0), ("c", 1.0), ("d", 0.5), ("e", 0.5)]


def _build(r):
    for n, w in NODES:
        r.add_node(n, w)
    return r


def test_routing_deterministic():
    r = _build(ConsistentHashRing())
    assert all(r.route(f"k{i}") == r.route(f"k{i}") for i in range(100))


def test_consistent_migration_is_small():
    keys = [f"k{i}" for i in range(20000)]
    r = _build(ConsistentHashRing(vnodes_per_unit=300))
    a0 = r.route_batch(keys)
    r.add_node("f", 1.0)
    a1 = r.route_batch(keys)
    moved = sum(x != y for x, y in zip(a0, a1)) / len(keys)
    # adding 1 of ~6 weighted units should move roughly its share, never a majority
    assert moved < 0.30, moved


def test_modulo_migration_is_catastrophic():
    keys = [f"k{i}" for i in range(20000)]
    r = _build(ModuloRouter())
    a0 = r.route_batch(keys)
    r.add_node("f", 1.0)
    a1 = r.route_batch(keys)
    moved = sum(x != y for x, y in zip(a0, a1)) / len(keys)
    assert moved > 0.70, moved          # modulo reshuffles almost everything


def test_bounded_load_respects_cap():
    import math
    keys = [f"k{i}" for i in range(20000)]
    r = _build(BoundedLoadRing(epsilon=0.25))
    _, load = r.assign(keys)
    cap = math.ceil(1.25 * len(keys) / len(r.nodes))
    assert max(load.values()) <= cap


def test_weighted_distribution_is_proportional():
    keys = [f"k{i}" for i in range(40000)]
    r = _build(ConsistentHashRing(vnodes_per_unit=400))
    load = Counter(r.route_batch(keys))
    # 'a' (w=1.0) should carry clearly more than 'd' (w=0.5)
    assert load["a"] > 1.4 * load["d"]
