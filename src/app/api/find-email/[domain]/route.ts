import { NextRequest, NextResponse } from "next/server";
import { scrapeDomainForContacts } from "@/lib/emailFinder";
import { getEmailRecord, saveEmailRecord } from "@/lib/emailStore";

export const dynamic = "force-dynamic";
// Scraping a site can be slow; without this Vercel kills the function after
// the platform default (10s on Hobby), which is what was causing "couldn't
// reach that website" even for sites that just respond a bit slowly.
export const maxDuration = 60;

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ domain: string }> }
) {
  const { domain } = await params;
  const record = getEmailRecord(domain);
  if (!record) {
    return NextResponse.json({ domain, emails: [], scrapedAt: null });
  }
  return NextResponse.json(record);
}

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ domain: string }> }
) {
  const { domain } = await params;
  if (!domain) {
    return NextResponse.json({ error: "Missing domain" }, { status: 400 });
  }

  const result = await scrapeDomainForContacts(domain);

  const record = saveEmailRecord({
    domain: result.domain,
    emails: result.emails,
    phone: result.phone,
    source: "scrape",
    scrapedAt: new Date().toISOString(),
    pagesChecked: result.pagesChecked,
    error: result.error,
  });

  return NextResponse.json(record);
}