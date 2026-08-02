#!/usr/bin/env python3
"""ads-radar verify: confirm domains as ACTIVE Google advertisers via the public
Ads Transparency Center RPC (free, no key).

Usage:
  verify.py --domains tupatarkastus.fi,wicflow.com
  verify.py --hotlist HOTLIST.csv

Cache: verified.jsonl (resume-safe). Throttle: 1 req/s.
"""

import argparse
import csv
import difflib
import html
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from collections import Counter
from http.cookiejar import CookieJar
from pathlib import Path

LEGAL_SUFFIXES = ("oyj", "oy", "ab", "ky", "ry", "tmi", "osk")

FI_CHAR_MAP = str.maketrans({"a": "a", "a": "a", "o": "o"})


def normalize_name(name):
    if not name:
        return ""
    n = html.unescape(name)
    n = n.replace(chr(173), "")
    n = n.lower()
    n = re.sub(r"[^a-z0-9\s]", " ", n)
    words = n.split()
    words = [w for w in words if w not in LEGAL_SUFFIXES]
    return " ".join(sorted(words))


def name_similarity(company_raw, advertiser):
    if not company_raw or not advertiser:
        return 0.0
    segments = re.split(r"\s[-|/\u2013\u2502\u00b7]\s", company_raw) + [company_raw]
    nb = normalize_name(advertiser)
    nb_tokens = set(nb.split())
    if not nb:
        return 0.0
    best = 0.0
    for seg in segments:
        na = normalize_name(seg)
        if not na:
            continue
        best = max(best, difflib.SequenceMatcher(None, na, nb).ratio())
        na_tokens = set(na.split())
        if na_tokens and nb_tokens:
            if len(na_tokens) <= len(nb_tokens):
                smaller, larger = na_tokens, nb_tokens
            else:
                smaller, larger = nb_tokens, na_tokens
            if smaller and smaller.issubset(larger):
                best = max(best, 0.9)
    return best

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
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
            _opener.open(req, timeout=15).read(50000)
        except Exception:
            pass
    return _opener


def check_domain(domain, _retries=3):
    global _opener
    payload = json.dumps({"1": domain, "2": 1, "3": {"12": {"1": domain}}, "7": {"1": 1}})
    body = urllib.parse.urlencode({"f.req": payload}).encode()
    req = urllib.request.Request(RPC, data=body, headers={
        **HEADERS, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    try:
        raw = opener().open(req, timeout=20).read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 429 and _retries > 0:
            time.sleep(45)
            _opener = None
            return check_domain(domain, _retries - 1)
        return {"domain": domain, "verified": None, "error": "HTTPError: " + str(e)}
    except Exception as e:
        return {"domain": domain, "verified": None, "error": type(e).__name__ + ": " + str(e)}
    if raw.startswith(")]}'"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[4:]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"domain": domain, "verified": None, "error": "unparseable"}
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
    print("verifying " + str(len(domains)) + " domains (" + str(len(cache)) + " cached)")
    with open(cache_path, "a") as fh:
        for i, d in enumerate(domains, 1):
            res = check_domain(d)
            cache[d] = res
            fh.write(json.dumps(res, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 20 == 0:
                ok = sum(1 for r in cache.values() if r.get("verified"))
                print("  " + str(i) + "/" + str(len(domains)) + " (live so far: " + str(ok) + ")")
            time.sleep(args.sleep)

    out_path = hl_path.parent / "HOTLIST-verified.csv"

    advertiser_name_counts = Counter()
    for r in rows:
        v = cache.get(r["domain"], {})
        name = next(iter((v.get("advertisers") or {}).values()), "")
        if name:
            advertiser_name_counts[normalize_name(name)] += 1
    AGENCY_THRESHOLD = 3
    MATCH_THRESHOLD = 0.72

    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        fields = list(rows[0].keys()) + [
            "google_verified_live", "google_advertiser_name", "ads_status",
            "advertiser_reconciliation", "advertiser_match_score",
        ]
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

            reconciliation, score = "n/a", ""
            if live and name:
                score_val = name_similarity(r.get("company", ""), name)
                score = "{:.2f}".format(score_val)
                is_agency_pattern = advertiser_name_counts[normalize_name(name)] >= AGENCY_THRESHOLD
                if score_val >= MATCH_THRESHOLD:
                    reconciliation = "match"
                elif is_agency_pattern:
                    reconciliation = "likely_agency"
                else:
                    reconciliation = "mismatch"
                    status = "ADVERTISER_MISMATCH"

            w.writerow(list(r.values()) + [live, name, status, reconciliation, score])

    live_n = sum(1 for r in rows if cache.get(r["domain"], {}).get("verified"))
    mismatch_n = 0
    with open(out_path) as fh:
        for row in csv.DictReader(fh):
            if row.get("advertiser_reconciliation") == "mismatch":
                mismatch_n += 1
    print("done: " + str(live_n) + "/" + str(len(rows)) + " rows LIVE (raw), " + str(mismatch_n) + " flagged ADVERTISER_MISMATCH -> " + str(out_path))
    if mismatch_n:
        print("  -> " + str(mismatch_n) + " rows found a live advertiser but the name does not match the company or a known agency pattern. Excluded from LIVE_CONFIRMED.")


if __name__ == "__main__":
    main()
