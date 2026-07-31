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


def yes(v):
    return str(v).strip().lower() in ("true", "1", "yes", "y")


def build(lead):
    company = lead.get("company") or lead["domain"]
    niche = NICHE_FI.get(lead.get("niche", ""), lead.get("niche", ""))

    obs = []
    recs = []

    obs.append("Google-mainonta on aktiivista (vahvistettu Googlen julkisesta mainostajarekisteristä).")

    if yes(lead.get("conv_tracking")):
        obs.append("Konversioseuranta löytyy sivustolta.")
    else:
        obs.append("Konversioseurantaa ei löytynyt.")
        recs.append("Asentakaa Google Ads -konversioseuranta ensimmäisenä.")

    if yes(lead.get("meta_pixel")):
        obs.append("Meta-pikseli löytyy sivustolta.")
    else:
        obs.append("Meta-pikseliä ei löytynyt.")
        recs.append("Ottakaa Meta-pikseli käyttöön uudelleenmarkkinointia varten.")

    q = (lead.get("quality_issues") or "").strip()
    if q:
        obs.append(f"Sivustolla havaittiin seuraavia laatuongelmia: {q}.")
        recs.append("Korjatkaa sivuston tekniset laatuongelmat ennen mainosbudjetin kasvattamista.")

    flags = (lead.get("issue_flags") or "").strip()
    if flags:
        obs.append(f"Havaitut tekniset liput: {flags}.")

    if not recs:
        recs.append("Jatkakaa kampanjoiden optimointia datan perusteella.")
    recs.append("Nopea vastaaminen liideihin parantaa mainonnan tuottoa.")

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
    lines.extend(["", "## Suositukset", ""])
    lines.extend(f"{i}. {r}" for i, r in enumerate(recs, 1))
    lines.extend([
        "",
        "Käydään läpi 15 minuutissa, jos haluatte.",
        "",
        "Felix Wickholm / Wicflow Oy",
    ])
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
            written += 1

    print(f"Generated {written} analyses from {total} hotlist rows -> {outdir}")


if __name__ == "__main__":
    main()