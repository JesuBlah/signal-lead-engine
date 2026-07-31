#!/usr/bin/env python3
"""
ads-radar analysis

Usage:
    python3 scripts/analysis.py \
        --hotlist resultsd/HOTLIST-verified.csv \
        --out analyses
"""

import argparse
import csv
from pathlib import Path

NICHE_FI = {
    "isannointi": "isännöinti",
    "lvi-sahko": "LVI- ja sähköala",
    "siivous": "siivousala",
    "venekaupat": "venekauppa",
    "maanrakennus-kuljetus": "maanrakennus ja kuljetus",
}

NICHE_EN = {
    "isannointi": "property management",
    "lvi-sahko": "HVAC & electrical",
    "siivous": "cleaning services",
    "venekaupat": "boat sales",
    "maanrakennus-kuljetus": "earthworks & logistics",
}


def yes(v):
    return str(v).strip().lower() in ("true", "1", "yes", "y")


def build(lead):
    company = lead.get("company") or lead["domain"]
    niche = NICHE_FI.get(lead.get("niche", ""), lead.get("niche", ""))

    obs = []

    obs.append("Google-mainonta on aktiivista (vahvistettu Googlen julkisesta mainostajarekisteristä).")

    if yes(lead.get("conv_tracking")):
        obs.append("Konversioseuranta löytyy sivustolta.")
    else:
        obs.append("Konversioseurantaa ei löytynyt.")

    if yes(lead.get("meta_pixel")):
        obs.append("Meta-pikseli löytyy sivustolta.")
    else:
        obs.append("Meta-pikseliä ei löytynyt.")

    q = (lead.get("quality_issues") or "").strip()
    if q:
        obs.append(f"Sivustolla havaittiin seuraavia laatuongelmia: {q}.")

    flags = (lead.get("issue_flags") or "").strip()
    if flags:
        obs.append(f"Havaitut tekniset liput: {flags}.")

    lines = [
        f"# Pika-analyysi: {company}",
        "",
        f"**Verkkotunnus:** {lead['domain']}",
        f"**Toimiala:** {niche}",
        f"**Niche confidence:** {lead.get('niche_confidence','')}",
        "",
        "## Havainnot",
        "",
    ]
    lines.extend(f"- {o}" for o in obs)
    return "\n".join(lines)


def build_en(lead):
    company = lead.get("company") or lead["domain"]
    niche = NICHE_EN.get(lead.get("niche", ""), lead.get("niche", ""))

    obs = []

    obs.append("Google Ads activity is live (confirmed via Google's public Ads Transparency Center).")

    if yes(lead.get("conv_tracking")):
        obs.append("Conversion tracking is installed on the site.")
    else:
        obs.append("No conversion tracking was found.")

    if yes(lead.get("meta_pixel")):
        obs.append("Meta Pixel is installed on the site.")
    else:
        obs.append("No Meta Pixel was found.")

    q = (lead.get("quality_issues") or "").strip()
    if q:
        obs.append(f"The site has the following quality issues: {q}.")

    flags = (lead.get("issue_flags") or "").strip()
    if flags:
        obs.append(f"Detected technical flags: {flags}.")

    lines = [
        f"# Quick analysis: {company}",
        "",
        f"**Domain:** {lead['domain']}",
        f"**Industry:** {niche}",
        f"**Niche confidence:** {lead.get('niche_confidence','')}",
        "",
        "## Findings",
        "",
    ]
    lines.extend(f"- {o}" for o in obs)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hotlist", required=True, help="HOTLIST-verified.csv")
    ap.add_argument("--out", required=True, help="Output directory")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    total = 0
    written = 0

    with open(args.hotlist, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for lead in reader:
            total += 1
            if not yes(lead.get("google_verified_live")):
                continue

            outfile = outdir / f"{lead['domain']}.md"
            outfile.write_text(build(lead), encoding="utf-8")
            outfile_en = outdir / f"{lead['domain']}.en.md"
            outfile_en.write_text(build_en(lead), encoding="utf-8")
            written += 1

    print(f"Generated {written} analyses from {total} hotlist rows -> {outdir}")


if __name__ == "__main__":
    main()