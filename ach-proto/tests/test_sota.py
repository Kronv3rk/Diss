from ach_proto import AnchorHashRouter, MaglevRouter

NODES = [f"n{i}" for i in range(8)]


def _build(r):
    for n in NODES:
        r.add_node(n)
    return r


def test_maglev_deterministic_and_covers_nodes():
    r = _build(MaglevRouter(table_size=2003))
    keys = [f"k{i}" for i in range(5000)]
    a = r.route_batch(keys)
    assert set(a) <= set(NODES) and len(set(a)) == len(NODES)
    assert a == r.route_batch(keys)


def test_maglev_low_disruption_on_remove():
    r = _build(MaglevRouter(table_size=2003))
    keys = [f"k{i}" for i in range(20000)]
    a0 = r.route_batch(keys)
    r.remove_node("n3")
    a1 = r.route_batch(keys)
    moved = sum(x != y for x, y in zip(a0, a1)) / len(keys)
    assert moved < 0.30                       # far below modulo's ~7/8


def test_anchorhash_minimal_disruption():
    """AnchorHash's defining property: removing a node remaps ONLY its keys."""
    r = _build(AnchorHashRouter(capacity=64))
    keys = [f"k{i}" for i in range(20000)]
    a0 = r.route_batch(keys)
    r.remove_node("n3")
    a1 = r.route_batch(keys)
    for x, y in zip(a0, a1):
        if x == "n3":
            assert y != "n3"                  # n3's keys move elsewhere
        else:
            assert x == y                     # everyone else is untouched
