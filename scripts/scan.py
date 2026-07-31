#!/usr/bin/env python3
"""ads-radar scanner: detect paid-ads footprints + website-quality signals for a list of domains.

Stdlib only (urllib, concurrent.futures). Resumable via incremental JSONL.

Usage:
  scan.py --input domains.csv --output ~/business/active/ads-radar/run-name
  scan.py --domains tupatarkastus.fi,example.fi --output /tmp/adhoc
  scan.py --input list.csv --column website --workers 16 --limit 200

Input: CSV (auto-detects domain column: website/domain/url/www/kotisivu/verkkosivut)
       or plain text, one domain per line. All original CSV columns pass through.
Output: <output>/results.jsonl (incremental, resume-safe)
        <output>/results.csv   (rebuilt from JSONL at end)
        summary printed to stdout.
"""

import argparse
import concurrent.futures
import csv
import json
import re
import ssl
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
MAX_BYTES = 1_500_000
TIMEOUT = 12

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE  # scanner, not a client; many SMB certs are misconfigured

RE = {
    "aw": re.compile(r"AW-\d{6,}"),
    "gtm": re.compile(r"GTM-[A-Z0-9]{4,}"),
    "ga4": re.compile(r"G-[A-Z0-9]{8,12}"),
    "gads_domains": re.compile(r"googleadservices|googlesyndication|google_conversion|doubleclick\.net", re.I),
    "conversion_linker": re.compile(r"conversion_linker|_gcl_aw", re.I),
    "meta_pixel_id": re.compile(r"fbq\(\s*['\"]init['\"]\s*,\s*['\"](\d{6,})['\"]"),
    "meta_any": re.compile(r"connect\.facebook\.net|facebook\.com/tr\?", re.I),
    "bing_uet": re.compile(r"bat\.bing\.com|\buetq\b", re.I),
    "linkedin": re.compile(r"snap\.licdn\.com|_linkedin_partner_id", re.I),
    "tiktok": re.compile(r"analytics\.tiktok\.com", re.I),
    "gtm_conv_id": re.compile(r'"vtp_conversionId"\s*:\s*"(\d{6,})"'),
    "title": re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S),
    "meta_desc": re.compile(r'<meta[^>]+name=["\']description["\'][^>]*>', re.I),
    "viewport": re.compile(r'<meta[^>]+name=["\']viewport["\']', re.I),
    "h1": re.compile(r"<h1[\s>]", re.I),
    "icon_link": re.compile(r'<link[^>]+rel=["\'][^"\']*icon[^"\']*["\'][^>]*>', re.I),
    "copyright_year": re.compile(r"(?:©|&copy;|copyright)\s*(?:\D{0,20})?(20\d\d)", re.I),
    "ldjson": re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S),
    "h1_text": re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S),
    "meta_desc_text": re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', re.I | re.S),
}

# --- Aspakone detector groups (additive, 2026-07-29) ---------------------------
# The Aspakone ICP is "site with verified traffic", not an industry. These three
# groups turn a plain domain into one of the three sourcing segments without
# touching the ads/quality logic above. TOL sourcing cannot do this: under
# TOL 2025 there is no industry code for verkkokauppa at all.
ECOM = [
    ("shopify", re.compile(r"cdn\.shopify|myshopify|shopify-features", re.I)),
    ("woocommerce", re.compile(r"woocommerce|wc-ajax|wp-content/plugins/woocommerce", re.I)),
    ("mycashflow", re.compile(r"mycashflow|mcfstatic", re.I)),
    ("vilkas_epages", re.compile(r"epages|vilkas\.fi|/WebRoot/", re.I)),
    ("magento", re.compile(r"/static/version|Magento_|mage/cookies", re.I)),
    ("prestashop", re.compile(r"prestashop|/modules/ps_", re.I)),
    ("wix_stores", re.compile(r"wixstores|ecom-platform", re.I)),
    ("squarespace_commerce", re.compile(r"squarespace-commerce|/commerce/", re.I)),
    ("shopware", re.compile(r"shopware", re.I)),
    ("crasman", re.compile(r"crasman", re.I)),
]

