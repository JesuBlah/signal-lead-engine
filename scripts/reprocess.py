#!/usr/bin/env python3
"""ads-radar reprocess: recompute google_ads / meta_pixel / conv_tracking / segment
from an EXISTING results.jsonl, without re-scanning the web.

Why this exists: the original scan_domain() logic in scan.py had two data bugs,
fixed 2026-08-01:
  1. google_ads / meta_pixel were set True from bare domain-reference regexes
     (no ID required) -> false positives.
  2. google_conv_tracking was computed as bool(aw_ids or conv_ids), which means
     the mere presence of the base Ads tag (aw_ids) was treated as proof a
     conversion action was configured. It isn't -- only conv_ids (a resolved
     conversion ID) is real evidence of tracking. This bug meant EVERY company
     running live ads was automatically marked as "has conversion tracking",
     so the "live ads + zero tracking" segment (the best prospects) was
     structurally unreachable.

The raw ID arrays (google_aw_ids, google_conversion_ids, meta_pixel_ids) were
already captured correctly in results.jsonl at scan time -- only the derived
booleans were wrong. This script recomputes them from those arrays in place,
so you get corrected data across all already-scanned domains for free.

Usage:
  python3 scripts/reprocess.py --results-root ~/business/active/ads-radar/run-name
  python3 scripts/reprocess.py --results-root resultsd --dry-run   # preview counts only
"""

import argparse
import json
from pathlib import Path


def recompute(r):
    a = r.get("ads") or {}
    q = r.get("quality") or {}
    aw_ids = a.get("google_aw_ids") or []
    conv_ids = a.get("google_conversion_ids") or []
    meta_pixel_ids = a.get("meta_pixel_ids") or []

    a["google_ads"] = bool(aw_ids or conv_ids)
    a["google_conv_tracking"] = bool(conv_ids)
    a["meta_pixel"] = bool(meta_pixel_ids)
    r["ads"] = a

    quality_issues = r.get("quality_issues", 0)
    if a["google_ads"] or a["meta_pixel"]:
        if quality_issues >= 2:
            r["segment"] = "A_ads_weak_site"
        elif a["google_ads"] and not a["google_conv_tracking"]:
            r["segment"] = "B_ads_no_conv_tracking"
        else:
            r["segment"] = "C_ads_ok_site"
    else:
        r["segment"] = "D_no_ads_detected"

    if a["google_ads"] or a["meta_pixel"]:
        r["aspakone_segment"] = r.get("aspakone_segment") or "S2_advertiser"
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", required=True)
    ap.add_argument("--dry-run", action="store_true", help="print before/after counts, don't write")
    args = ap.parse_args()

    root = Path(args.results_root).expanduser()
    direct = root / "results.jsonl"
    paths = [direct] if direct.exists() else sorted(root.glob("*/results.jsonl"))
    if not paths:
        raise SystemExit(f"no results.jsonl under {root}")

    total_before = {"google_ads": 0, "meta_pixel": 0, "conv_tracking": 0}
    total_after = {"google_ads": 0, "meta_pixel": 0, "conv_tracking": 0}
    seg_before, seg_after = {}, {}

    for p in paths:
        rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        for r in rows:
            a = r.get("ads") or {}
            if a.get("google_ads"):
                total_before["google_ads"] += 1
            if a.get("meta_pixel"):
                total_before["meta_pixel"] += 1
            if a.get("google_conv_tracking"):
                total_before["conv_tracking"] += 1
            seg_before[r.get("segment", "?")] = seg_before.get(r.get("segment", "?"), 0) + 1

        rows = [recompute(r) for r in rows]

        for r in rows:
            a = r.get("ads") or {}
            if a.get("google_ads"):
                total_after["google_ads"] += 1
            if a.get("meta_pixel"):
                total_after["meta_pixel"] += 1
            if a.get("google_conv_tracking"):
                total_after["conv_tracking"] += 1
            seg_after[r.get("segment", "?")] = seg_after.get(r.get("segment", "?"), 0) + 1

        if not args.dry_run:
            with open(p, "w") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("google_ads:      ", total_before["google_ads"], "->", total_after["google_ads"])
    print("meta_pixel:      ", total_before["meta_pixel"], "->", total_after["meta_pixel"])
    print("conv_tracking:   ", total_before["conv_tracking"], "->", total_after["conv_tracking"])
    print()
    print("segments before:", dict(sorted(seg_before.items())))
    print("segments after: ", dict(sorted(seg_after.items())))
    if args.dry_run:
        print("\n(dry run - no files written; drop --dry-run to apply)")
    else:
        print(f"\nrewrote {len(paths)} results.jsonl file(s) in place. Now re-run report.py.")


if __name__ == "__main__":
    main()