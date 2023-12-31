"""Make `src` importable in tests without per-file sys.path hacks."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