PAY = [
    ("paytrail", re.compile(r"paytrail", re.I)),
    ("checkout_fi", re.compile(r"checkout\.fi|checkout-finland", re.I)),
    ("klarna", re.compile(r"klarna", re.I)),
    ("walley", re.compile(r"walley|collector\.se", re.I)),
    ("svea", re.compile(r"svea(?:pay|economy|checkout)|svea\.(?:com|fi)", re.I)),
    ("mobilepay", re.compile(r"mobilepay", re.I)),
    ("verifone", re.compile(r"verifone|point\.fi", re.I)),
    ("stripe", re.compile(r"js\.stripe\.com|stripe\.com/v3", re.I)),
]

CHAT = [
    ("leadoo", re.compile(r"leadoo", re.I)),
    ("giosg", re.compile(r"giosg", re.I)),
    ("smartsupp", re.compile(r"smartsupp", re.I)),
    ("tawk", re.compile(r"tawk\.to", re.I)),
    ("intercom", re.compile(r"intercom(?:cdn|\.io)|widget\.intercom", re.I)),
    ("crisp", re.compile(r"crisp\.chat", re.I)),
    ("zendesk", re.compile(r"zopim|zendesk\.com/embeddable|static\.zdassets", re.I)),
    ("hubspot_chat", re.compile(r"js\.hs-scripts\.com|hubspot.*conversations", re.I)),
    ("drift", re.compile(r"js\.driftt\.com|drift\.com", re.I)),
    ("trengo", re.compile(r"trengo", re.I)),
    ("ninchat", re.compile(r"ninchat", re.I)),
    ("chatra", re.compile(r"chatra\.io", re.I)),
    ("freshchat", re.compile(r"freshchat|wchat\.freshchat", re.I)),
    ("tidio", re.compile(r"tidio", re.I)),
    ("livechat", re.compile(r"livechatinc", re.I)),
]

PLATFORMS = [
    ("wordpress", re.compile(r"wp-content|wp-includes", re.I)),
    ("elementor", re.compile(r"elementor", re.I)),
    ("wix", re.compile(r"wix\.com|wixstatic", re.I)),
    ("squarespace", re.compile(r"squarespace", re.I)),
    ("webflow", re.compile(r"webflow", re.I)),
    ("shopify", re.compile(r"cdn\.shopify|myshopify", re.I)),
    ("nextjs", re.compile(r"_next/static|__NEXT_DATA__")),
    ("duda", re.compile(r"dudaone|dudamobile", re.I)),
    ("kotisivukone", re.compile(r"kotisivukone", re.I)),
]

# --- Niche detection (additive, 2026-07-30) -------------------------------
# scan.py is now the single source of truth for business niche, replacing the
# manual icebreakers-ads-push.csv labeling step. Preferred signal is a
# Schema.org / JSON-LD "@type" declaration (high confidence, structured);
# fallback is keyword matching over title/meta description/H1s/visible text
# (Finnish + English terms, since the ICP is mostly Finnish SMBs).
SCHEMA_NICHE_MAP = {
    "plumber": "plumbing",
    "electrician": "electrical",
    "hvacbusiness": "hvac",
    "cleaningservice": "cleaning",
    "restaurant": "restaurant",
    "cafeorcoffeeshop": "cafe",
    "bakery": "bakery",
    "dentist": "dental",
    "physician": "medical",
    "medicalclinic": "medical",
    "medicalbusiness": "medical",
    "realestateagent": "real_estate",
    "locksmith": "locksmith",
    "movingcompany": "moving",
    "autorepair": "auto_repair",
    "automotivebusiness": "auto_repair",
    "beautysalon": "beauty",
    "hairsalon": "hair_salon",
    "nailsalon": "beauty",
    "legalservice": "legal",
    "attorney": "legal",
    "accountingservice": "accounting",
    "insuranceagency": "insurance",
    "generalcontractor": "contractor",
    "roofingcontractor": "roofing",
    "landscapingbusiness": "landscaping",
    "pestcontrolservice": "pest_control",
    "florist": "florist",
    "photographer": "photography",
    "veterinarycare": "veterinary",
    "gymorfitnesscenter": "fitness",
    "hotel": "hotel",
    "lodgingbusiness": "hotel",
    "carwash": "car_wash",
    "drycleaningorlaundry": "laundry",
}

