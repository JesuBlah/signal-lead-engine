import "server-only";
import fs from "fs";
import path from "path";
import Papa from "papaparse";
import type { Company } from "./types";
import { getEmailRecord } from "./emailStore";

const DATA_DIR = path.join(process.cwd(), "data");
const ANALYSES_DIR = path.join(process.cwd(), "analyses");
const CSV_PATH = path.join(DATA_DIR, "HOTLIST-verified.csv");

function toBool(value: string | undefined): boolean {
  return (value ?? "").trim().toLowerCase() === "true";
}

function toNum(value: string | undefined): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

let analysisDomainsCache: Set<string> | null = null;

function getAnalysisDomains(): Set<string> {
  if (analysisDomainsCache) return analysisDomainsCache;
  let files: string[] = [];
  try {
    files = fs.readdirSync(ANALYSES_DIR);
  } catch {
    files = [];
  }
  analysisDomainsCache = new Set(
    files
      .filter((f) => f.endsWith(".md") && !f.endsWith(".en.md"))
      .map((f) => f.replace(/\.md$/, ""))
  );
  return analysisDomainsCache;
}

let companiesCache: Company[] | null = null;

/** Parse the HOTLIST-verified.csv into typed Company records. Cached in memory per server process. */
export function getCompanies(): Company[] {
  if (companiesCache) return companiesCache;

  const raw = fs.readFileSync(CSV_PATH, "utf-8");
  const parsed = Papa.parse<Record<string, string>>(raw, {
    header: true,
    skipEmptyLines: true,
  });

  const analysisDomains = getAnalysisDomains();

  const companies: Company[] = parsed.data
    .filter((row) => row.domain && row.domain.trim().length > 0)
    .map((row) => {
      const domain = row.domain.trim();
      const emailRecord = getEmailRecord(domain);
      const csvEmail = (row.email ?? "").trim();
      const bestEmail =
        csvEmail || emailRecord?.emails?.[0] || "";

      return {
        score: toNum(row.score),
        run: row.run ?? "",
        niche: row.niche ?? "",
        nicheSource: row.niche_source ?? "",
        nicheConfidence: toNum(row.niche_confidence),
        company: row.company?.trim() || domain,
        domain,
        segment: row.segment ?? "",
        revenueEur: row.revenue_eur ?? "",
        employees: row.employees ?? "",
        yTunnus: row.y_tunnus ?? "",
        googleAds: toBool(row.google_ads),
        convTracking: toBool(row.conv_tracking),
        metaPixel: toBool(row.meta_pixel),
        qualityIssues: toNum(row.quality_issues),
        issueFlags: (row.issue_flags ?? "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        platform: row.platform ?? "",
        email: bestEmail,
        phone: row.phone?.trim() || emailRecord?.phone || "",
        city: row.city ?? "",
        googleVerifiedLive: toBool(row.google_verified_live),
        googleAdvertiserName: row.google_advertiser_name ?? "",
        adsStatus: row.ads_status ?? "",
        hasAnalysis: analysisDomains.has(domain),
      };
    });

  companiesCache = companies;
  return companies;
}

export function getCompanyByDomain(domain: string): Company | undefined {
  return getCompanies().find((c) => c.domain === domain);
}

export function getAnalysisMarkdown(
  domain: string,
  lang: "fi" | "en" = "fi"
): string | null {
  const suffix = lang === "en" ? ".en.md" : ".md";
  const filePath = path.join(ANALYSES_DIR, `${domain}${suffix}`);
  try {
    return fs.readFileSync(filePath, "utf-8");
  } catch {
    return null;
  }
}

export function getNiches(): string[] {
  const set = new Set<string>();
  for (const c of getCompanies()) {
    if (c.niche) set.add(c.niche);
  }
  return Array.from(set).sort();
}

/** Segment letter, e.g. "A_ads_weak_site" -> "A" */
export function segmentLetter(segment: string): string {
  return segment.split("_")[0] || "?";
}
