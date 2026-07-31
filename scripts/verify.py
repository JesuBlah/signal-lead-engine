#!/usr/bin/env python3
"""ads-radar verify: confirm domains as ACTIVE Google advertisers via the public
Ads Transparency Center RPC (free, no key). Tag detection says "has the plumbing";
this says "actually ran Google Ads within ~12 months" — the only honest basis for
"you're running ads" outreach copy.

Endpoint (reverse-engineered, may rot — canary: github.com/block-town/google-ads-transparency-mcp):
  POST https://adstransparency.google.com/anji/_/rpc/SearchService/SearchCreatives?authuser=
  form: f.req={"2":40,"3":{"12":{"1":"<bare domain>"}}}
  json()["1"] non-empty => verified advertiser (entries carry advertiser id "1", name "12" or "14").

Usage:
  verify.py --domains tupatarkastus.fi,wicflow.com
  verify.py --hotlist <results-root>/HOTLIST.csv        # verifies every unique domain, rewrites
                                                        # the hotlist with verified/advertiser cols

Column handling: HOTLIST-verified.csv is built from every column already in
HOTLIST.csv (whatever those are, including niche/niche_source/niche_confidence
from scan.py's auto-detection) plus three appended columns: google_verified_live,
google_advertiser_name, ads_status. No niche logic lives here by design.
Cache: <dir-of-input>/verified.jsonl (resume-safe). Throttle: 1 req/s.
"""

import argparse
import csv
import json
import ssl
import time
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # macOS system python without certs; public read-only endpoint
    CTX = ssl.create_default_context()
    CTX.check_hostname = False
    CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,fi;q=0.8",
    "Origin": "https://adstransparency.google.com",
    "Referer": "https://adstransparency.google.com/",
}
RPC = "https://adstransparency.google.com/anji/_/rpc/SearchService/SearchCreatives?authuser="

_opener = None


def opener():
    global _opener
    if _opener is None:
        cj = CookieJar()
        _opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=CTX),
            urllib.request.HTTPCookieProcessor(cj))
        req = urllib.request.Request("https://adstransparency.google.com/?region=FI", headers=HEADERS)
        try:
            _opener.open(req, timeout=15).read(50_000)
        except Exception:
            pass
    return _opener


def check_domain(domain, _retries=3):
    global _opener
    # payload shape from block-town/google-ads-transparency-mcp (the maintained fix):
    # domain must appear in BOTH "1" and "3.12.1"; "7":{"1":1} is required.
    payload = json.dumps({"1": domain, "2": 1, "3": {"12": {"1": domain}}, "7": {"1": 1}})
    body = urllib.parse.urlencode({"f.req": payload}).encode()
    req = urllib.request.Request(RPC, data=body, headers={
        **HEADERS, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    try:
        raw = opener().open(req, timeout=20).read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 429 and _retries > 0:
            time.sleep(45)          # Google throttles bursts; cool off, fresh session
            _opener = None
            return check_domain(domain, _retries - 1)
        return {"domain": domain, "verified": None, "error": f"HTTPError: {e}"}
    except Exception as e:
        return {"domain": domain, "verified": None, "error": f"{type(e).__name__}: {e}"}
    if raw.startswith(")]}'"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[4:]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"domain": domain, "verified": None, "error": f"unparseable ({raw[:80]!r})"}
    creatives = data.get("1") or []
    advertisers = {}
    for c in creatives:
        aid = c.get("1")
        name = c.get("12") or c.get("14") or ""
        if isinstance(name, dict):
            name = name.get("1", "") or ""
        if aid:
            advertisers.setdefault(aid, name if isinstance(name, str) else "")
    return {"domain": domain, "verified": bool(creatives), "n_creatives": len(creatives),
            "advertisers": advertisers, "error": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains")
    ap.add_argument("--hotlist")
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()

    if args.domains:
        for d in args.domains.split(","):
            print(json.dumps(check_domain(d.strip()), ensure_ascii=False))
            time.sleep(args.sleep)
        return

    hl_path = Path(args.hotlist).expanduser()
    cache_path = hl_path.parent / "verified.jsonl"
    cache = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            try:
                r = json.loads(line)
                if r.get("verified") is not None:
                    cache[r["domain"]] = r
            except Exception:
                pass

    rows = list(csv.DictReader(open(hl_path)))
    domains = [d for d in dict.fromkeys(r["domain"] for r in rows) if d not in cache]
    print(f"verifying {len(domains)} domains ({len(cache)} cached) ~{int(len(domains)*args.sleep/60)+1} min")
    with open(cache_path, "a") as fh:
        for i, d in enumerate(domains, 1):
            res = check_domain(d)
            cache[d] = res
            fh.write(json.dumps(res, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 20 == 0:
                ok = sum(1 for r in cache.values() if r.get("verified"))
                print(f"  {i}/{len(domains)} (live so far: {ok})", flush=True)
            time.sleep(args.sleep)

    out_path = hl_path.parent / "HOTLIST-verified.csv"
    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        fields = list(rows[0].keys()) + ["google_verified_live", "google_advertiser_name", "ads_status"]
        w.writerow(fields)
        for r in rows:
            v = cache.get(r["domain"], {})
            live = v.get("verified")
            name = next(iter((v.get("advertisers") or {}).values()), "")
            tag_google = r.get("google_ads") == "True"
            if live:
                status = "LIVE_CONFIRMED"
            elif live is False and tag_google:
                status = "TAG_STALE_OR_HIDDEN"
            elif live is False:
                status = "META_ONLY" if r.get("meta_pixel") == "True" else "NEGATIVE"
            else:
                status = "VERIFY_ERROR"
            w.writerow(list(r.values()) + [live, name, status])
    live_n = sum(1 for r in rows if cache.get(r["domain"], {}).get("verified"))
    print(f"done: {live_n}/{len(rows)} rows LIVE_CONFIRMED -> {out_path}")


if __name__ == "__main__":
    main()