NICHE_KEYWORDS = {
    "plumbing": [r"\bputkimies\b", r"\bputkiasenn\w*", r"\bLVI\b", r"\bplumb\w*"],
    "electrical": [r"sähköasenn\w*", r"sähkömies", r"\belectrician\b", r"\belectrical\b"],
    "hvac": [r"ilmanvaihto", r"lämpöpump\w*", r"\bhvac\b", r"ilmastointi"],
    "cleaning": [r"siivous\w*", r"cleaning service", r"\bcleaner\b"],
    "restaurant": [r"\bravintola\w*", r"\brestaurant\b", r"ruokalista", r"\bmenu\b"],
    "cafe": [r"\bkahvila\w*", r"\bcafe\b", r"coffee shop"],
    "bakery": [r"\bleipomo\w*", r"\bbakery\b", r"konditoria"],
    "dental": [r"hammaslääkäri\w*", r"\bdentist\w*", r"hammashoito\w*"],
    "medical": [r"\blääkäri\w*", r"terveyskeskus", r"\bclinic\b", r"medical center"],
    "real_estate": [r"kiinteistönvälit\w*", r"real estate", r"\brealtor\b", r"asunnonvälitys"],
    "locksmith": [r"lukkoseppä\w*", r"\blocksmith\b"],
    "moving": [r"muuttopalvelu\w*", r"moving company", r"\bmuutot\b"],
    "auto_repair": [r"autokorjaamo\w*", r"auto repair", r"\bkorjaamo\b", r"car service"],
    "beauty": [r"kauneushoitola\w*", r"beauty salon", r"kosmetolog\w*"],
    "hair_salon": [r"\bkampaamo\w*", r"hair salon", r"\bparturi\w*"],
    "legal": [r"asianajotoimisto\w*", r"law firm", r"lakiasiaintoimisto\w*", r"\battorney\b"],
    "accounting": [r"tilitoimisto\w*", r"accounting firm", r"kirjanpito\w*"],
    "insurance": [r"vakuutus\w*", r"insurance agency"],
    "contractor": [r"rakennusliike\w*", r"general contractor", r"remontointi\w*"],
    "roofing": [r"kattourakoitsija\w*", r"\broofing\b", r"kattoremontti\w*"],
    "landscaping": [r"pihasuunnittelu\w*", r"\blandscaping\b", r"viherrakennus\w*"],
    "pest_control": [r"tuholaistorjunta\w*", r"pest control"],
    "florist": [r"kukkakauppa\w*", r"\bflorist\b"],
    "photography": [r"valokuvaus\w*", r"\bphotographer\b", r"photography studio"],
    "veterinary": [r"eläinlääkäri\w*", r"\bveterinary\b", r"vet clinic"],
    "fitness": [r"\bkuntosali\w*", r"\bgym\b", r"fitness center"],
    "hotel": [r"\bhotelli\w*", r"\bhotel\b", r"majoitus\w*"],
    "car_wash": [r"autopesu\w*", r"car wash"],
    "laundry": [r"pesula\w*", r"\blaundry\b", r"dry cleaning"],
}
NICHE_KEYWORDS_RX = {niche: [re.compile(p, re.I) for p in pats] for niche, pats in NICHE_KEYWORDS.items()}


