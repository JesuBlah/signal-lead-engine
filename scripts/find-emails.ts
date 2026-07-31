/**
 * Bulk email finder.
 *
 * Reads data/HOTLIST-verified.csv, scrapes each company's website for a
 * contact email + phone number, and writes results into data/emails.json
 * (the same cache the web app's "Find email" button uses). Skips domains
 * that already have a cached result unless --force is passed.
 *
 * Usage:
 *   npm run find-emails                 # scan every domain missing an email
 *   npm run find-emails -- --verified   # only google_verified_live=True rows
 *   npm run find-emails -- --force      # re-scan even if already cached
 *   npm run find-emails -- --limit 20   # cap how many domains to scan
 *   npm run find-emails -- --domain foo.fi   # scan a single domain
 */
import fs from "fs";
import path from "path";
import Papa from "papaparse";
import { scrapeDomainForContacts } from "../src/lib/emailFinder";

const DATA_DIR = path.join(process.cwd(), "data");
const CSV_PATH = path.join(DATA_DIR, "HOTLIST-verified.csv");
const STORE_PATH = path.join(DATA_DIR, "emails.json");

type Row = Record<string, string>;
type EmailRecord = {
  domain: string;
  emails: string[];
  phone?: string;
  source: "csv" | "scrape";
  scrapedAt?: string;
  pagesChecked?: string[];
  error?: string;
};

function parseArgs() {
  const args = process.argv.slice(2);
  return {
    force: args.includes("--force"),
    verifiedOnly: args.includes("--verified"),
    limit: (() => {
      const i = args.indexOf("--limit");
      return i >= 0 ? Number(args[i + 1]) : Infinity;
    })(),
    onlyDomain: (() => {
      const i = args.indexOf("--domain");
      return i >= 0 ? args[i + 1] : null;
    })(),
    concurrency: (() => {
      const i = args.indexOf("--concurrency");
      return i >= 0 ? Number(args[i + 1]) : 4;
    })(),
  };
}

function readStore(): Record<string, EmailRecord> {
  try {
    return JSON.parse(fs.readFileSync(STORE_PATH, "utf-8"));
  } catch {
    return {};
  }
}

function writeStore(store: Record<string, EmailRecord>) {
  fs.mkdirSync(path.dirname(STORE_PATH), { recursive: true });
  fs.writeFileSync(STORE_PATH, JSON.stringify(store, null, 2), "utf-8");
}

async function runPool<T>(
  items: T[],
  concurrency: number,
  worker: (item: T, index: number) => Promise<void>
) {
  let cursor = 0;
  async function next(): Promise<void> {
    const i = cursor++;
    if (i >= items.length) return;
    await worker(items[i], i);
    return next();
  }
  await Promise.all(Array.from({ length: concurrency }, () => next()));
}

async function main() {
  const opts = parseArgs();
  const raw = fs.readFileSync(CSV_PATH, "utf-8");
  const parsed = Papa.parse<Row>(raw, { header: true, skipEmptyLines: true });

  let rows = parsed.data.filter((r) => r.domain && r.domain.trim());
  if (opts.onlyDomain) {
    rows = rows.filter((r) => r.domain.trim() === opts.onlyDomain);
  }
  if (opts.verifiedOnly) {
    rows = rows.filter(
      (r) => (r.google_verified_live ?? "").trim().toLowerCase() === "true"
    );
  }

  const store = readStore();

  let targets = rows.filter((r) => {
    const domain = r.domain.trim();
    const alreadyHasCsvEmail = (r.email ?? "").trim().length > 0;
    const cached = store[domain];
    if (opts.force) return true;
    if (alreadyHasCsvEmail) return false;
    if (cached && cached.emails.length > 0) return false;
    return true;
  });

  if (Number.isFinite(opts.limit)) {
    targets = targets.slice(0, opts.limit);
  }

  console.log(
    `Scanning ${targets.length} domain(s) (of ${rows.length} total rows)...`
  );

  let done = 0;
  let foundCount = 0;

  await runPool(targets, opts.concurrency, async (row) => {
    const domain = row.domain.trim();
    const result = await scrapeDomainForContacts(domain);
    store[domain] = {
      domain,
      emails: result.emails,
      phone: result.phone,
      source: "scrape",
      scrapedAt: new Date().toISOString(),
      pagesChecked: result.pagesChecked,
      error: result.error,
    };
    done++;
    if (result.emails.length > 0) {
      foundCount++;
      console.log(`[${done}/${targets.length}] ${domain} -> ${result.emails[0]}`);
    } else {
      console.log(`[${done}/${targets.length}] ${domain} -> (none) ${result.error ?? ""}`);
    }
    // Persist incrementally so a long run can be interrupted safely.
    writeStore(store);
  });

  console.log(`\nDone. Found emails for ${foundCount}/${targets.length} scanned domains.`);
  console.log(`Results saved to ${STORE_PATH}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
