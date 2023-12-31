"""Load a real workload trace into a key-popularity distribution.

Accepts either a frequency table (CSV "key,count" / "rank,count", or JSON
{key: count}) or an event log (one key per line, counted automatically), and
returns a length-NK probability vector over the key universe - a drop-in
replacement for the synthetic Zipf popularity in LoadGenerator.
"""
import json
import os
from collections import Counter

import numpy as np


def _read_counts(path: str) -> np.ndarray:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path, encoding="utf-8") as f:
            return np.asarray(list(json.load(f).values()), dtype=np.float64)
    with open(path, encoding="utf-8") as f:
        rows = [ln.rstrip("\n") for ln in f if ln.strip()]
    looks_csv = rows and all("," in r for r in rows[:20])
    if looks_csv:
        vals = []
        for r in rows:
            try:
                vals.append(float(r.split(",")[-1]))   # last column = count
            except ValueError:
                continue                                # skip header/garbage
        return np.asarray(vals, dtype=np.float64)
    counts = Counter(rows)                              # event log: count keys
    return np.asarray(list(counts.values()), dtype=np.float64)


def load_popularity(path: str, NK: int) -> np.ndarray:
    """Return a normalized popularity vector of length NK (descending),
    taking the top-NK keys by frequency and renormalizing."""
    counts = np.sort(_read_counts(path))[::-1][:NK].astype(np.float64)
    if counts.size == 0:
        raise ValueError(f"no counts parsed from trace: {path}")
    if counts.size < NK:                                # pad the tail with the min count
        counts = np.concatenate([counts, np.full(NK - counts.size, counts[-1])])
    return counts / counts.sum()