def _strip_html_text(html, limit=8000):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;|&amp;|&#39;|&quot;|&rsquo;", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def detect_niche(html, title):
    """Returns (niche, source, confidence). source is 'schema_org', 'keywords', or 'none'."""
    for block in RE["ldjson"].findall(html):
        try:
            data = json.loads(block.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        items = data if isinstance(data, list) else [data]
        stack = list(items)
        while stack:
            item = stack.pop()
            if not isinstance(item, dict):
                continue
            types = item.get("@type")
            types = [types] if isinstance(types, str) else (types if isinstance(types, list) else [])
            for t in types:
                niche = SCHEMA_NICHE_MAP.get(str(t).strip().lower())
                if niche:
                    return niche, "schema_org", 0.95
            graph = item.get("@graph")
            if isinstance(graph, list):
                stack.extend(g for g in graph if isinstance(g, dict))

    m = RE["meta_desc_text"].search(html)
    meta_desc = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    h1_texts = " ".join(re.sub(r"<[^>]+>", " ", h) for h in RE["h1_text"].findall(html))
    body_text = _strip_html_text(html, limit=4000)
    haystack = " ".join([title or "", meta_desc, h1_texts, body_text])

    scores = {}
    for niche, patterns in NICHE_KEYWORDS_RX.items():
        hits = sum(1 for p in patterns if p.search(haystack))
        if hits:
            scores[niche] = hits
    if scores:
        best = max(scores, key=scores.get)
        confidence = round(min(0.35 + 0.15 * scores[best], 0.85), 2)
        return best, "keywords", confidence
    return "", "none", 0.0


def fetch(url, timeout=TIMEOUT, max_bytes=MAX_BYTES):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fi,en;q=0.8"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        body = r.read(max_bytes)
        return body.decode("utf-8", errors="replace"), r.geturl(), int((time.time() - t0) * 1000), r.status


def head_status(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=8, context=CTX) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def normalize_domain(raw):
    d = raw.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    d = d.split("/")[0].split("?")[0].strip()
    return d if "." in d else None


def scan_domain(domain, row_extra=None):
    out = {"domain": domain, "fetched": False, "error": None}
    if row_extra:
        out["source_row"] = row_extra
    html, final_url, ms = "", "", None
    for scheme in ("https", "http"):
        try:
            html, final_url, ms, _status = fetch(f"{scheme}://{domain}/")
            out["fetched"] = True
            break
        except Exception as e:
            out["error"] = f"{type(e).__name__}: {e}"
    if not out["fetched"]:
        return out
    out["error"] = None
    out["final_url"] = final_url
    out["response_ms"] = ms
    out["html_kb"] = len(html) // 1024

    aw_ids = sorted(set(RE["aw"].findall(html)))
    gtm_ids = sorted(set(RE["gtm"].findall(html)))[:3]
    conv_ids = []
    gtm_signals = {"gads": False, "meta": False, "bing": False}
    for gtm in gtm_ids:
        try:
            gjs, _, _, _ = fetch(f"https://www.googletagmanager.com/gtm.js?id={gtm}", timeout=10)
        except Exception:
            continue
        aw_ids += RE["aw"].findall(gjs)
        conv_ids += RE["gtm_conv_id"].findall(gjs)
        if RE["gads_domains"].search(gjs) or RE["conversion_linker"].search(gjs):
            gtm_signals["gads"] = True
        if RE["meta_any"].search(gjs) or "fbq" in gjs:
            gtm_signals["meta"] = True
        if RE["bing_uet"].search(gjs):
            gtm_signals["bing"] = True
    aw_ids = sorted(set(aw_ids))
    conv_ids = sorted(set(conv_ids))

    meta_pixel_ids = sorted(set(RE["meta_pixel_id"].findall(html)))
    meta_present = bool(meta_pixel_ids) or bool(RE["meta_any"].search(html)) or gtm_signals["meta"]

    out["ads"] = {
        "google_aw_ids": aw_ids,
        "google_conversion_ids": conv_ids,
        "google_ads": bool(aw_ids or conv_ids or RE["gads_domains"].search(html) or gtm_signals["gads"]),
        "google_conv_tracking": bool(aw_ids or conv_ids),
        "meta_pixel_ids": meta_pixel_ids,
        "meta_pixel": meta_present,
        "bing_uet": bool(RE["bing_uet"].search(html)) or gtm_signals["bing"],
        "linkedin_insight": bool(RE["linkedin"].search(html)),
        "tiktok_pixel": bool(RE["tiktok"].search(html)),
        "gtm_ids": gtm_ids,
        "ga4_ids": sorted(set(RE["ga4"].findall(html)))[:3],
    }

    m = RE["title"].search(html)
    title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    icon_declared = bool(RE["icon_link"].search(html))
    favicon_ico = head_status(f"https://{domain}/favicon.ico")
    years = [int(y) for y in RE["copyright_year"].findall(html)]
    platform = next((name for name, rx in PLATFORMS if rx.search(html)), "")

    out["quality"] = {
        "title": title[:120],
        "no_title": not title,
        "no_meta_description": not RE["meta_desc"].search(html),
        "no_viewport": not RE["viewport"].search(html),
        "no_h1": not RE["h1"].search(html),
        "favicon_missing": (not icon_declared) and favicon_ico != 200,
        "stale_copyright": bool(years) and max(years) <= 2024,
        "copyright_year": max(years) if years else None,
        "platform": platform,
        "slow_response": ms is not None and ms > 2500,
    }
    niche, niche_source, niche_confidence = detect_niche(html, title)
    out["niche"] = niche
    out["niche_source"] = niche_source
    out["niche_confidence"] = niche_confidence

    q = out["quality"]
    out["quality_issues"] = sum(
        q[k] for k in ("no_title", "no_meta_description", "no_viewport", "no_h1",
                       "favicon_missing", "stale_copyright", "slow_response")
    )
    a = out["ads"]
    if a["google_ads"] or a["meta_pixel"]:
        out["segment"] = "A_ads_weak_site" if out["quality_issues"] >= 2 else (
            "B_ads_no_conv_tracking" if (a["google_ads"] and not a["google_conv_tracking"]) else "C_ads_ok_site")
    else:
        out["segment"] = "D_no_ads_detected"

    # --- Aspakone segmentation (additive) --------------------------------------
    ecom = [n for n, rx in ECOM if rx.search(html)]
    pay = [n for n, rx in PAY if rx.search(html)]
    chat = [n for n, rx in CHAT if rx.search(html)]
    cart_hint = bool(re.search(r"/ostoskori|/kassa|add-to-cart|lisaa-koriin|/tuote/|/verkkokauppa", html, re.I))
    out["ecom"] = {
        "platforms": ecom,
        "payment_providers": pay,
        "cart_hint": cart_hint,
        "is_webshop": bool(ecom and (pay or cart_hint)) or bool(len(pay) >= 2),
    }
    out["chat"] = {"vendors": chat, "has_chat": bool(chat)}

    # Priority order matters: an existing paid chat widget is the strongest
    # conversation (price + outcome, not education), so S3 outranks S1/S2.
    if chat:
        out["aspakone_segment"] = "S3_chat_switcher"
    elif out["ecom"]["is_webshop"]:
        out["aspakone_segment"] = "S1_webshop"
    elif a["google_ads"] or a["meta_pixel"]:
        out["aspakone_segment"] = "S2_advertiser"
    else:
        out["aspakone_segment"] = "X_no_traffic_signal"
    return out


def read_domains(args):
    rows = []
    if args.domains:
        for d in args.domains.split(","):
            nd = normalize_domain(d)
            if nd:
                rows.append((nd, None))
        return rows
    path = Path(args.input).expanduser()
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".csv" or ("," in text.splitlines()[0] or ";" in text.splitlines()[0]):
        delim = ";" if text.splitlines()[0].count(";") > text.splitlines()[0].count(",") else ","
        reader = csv.DictReader(text.splitlines(), delimiter=delim)
        col = args.column
        if not col:
            cands = [c for c in (reader.fieldnames or [])
                     if c and c.strip().lower() in ("website", "domain", "url", "www", "kotisivu",
                                                    "verkkosivu", "verkkosivut", "site", "web", "homepage",
                                                    "company_website", "website_url")]
            if not cands:
                sys.exit(f"No domain column found in {reader.fieldnames}; pass --column")
            col = cands[0]
        for r in reader:
            nd = normalize_domain(r.get(col) or "")
            if nd:
                rows.append((nd, {k: v for k, v in r.items() if k and v}))
    else:
        for line in text.splitlines():
            nd = normalize_domain(line)
            if nd:
                rows.append((nd, None))
    seen = set()
    uniq = []
    for d, extra in rows:
        if d not in seen:
            seen.add(d)
            uniq.append((d, extra))
    return uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="CSV or txt file of domains")
    ap.add_argument("--domains", help="comma-separated ad-hoc domains")
    ap.add_argument("--column", help="CSV column holding the website/domain")
    ap.add_argument("--output", required=True, help="output directory")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    if not args.input and not args.domains:
        sys.exit("need --input or --domains")

    outdir = Path(args.output).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)
    jsonl_path = outdir / "results.jsonl"

    done = set()
    if jsonl_path.exists():
        for line in jsonl_path.read_text().splitlines():
            try:
                done.add(json.loads(line)["domain"])
            except Exception:
                pass

    todo = [(d, e) for d, e in read_domains(args) if d not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"scanning {len(todo)} domains ({len(done)} already done) -> {jsonl_path}", flush=True)

    results = []
    with open(jsonl_path, "a") as fh, concurrent.futures.ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(scan_domain, d, e): d for d, e in todo}
        for i, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            try:
                res = fut.result()
            except Exception as e:
                res = {"domain": futs[fut], "fetched": False, "error": f"worker: {e}"}
            results.append(res)
            fh.write(json.dumps(res, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}", flush=True)

    # rebuild CSV from full JSONL
    all_res = [json.loads(l) for l in jsonl_path.read_text().splitlines() if l.strip()]
    csv_path = outdir / "results.csv"
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["domain", "segment", "aspakone_segment", "niche", "niche_source", "niche_confidence",
                    "ecom_platforms", "payment_providers",
                    "is_webshop", "chat_vendors", "google_ads", "google_conv_tracking", "aw_ids", "meta_pixel",
                    "meta_pixel_ids", "bing_uet", "linkedin", "quality_issues", "favicon_missing",
                    "no_meta_description", "no_viewport", "stale_copyright", "slow_response",
                    "platform", "response_ms", "title", "company", "error"])
        for r in all_res:
            a, q = r.get("ads", {}), r.get("quality", {})
            ec, ch = r.get("ecom", {}), r.get("chat", {})
            src = r.get("source_row") or {}
            company = next((src[k] for k in src if k.strip().lower() in
                            ("name", "company", "company_name", "yritys", "nimi", "toiminimi")), "")
            w.writerow([r["domain"], r.get("segment", ""), r.get("aspakone_segment", ""),
                        r.get("niche", ""), r.get("niche_source", ""), r.get("niche_confidence", ""),
                        " ".join(ec.get("platforms", []) or []),
                        " ".join(ec.get("payment_providers", []) or []),
                        ec.get("is_webshop", ""), " ".join(ch.get("vendors", []) or []),
                        a.get("google_ads", ""),
                        a.get("google_conv_tracking", ""), " ".join(a.get("google_aw_ids", []) or []) or
                        " ".join(a.get("google_conversion_ids", []) or []),
                        a.get("meta_pixel", ""), " ".join(a.get("meta_pixel_ids", []) or []),
                        a.get("bing_uet", ""), a.get("linkedin_insight", ""),
                        r.get("quality_issues", ""), q.get("favicon_missing", ""),
                        q.get("no_meta_description", ""), q.get("no_viewport", ""),
                        q.get("stale_copyright", ""), q.get("slow_response", ""),
                        q.get("platform", ""), r.get("response_ms", ""), q.get("title", ""),
                        company, r.get("error", "")])

    segs = {}
    for r in all_res:
        segs[r.get("segment", "error")] = segs.get(r.get("segment", "error"), 0) + 1
    fetched = sum(1 for r in all_res if r.get("fetched"))
    print(f"\ndone: {len(all_res)} domains, {fetched} fetched ok")
    for s in sorted(segs):
        print(f"  {s}: {segs[s]}")
    print(f"csv: {csv_path}")


if __name__ == "__main__":
    main()