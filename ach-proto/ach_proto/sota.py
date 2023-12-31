"""SOTA placement schemes for the migration benchmark: Maglev and AnchorHash.

Both expose the same add_node / remove_node / route interface as the rings, so
they slot directly into bench/migration_bench.py.
"""
from __future__ import annotations

from .ring import _h64


class MaglevRouter:
    """Maglev consistent hashing (Eisenbud et al., Google NSDI'16).

    Builds a lookup table of size M (prime) via per-node permutations; route =
    table[hash(key) % M]. Rebuilt on membership change."""

    name = "Maglev"

    def __init__(self, table_size: int = 65537):
        self.M = table_size
        self._nodes: list[str] = []
        self._table: list[str] = []

    def _perm(self, node: str):
        offset = _h64("offset:" + node) % self.M
        skip = _h64("skip:" + node) % (self.M - 1) + 1
        return offset, skip

    def _build(self) -> None:
        M, nodes = self.M, self._nodes
        N = len(nodes)
        if N == 0:
            self._table = []
            return
        perm = [self._perm(n) for n in nodes]
        nxt = [0] * N
        entry = [-1] * M
        filled = 0
        while True:
            for i in range(N):
                off, skip = perm[i]
                c = (off + nxt[i] * skip) % M
                while entry[c] != -1:
                    nxt[i] += 1
                    c = (off + nxt[i] * skip) % M
                entry[c] = i
                nxt[i] += 1
                filled += 1
                if filled == M:
                    self._table = [nodes[e] for e in entry]
                    return

    def add_node(self, node: str, weight: float = 1.0) -> None:
        self._nodes.append(node)
        self._build()

    def remove_node(self, node: str) -> None:
        self._nodes.remove(node)
        self._build()

    @property
    def nodes(self) -> list[str]:
        return list(self._nodes)

    def route(self, key: str) -> str:
        return self._table[_h64(key) % self.M]

    def route_batch(self, keys):
        t, M = self._table, self.M
        return [t[_h64(k) % M] for k in keys]


class AnchorHashRouter:
    """AnchorHash (Mendelson, Cidon, Keslassy - IEEE/ACM ToN 2020).

    Minimal-disruption consistent hashing: removing a node remaps only that
    node's keys. `capacity` is the anchor size (max buckets ever)."""

    name = "AnchorHash"

    def __init__(self, capacity: int = 256):
        self.a = capacity
        self.A = [0] * self.a
        self.K = list(range(self.a))
        self.W = list(range(self.a))
        self.L = list(range(self.a))
        self.R: list[int] = []
        self.N = self.a
        for b in range(self.a - 1, -1, -1):      # start empty (N=0)
            self._remove_bucket(b)
        self._name_of: dict[int, str] = {}
        self._bucket_of: dict[str, int] = {}

    def _remove_bucket(self, b: int) -> None:
        self.R.append(b)
        self.N -= 1
        self.A[b] = self.N
        self.W[self.L[b]] = self.W[self.N]
        self.L[self.W[self.N]] = self.L[b]
        self.K[b] = self.W[self.N]

    def _add_bucket(self) -> int:
        b = self.R.pop()
        self.A[b] = 0
        self.W[self.N] = b
        self.L[b] = self.N
        self.K[b] = b
        self.N += 1
        return b

    def add_node(self, node: str, weight: float = 1.0) -> None:
        self._bucket_of[node] = b = self._add_bucket()
        self._name_of[b] = node

    def remove_node(self, node: str) -> None:
        b = self._bucket_of.pop(node)
        del self._name_of[b]
        self._remove_bucket(b)

    @property
    def nodes(self) -> list[str]:
        return list(self._bucket_of)

    def _bucket(self, key: str) -> int:
        b = _h64(key) % self.a
        while self.A[b] != 0:
            h = _h64(f"{key}#{self.A[b]}") % self.A[b]
            while self.A[h] >= self.A[b]:
                h = self.K[h]
            b = h
        return b

    def route(self, key: str) -> str:
        return self._name_of[self._bucket(key)]

    def route_batch(self, keys):
        return [self.route(k) for k in keys]
