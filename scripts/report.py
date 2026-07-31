#!/usr/bin/env python3
"""ads-radar report: rank scan results into a hotlist, enriched with finderfirm revenue.

Usage:
  report.py --results-root ~/business/active/ads-radar/2026-07-19-nichetest \
            [--db ~/business/code/wicflow-tools/data/wicflow.db] \
            [--min-revenue 1000000]

Walks <results-root>/*/results.jsonl (subdir name = run label, kept in the "run"
column for grouping; a bare results.jsonl directly in the root also works),
joins revenue/employees from finderfirm via the y_tunnus that scan.py passes
through in source_row, writes:
  <results-root>/HOTLIST.csv   ranked leads (advertisers only), with the
                                niche/niche_source/niche_confidence that
                                scan.py auto-detected per domain
  <results-root>/SUMMARY.md    per-run funnel + top leads
"""

import argparse
import csv
import json
import sqlite3
from pathlib import Path


def load_results(root):
    runs = {}
    root = Path(root).expanduser()
    direct = root / "results.jsonl"
    paths = [direct] if direct.exists() else sorted(root.glob("*/results.jsonl"))
    for p in paths:
        niche = p.parent.name if p.parent != root else root.name
        rows = []
        for line in p.read_text().splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        runs[niche] = rows
    return runs


def enrich_revenue(runs, db_path):
    if not db_path or not Path(db_path).expanduser().exists():
        return
    con = sqlite3.connect(str(Path(db_path).expanduser()))
    yts = set()
    for rows in runs.values():
        for r in rows:
            yt = (r.get("source_row") or {}).get("y_tunnus")
            if yt:
                yts.add(yt)
    if not yts:
        return
    # finderfirm scraper artifacts: some runs stamp one aggregate revenue onto every
    # row (e.g. 709186588 on 331 companies). Null any value shared by >5 companies.
    suspect = {row[0] for row in con.execute(
        "SELECT revenue_eur FROM finderfirm WHERE revenue_eur > 100000 "
        "GROUP BY revenue_eur HAVING COUNT(DISTINCT y_tunnus) > 5")}
    data = {}
    yl = list(yts)
    for i in range(0, len(yl), 500):
        chunk = yl[i:i + 500]
        q = ",".join("?" * len(chunk))
        for yt, rev, emp, ind in con.execute(
                f"SELECT y_tunnus, revenue_eur, employees, industry FROM finderfirm WHERE y_tunnus IN ({q})", chunk):
            data[yt] = {"revenue_eur": None if rev in suspect else rev, "employees": emp, "industry": ind}
    for rows in runs.values():
        for r in rows:
            yt = (r.get("source_row") or {}).get("y_tunnus")
            if yt in data:
                r["firm"] = data[yt]


def company_name(r):
    src = r.get("source_row") or {}
    for k in src:
        if k.strip().lower() in ("company_name", "name", "company", "yritys", "nimi"):
            return src[k]
    return r.get("quality", {}).get("title", "")[:60]


def lead_score(r):
    """Higher = hotter. Ads signal + site weakness + size."""
    a, q = r.get("ads", {}), r.get("quality", {})
    s = 0
    if a.get("google_conv_tracking"):
        s += 30
    elif a.get("google_ads"):
        s += 22
    if a.get("meta_pixel"):
        s += 12
    if a.get("google_ads") and not a.get("google_conv_tracking"):
        s += 15  # spending blind
    s += min(r.get("quality_issues", 0), 5) * 6
    rev = (r.get("firm") or {}).get("revenue_eur") or 0
    if rev >= 10_000_000:
        s += 20
    elif rev >= 2_000_000:
        s += 15
    elif rev >= 1_000_000:
        s += 8
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", required=True)
    ap.add_argument("--db", default="~/business/code/wicflow-tools/data/wicflow.db")
    ap.add_argument("--min-revenue", type=int, default=0)
    ap.add_argument("--top", type=int, default=25, help="leads listed per niche in SUMMARY.md")
    args = ap.parse_args()

    root = Path(args.results_root).expanduser()
    runs = load_results(root)
    if not runs:
        raise SystemExit(f"no results.jsonl under {root}")
    enrich_revenue(runs, args.db)

    hot = []
    for niche, rows in runs.items():
        for r in rows:
            a = r.get("ads", {})
            if not (a.get("google_ads") or a.get("meta_pixel")):
                continue
            rev = (r.get("firm") or {}).get("revenue_eur") or 0
            if args.min_revenue and rev and rev < args.min_revenue:
                continue
            r["_niche"] = niche
            r["_score"] = lead_score(r)
            hot.append(r)
    hot.sort(key=lambda r: -r["_score"])

    hl = root / "HOTLIST.csv"
    with open(hl, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["score", "run", "niche", "niche_source", "niche_confidence", "company", "domain",
                    "segment", "revenue_eur", "employees",
                    "google_ads", "conv_tracking", "meta_pixel", "quality_issues",
                    "issue_flags", "platform", "email", "phone", "city"])
        for r in hot:
            q = r.get("quality", {})
            src = r.get("source_row") or {}
            firm = r.get("firm") or {}
            flags = ",".join(k for k in ("favicon_missing", "no_meta_description", "no_viewport",
                                         "no_h1", "stale_copyright", "slow_response", "no_title") if q.get(k))
            w.writerow([r["_score"], r["_niche"], r.get("niche", ""), r.get("niche_source", ""),
                        r.get("niche_confidence", ""), company_name(r), r["domain"], r.get("segment", ""),
                        firm.get("revenue_eur", ""), firm.get("employees", ""),
                        r["ads"].get("google_ads"), r["ads"].get("google_conv_tracking"),
                        r["ads"].get("meta_pixel"), r.get("quality_issues", ""), flags,
                        q.get("platform", ""), src.get("email", ""), src.get("phone", ""),
                        src.get("city", "")])

    lines = [f"# ads-radar summary — {root.name}", ""]
    for niche, rows in sorted(runs.items()):
        fetched = [r for r in rows if r.get("fetched")]
        segs = {}
        for r in fetched:
            segs[r.get("segment", "?")] = segs.get(r.get("segment", "?"), 0) + 1
        ads_n = sum(v for k, v in segs.items() if k.startswith(("A", "B", "C")))
        lines += [f"## {niche} — {len(rows)} domains, {len(fetched)} reachable, "
                  f"{ads_n} advertisers ({0 if not fetched else round(100 * ads_n / len(fetched))}%)",
                  "", "| segment | n |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in sorted(segs.items())]
        top = [r for r in hot if r["_niche"] == niche][: args.top]
        if top:
            lines += ["", "| score | company | domain | seg | rev € | issues |", "|---|---|---|---|---|---|"]
            for r in top:
                firm = r.get("firm") or {}
                lines.append(f"| {r['_score']} | {company_name(r)} | {r['domain']} | {r.get('segment','')[:1]} | "
                             f"{firm.get('revenue_eur') or ''} | {r.get('quality_issues','')} |")
        lines.append("")
    (root / "SUMMARY.md").write_text("\n".join(lines))
    print(f"hotlist: {hl} ({len(hot)} advertisers)")
    print(f"summary: {root / 'SUMMARY.md'}")


if __name__ == "__main__":
    main()
