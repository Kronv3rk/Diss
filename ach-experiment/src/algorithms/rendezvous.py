"""SOTA baseline: capacity-weighted Rendezvous / HRW hashing (static placement).

Weighted Highest-Random-Weight (Thaler & Ravishankar 1998; weighted variant):
token s is owned by argmax_i  w_i / (-ln u_{s,i}),  u_{s,i} ~ U(0,1) deterministic
per (token, node). P(node i wins) = w_i / sum_j w_j, so placement is
capacity-proportional in expectation with good spread. Static: computed once.
"""
import numpy as np


class HRW:
    name = "HRW"

    def __init__(self, capacities, V, seed: int = 20240517):
        self.capacities = np.asarray(capacities, dtype=np.float64)
        self.V = int(V)
        self.seed = int(seed)
        self._initialized = False

    def _assignment(self) -> np.ndarray:
        n = len(self.capacities)
        scores = np.empty((self.V, n), dtype=np.float64)
        for i in range(n):
            rng = np.random.RandomState((self.seed + i * 9176) % (2**32))
            u = rng.uniform(1e-12, 1.0, self.V)
            scores[:, i] = self.capacities[i] / (-np.log(u))
        return np.argmax(scores, axis=1).astype(np.int32)

    def step(self, ring, ell: np.ndarray, total_load: float, t: int) -> float:
        if self._initialized:
            return 0.0
        prev = ring.snapshot()
        ring.reassign(np.arange(self.V, dtype=np.int32), self._assignment())
        self._initialized = True
        return ring.get_M_keys(prev)
