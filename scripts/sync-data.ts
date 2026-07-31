/**
 * Copies the latest pipeline output (../resultsd/HOTLIST-verified.csv and
 * ../analyses/*.md) into web/data and web/analyses, which is what the
 * dashboard actually reads at build/runtime.
 *
 * Run this any time you re-run the Python pipeline (scan.py -> verify.py ->
 * analysis.py) and want the dashboard to reflect the fresh results.
 *
 * Usage: npm run sync-data
 */
import fs from "fs";
import path from "path";

const ROOT = path.join(process.cwd(), ".."); // signal-lead-engine/
const WEB = process.cwd(); // signal-lead-engine/web/

const SRC_CSV = path.join(ROOT, "resultsd", "HOTLIST-verified.csv");
const DEST_CSV = path.join(WEB, "data", "HOTLIST-verified.csv");

const SRC_ANALYSES = path.join(ROOT, "analyses");
const DEST_ANALYSES = path.join(WEB, "analyses");

function copyCsv() {
  if (!fs.existsSync(SRC_CSV)) {
    console.error(`Missing ${SRC_CSV} — run the pipeline first (scripts/verify.py).`);
    process.exit(1);
  }
  fs.mkdirSync(path.dirname(DEST_CSV), { recursive: true });
  fs.copyFileSync(SRC_CSV, DEST_CSV);
  console.log(`Copied HOTLIST-verified.csv -> web/data/`);
}

function copyAnalyses() {
  if (!fs.existsSync(SRC_ANALYSES)) {
    console.error(`Missing ${SRC_ANALYSES} — run scripts/analysis.py first.`);
    process.exit(1);
  }
  fs.mkdirSync(DEST_ANALYSES, { recursive: true });
  const files = fs.readdirSync(SRC_ANALYSES).filter((f) => f.endsWith(".md"));
  for (const f of files) {
    fs.copyFileSync(path.join(SRC_ANALYSES, f), path.join(DEST_ANALYSES, f));
  }
  console.log(`Copied ${files.length} analysis file(s) -> web/analyses/`);
}

copyCsv();
copyAnalyses();
console.log("Data sync complete. Restart `npm run dev` (or redeploy) to see the changes.");
