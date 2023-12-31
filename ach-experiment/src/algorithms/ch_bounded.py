"""SOTA baseline: Consistent Hashing with Bounded Loads (Mirrokni, Thorup,
Zadimoghaddam - Google, 2017), adapted to the token-reassignment model.

Each step, nodes whose load exceeds the cap (1+eps)*mean shed their largest-arc
tokens to the **next node forward on the ring** that is below cap (the
consistent-hashing-preserving move), respecting v_min. Distinct from the greedy
Bounded-Loads baseline, which moves to the globally least-loaded node.
"""
import numpy as np


class CHBoundedLoads:
    name = "CH-BL"

    def __init__(self, epsilon: float = 0.25, v_min: int = 3, max_tokens: int = 2):
        self.epsilon = float(epsilon)
        self.v_min = int(v_min)
        self.max_tokens = int(max_tokens)

    def step(self, ring, ell: np.ndarray, total_load: float, t: int) -> float:
        ell = np.asarray(ell, dtype=np.float64)
        mean = float(np.mean(ell))
        if mean < 1e-9:
            return 0.0
        cap = (1.0 + self.epsilon) * mean
        over = np.where(ell > cap)[0]
        if len(over) == 0:
            return 0.0

        prev = ring.snapshot()
        V = ring.V
        a = ring.a
        for src in over[np.argsort(-ell[over])]:
            src_tokens = np.where(a == src)[0]
            budget = min(self.max_tokens, len(src_tokens) - self.v_min)
            if budget <= 0:
                continue
            cand = src_tokens[np.argsort(-ring.L[src_tokens])][:budget]
            for p in cand:
                recv = -1
                for off in range(1, V):
                    node = int(a[(p + off) % V])
                    if node != src and ell[node] < cap:
                        recv = node
                        break
                if recv >= 0:
                    ring.reassign(np.array([p], dtype=np.int32),
                                  np.array([recv], dtype=np.int32))
        return ring.get_M_keys(prev)
