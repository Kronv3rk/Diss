"""Fetch a real public workload trace and convert it to the popularity CSV
format read by src/trace_loader.py (one `key,count` line per key).

Run on a machine WITH internet (the experiment sandbox is network-restricted):

    python scripts/fetch_real_trace.py wikipedia --days 7 --out traces/wikipedia_real.csv

or, for the trace used in series TRACE (one full day of the Wikimedia hourly
pageview dumps, English Wikipedia desktop + mobile, all titles):

    python scripts/fetch_real_trace.py wikipedia-hourly --date 2024-01-15 \
        --top 60000 --out traces/wikipedia_en_20240115.csv

Then point a config at it:   trace: traces/wikipedia_en_20240115.csv
"""
import argparse
import csv
import gzip
import hashlib
import io
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


DUMP = ("https://dumps.wikimedia.org/other/pageviews/{y}/{y}-{m:02d}/"
        "pageviews-{y}{m:02d}{d:02d}-{h:02d}0000.gz")


def fetch_wikipedia_hourly(day: str, domains: list, top: int, out: str) -> None:
    """Aggregate one day (24 hourly dumps) of Wikimedia pageview counts.

    Each dump line is "domain_code page_title count_views response_size";
    views of the same title are summed over the 24 hours and over the given
    domain codes (e.g. "en" = desktop, "en.m" = mobile).  The unknown title
    "-" is skipped.  The SHA-256 of every downloaded dump is written next to
    the output so the trace can be re-derived and checked.
    """
    y, m, d = (int(x) for x in day.split("-"))
    doms = set(domains)
    counts: dict = {}
    hashes = []
    for h in range(24):
        url = DUMP.format(y=y, m=m, d=d, h=h)
        req = urllib.request.Request(url, headers={"User-Agent": "ach-experiment/0.1 (research)"})
        raw = urllib.request.urlopen(req, timeout=900).read()
        hashes.append((url.rsplit("/", 1)[1], hashlib.sha256(raw).hexdigest()))
        with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.split(" ")
                if len(parts) < 3 or parts[0] not in doms or parts[1] == "-":
                    continue
                counts[parts[1]] = counts.get(parts[1], 0) + int(parts[2])
        print(f"  hour {h:02d}: {len(counts)} titles so far")
    best = Counter(counts).most_common(top)
    _write(Counter(dict(best)), out)
    with open(out + ".sha256", "w") as f:
        for name, sha in hashes:
            f.write(f"{sha}  {name}\n")
    total = sum(counts.values())
    print(f"day total views {total}, unique titles {len(counts)}")


def _write(counts: Counter, out: str) -> None:
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for k, c in counts.most_common():
            w.writerow([k, c])
    print(f"wrote {len(counts)} keys -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", choices=["wikipedia", "wikipedia-hourly"])
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--date", default="2024-01-15",
                    help="wikipedia-hourly: day of the hourly dumps (YYYY-MM-DD)")
    ap.add_argument("--domains", default="en,en.m",
                    help="wikipedia-hourly: comma-separated domain codes")
    ap.add_argument("--top", type=int, default=60000,
                    help="wikipedia-hourly: number of most viewed titles to keep")
    ap.add_argument("--out", default="traces/wikipedia_real.csv")
    args = ap.parse_args()
    if args.source == "wikipedia":
        fetch_wikipedia(args.days, args.out)
    else:
        fetch_wikipedia_hourly(args.date, args.domains.split(","), args.top, args.out)


if __name__ == "__main__":
    main()

# Other real traces (large; download manually, then convert to key,count CSV):
#   - Twitter cache trace (Twemcache):  https://github.com/twitter/cache-trace
#   - SNIA IOTTA block/KV traces:       http://iotta.snia.org
#   - Alibaba cluster trace:            https://github.com/alibaba/clusterdata
