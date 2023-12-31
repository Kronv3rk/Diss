"""Real consistent-hash ring with capacity-weighted virtual nodes, plus a
Google-style bounded-load variant and a naive modulo router for comparison."""
from __future__ import annotations

import bisect
import hashlib
import math


def _h64(data: str) -> int:
    """64-bit hash via BLAKE2b (stdlib, no external deps)."""
    return int.from_bytes(hashlib.blake2b(data.encode(), digest_size=8).digest(), "big")


def gini(counts) -> float:
    """Gini coefficient of a load vector (0 = perfectly even)."""
    x = sorted(float(c) for c in counts)
    n = len(x)
    s = sum(x)
    if n == 0 or s == 0:
        return 0.0
    cum = sum((i + 1) * xi for i, xi in enumerate(x))
    return (2.0 * cum) / (n * s) - (n + 1.0) / n


class ModuloRouter:
    """Naive hash(key) % N - the strawman: tiny imbalance, catastrophic migration."""

    def __init__(self):
        self._nodes: list[str] = []

    def add_node(self, node: str, weight: float = 1.0) -> None:
        self._nodes.append(node)

    def remove_node(self, node: str) -> None:
        self._nodes.remove(node)

    @property
    def nodes(self) -> list[str]:
        return list(self._nodes)

    def route(self, key: str) -> str:
        return self._nodes[_h64(key) % len(self._nodes)]

    def route_batch(self, keys):
        nodes, n = self._nodes, len(self._nodes)
        return [nodes[_h64(k) % n] for k in keys]


class ConsistentHashRing:
    """Classic consistent hashing with capacity-weighted virtual nodes."""

    def __init__(self, vnodes_per_unit: int = 200):
        self.vnodes_per_unit = vnodes_per_unit
        self._ring: dict[int, str] = {}
        self._sorted: list[int] = []
        self._weight: dict[str, float] = {}

    def _vcount(self, weight: float) -> int:
        return max(1, int(round(self.vnodes_per_unit * weight)))

    def add_node(self, node: str, weight: float = 1.0) -> None:
        self._weight[node] = weight
        for i in range(self._vcount(weight)):
            self._ring[_h64(f"{node}#{i}")] = node
        self._sorted = sorted(self._ring)

    def remove_node(self, node: str) -> None:
        w = self._weight.pop(node)
        for i in range(self._vcount(w)):
            self._ring.pop(_h64(f"{node}#{i}"), None)
        self._sorted = sorted(self._ring)

    @property
    def nodes(self) -> list[str]:
        return list(self._weight)

    def route(self, key: str) -> str:
        s = self._sorted
        idx = bisect.bisect(s, _h64(key))
        if idx == len(s):
            idx = 0
        return self._ring[s[idx]]

    def route_batch(self, keys):
        return [self.route(k) for k in keys]


class BoundedLoadRing(ConsistentHashRing):
    """Consistent hashing with bounded loads (Mirrokni et al., Google 2017).

    Each key is placed on its consistent-hash node unless that node is already
    at capacity floor((1+eps) * mean_load); then it overflows to the next node
    on the ring with spare capacity. Guarantees max load <= (1+eps) * mean
    while keeping migration near consistent-hashing levels.
    """

    def __init__(self, epsilon: float = 0.25, vnodes_per_unit: int = 200):
        super().__init__(vnodes_per_unit=vnodes_per_unit)
        self.epsilon = float(epsilon)

    def assign(self, keys) -> tuple[dict, dict]:
        s = self._sorted
        m = len(s)
        nodes = self.nodes
        n = len(nodes)
        cap = math.ceil((1.0 + self.epsilon) * len(keys) / n)
        load = dict.fromkeys(nodes, 0)
        out = {}
        for k in keys:
            idx = bisect.bisect(s, _h64(k))
            if idx == m:
                idx = 0
            placed = None
            for step in range(m):
                node = self._ring[s[(idx + step) % m]]
                if load[node] < cap:
                    placed = node
                    break
            if placed is None:                      # all full (shouldn't happen)
                placed = self._ring[s[idx]]
            out[k] = placed
            load[placed] += 1
        return out, load
