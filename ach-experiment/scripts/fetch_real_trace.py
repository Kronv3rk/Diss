"""Fetch a real public workload trace and convert it to the popularity CSV
format read by src/trace_loader.py (one `key,count` line per key).

Run on a machine WITH internet (the experiment sandbox is network-restricted):

    python scripts/fetch_real_trace.py wikipedia --days 7 --out traces/wikipedia_real.csv

Then point a config at it:   trace: traces/wikipedia_real.csv
"""
import argparse
import csv
import json
import os
import urllib.request
from collections import Counter
from datetime import date, timedelta

WIKI = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
        "en.wikipedia/all-access/{y}/{m:02d}/{d:02d}")


def fetch_wikipedia(days: int, out: str) -> None:
    """Aggregate top-article view counts over recent days (real popularity)."""
    counts: Counter = Counter()
    start = date.today() - timedelta(days=2)
    for i in range(days):
        dd = start - timedelta(days=i)
        url = WIKI.format(y=dd.year, m=dd.month, d=dd.day)
        req = urllib.request.Request(url, headers={"User-Agent": "ach-experiment/0.1 (research)"})
        try:
            data = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:                       # noqa: BLE001
            print(f"  skip {dd}: {e}")
            continue
        for art in data["items"][0]["articles"]:
            counts[art["article"]] += int(art["views"])
        print(f"  {dd}: {len(counts)} unique articles so far")
    _write(counts, out)


def _write(counts: Counter, out: str) -> None:
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for k, c in counts.most_common():
            w.writerow([k, c])
    print(f"wrote {len(counts)} keys -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", choices=["wikipedia"])
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", default="traces/wikipedia_real.csv")
    args = ap.parse_args()
    if args.source == "wikipedia":
        fetch_wikipedia(args.days, args.out)


if __name__ == "__main__":
    main()

# Other real traces (large; download manually, then convert to key,count CSV):
#   - Twitter cache trace (Twemcache):  https://github.com/twitter/cache-trace
#   - SNIA IOTTA block/KV traces:       http://iotta.snia.org
#   - Alibaba cluster trace:            https://github.com/alibaba/clusterdata
