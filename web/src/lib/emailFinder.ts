// Framework-agnostic scraping logic (no "server-only" import so it can be
// reused both from a Next.js API route and from the standalone CLI script).

const EMAIL_REGEX =
  /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;

const PHONE_REGEX = /(\+358|0)\s?\d(?:[\s-]?\d){6,10}/g;

// File extensions and junk that regularly get false-matched as "emails"
// (e.g. filenames like logo@2x.png).
const BAD_EMAIL_PATTERNS = [
  /\.(png|jpg|jpeg|gif|svg|webp|css|js|ico)$/i,
  /^(example|test|user|name|your)@/i,
  /sentry\.io$/i,
  /wixpress\.com$/i,
  /schema\.org$/i,
  /w3\.org$/i,
];

const CANDIDATE_PATHS = [
  "",
  "/yhteystiedot",
  "/yhteystiedot/",
  "/contact",
  "/contact-us",
  "/about",
  "/about-us",
  "/ota-yhteytta",
  "/meille",
];

function cleanEmails(raw: string[], domain: string): string[] {
  const seen = new Set<string>();
  const good: string[] = [];
  const rootDomain = domain.replace(/^www\./, "");

  for (const e of raw) {
    const email = e.trim().toLowerCase().replace(/[.,;)]+$/, "");
    if (BAD_EMAIL_PATTERNS.some((re) => re.test(email))) continue;
    if (seen.has(email)) continue;
    seen.add(email);
    good.push(email);
  }

  // Prefer addresses that actually belong to the company's own domain.
  good.sort((a, b) => {
    const aOwn = a.endsWith("@" + rootDomain) ? 0 : 1;
    const bOwn = b.endsWith("@" + rootDomain) ? 0 : 1;
    return aOwn - bOwn;
  });

  return good;
}

async function fetchPage(url: string, timeoutMs = 8000): Promise<string | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      redirect: "follow",
      headers: {
        "User-Agent":
          "Mozilla/5.0 (compatible; SignalLeadEngineBot/1.0; +https://example.com/bot)",
      },
    });
    if (!res.ok) return null;
    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("text/html")) return null;
    return await res.text();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export interface ScrapeResult {
  domain: string;
  emails: string[];
  phone?: string;
  pagesChecked: string[];
  error?: string;
}

/**
 * Scrapes the homepage and a handful of common contact-page paths for a
 * domain, looking for mailto: links and plain-text email/phone patterns.
 * Checks all candidate pages in parallel.
 */
export async function scrapeDomainForContacts(
  domainInput: string
): Promise<ScrapeResult> {
  const domain = domainInput.trim().replace(/^https?:\/\//, "").replace(/\/$/, "");
  const base = `https://${domain}`;
  const pagesChecked: string[] = [];
  const foundEmails: string[] = [];
  let foundPhone: string | undefined;
  let lastError: string | undefined;

  // Fetch every candidate path in parallel instead of one-by-one. Sequential
  // checks (with an 8s timeout each) could add up to over a minute for a
  // slow site, which blew past Vercel's serverless function time limit and
  // surfaced as a false "couldn't reach that website" error even when the
  // site was actually reachable, just slow.
  const results = await Promise.all(
    CANDIDATE_PATHS.map(async (p) => {
      const url = base + p;
      const html = await fetchPage(url);
      return { url, html };
    })
  );

  for (const { url, html } of results) {
    pagesChecked.push(url);
    if (!html) {
      lastError = lastError ?? `Could not reach ${url}`;
      continue;
    }
    lastError = undefined;

    const mailtoMatches = Array.from(
      html.matchAll(/mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g)
    ).map((m) => m[1]);
    const textMatches = html.match(EMAIL_REGEX) ?? [];
    foundEmails.push(...mailtoMatches, ...textMatches);

    if (!foundPhone) {
      const phoneMatches = html.match(PHONE_REGEX);
      if (phoneMatches && phoneMatches.length > 0) {
        foundPhone = phoneMatches[0].replace(/\s+/g, " ").trim();
      }
    }
  }

  const emails = cleanEmails(foundEmails, domain);

  return {
    domain,
    emails,
    phone: foundPhone,
    pagesChecked,
    error: emails.length === 0 ? lastError ?? "No email found on scanned pages" : undefined,
  };
}