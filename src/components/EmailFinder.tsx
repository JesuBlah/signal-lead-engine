"use client";

import { useState } from "react";
import { Mail, Phone, Loader2, Search, CheckCircle2, XCircle } from "lucide-react";

interface Props {
  domain: string;
  initialEmail?: string;
  initialPhone?: string;
}

interface ScrapeResponse {
  domain: string;
  emails: string[];
  phone?: string;
  source?: "csv" | "scrape";
  scrapedAt?: string | null;
  error?: string;
}

export default function EmailFinder({ domain, initialEmail, initialPhone }: Props) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScrapeResponse | null>(
    initialEmail
      ? { domain, emails: [initialEmail], phone: initialPhone, source: "csv" }
      : null
  );
  const [error, setError] = useState<string | null>(null);

  async function findEmail() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/find-email/${encodeURIComponent(domain)}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const data: ScrapeResponse = await res.json();
      setResult(data);
    } catch {
      setError("Couldn't reach that website. It may be down or blocking bots.");
    } finally {
      setLoading(false);
    }
  }

  const hasEmails = result && result.emails && result.emails.length > 0;

  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-semibold">
          <Mail size={16} className="text-brand" /> Contact finder
        </h3>
        <button
          onClick={findEmail}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-brand-foreground transition hover:opacity-90 disabled:opacity-60"
        >
          {loading ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
          {loading ? "Scanning site…" : hasEmails ? "Re-scan site" : "Find email"}
        </button>
      </div>

      {!result && !loading && !error && (
        <p className="text-sm text-muted">
          No email on file yet. Click &ldquo;Find email&rdquo; to scan {domain}&rsquo;s homepage and
          contact page for a public email address.
        </p>
      )}

      {error && (
        <p className="flex items-center gap-1.5 text-sm text-danger">
          <XCircle size={14} /> {error}
        </p>
      )}

      {result && (
        <div className="flex flex-col gap-2">
          {hasEmails ? (
            <>
              {result.emails.map((email) => (
                <a
                  key={email}
                  href={`mailto:${email}`}
                  className="flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm font-medium text-success"
                >
                  <CheckCircle2 size={14} /> {email}
                </a>
              ))}
            </>
          ) : (
            <p className="flex items-center gap-1.5 text-sm text-muted">
              <XCircle size={14} className="text-danger" />
              {result.error ?? "No public email found on the scanned pages."}
            </p>
          )}

          {result.phone && (
            <p className="flex items-center gap-1.5 text-sm text-foreground">
              <Phone size={14} className="text-brand" /> {result.phone}
            </p>
          )}

          {result.source === "scrape" && (
            <p className="mt-1 text-xs text-muted">
              Scraped from the company&rsquo;s public website. Verify before outreach.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
