import Link from "next/link";
import { Building2, MapPin, FileText, Mail } from "lucide-react";
import type { Company } from "@/lib/types";
import { SegmentBadge, ScoreBadge, StatusPill } from "./StatusBadge";
import { Target, LineChart, Fingerprint } from "lucide-react";

export default function CompanyCard({ company }: { company: Company }) {
  return (
    <Link
      href={`/company/${encodeURIComponent(company.domain)}`}
      className="group flex flex-col gap-4 rounded-2xl border border-border bg-surface p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand/10 text-brand">
            <Building2 size={18} />
          </span>
          <div className="min-w-0">
            <h3 className="truncate font-semibold leading-tight group-hover:text-brand">
              {company.company}
            </h3>
            <p className="truncate text-xs text-muted">{company.domain}</p>
          </div>
        </div>
        <ScoreBadge score={company.score} />
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
        {company.niche && (
          <span className="rounded-full border border-border px-2 py-0.5 capitalize">
            {company.niche}
          </span>
        )}
        {company.city && (
          <span className="flex items-center gap-1">
            <MapPin size={12} /> {company.city}
          </span>
        )}
        <SegmentBadge segment={company.segment} />
      </div>

      <div className="flex flex-wrap gap-2">
        <StatusPill icon={Target} label="Ads" active={company.googleAds} />
        <StatusPill icon={LineChart} label="Conv." active={company.convTracking} />
        <StatusPill icon={Fingerprint} label="Pixel" active={company.metaPixel} />
      </div>

      <div className="mt-auto flex items-center justify-between border-t border-border pt-3 text-xs text-muted">
        <span className="flex items-center gap-1">
          <FileText size={12} />
          {company.hasAnalysis ? "AI analysis ready" : "No analysis yet"}
        </span>
        {company.email ? (
          <span className="flex items-center gap-1 text-success">
            <Mail size={12} /> email found
          </span>
        ) : (
          <span className="flex items-center gap-1">
            <Mail size={12} /> no email
          </span>
        )}
      </div>
    </Link>
  );
}
