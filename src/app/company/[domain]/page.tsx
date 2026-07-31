import { notFound } from "next/navigation";
import Link from "next/link";
import { marked } from "marked";
import {
  ArrowLeft,
  Building2,
  MapPin,
  Layers,
  Users,
  Wrench,
  BadgeCheck,
  Target,
  LineChart,
  Fingerprint,
  AlertTriangle,
  FileText,
} from "lucide-react";
import { getCompanies, getCompanyByDomain, getAnalysisMarkdown } from "@/lib/data";
import { SegmentBadge, ScoreBadge, StatusPill } from "@/components/StatusBadge";
import AnalysisView from "@/components/AnalysisView";
import EmailFinder from "@/components/EmailFinder";

export function generateStaticParams() {
  return getCompanies().map((c) => ({ domain: c.domain }));
}

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon size={14} className="shrink-0 text-muted" />
      <span className="text-muted">{label}:</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ domain: string }>;
}) {
  const { domain: rawDomain } = await params;
  const domain = decodeURIComponent(rawDomain);
  const company = getCompanyByDomain(domain);

  if (!company) notFound();

  const markdownFi = getAnalysisMarkdown(domain, "fi");
  const markdownEn = getAnalysisMarkdown(domain, "en");
  const htmlFi = markdownFi ? await marked.parse(markdownFi) : null;
  const htmlEn = markdownEn ? await marked.parse(markdownEn) : null;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <Link
        href="/"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted transition hover:text-foreground"
      >
        <ArrowLeft size={14} /> Back to dashboard
      </Link>

      <div className="mb-6 flex flex-col gap-4 rounded-2xl border border-border bg-surface p-6 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand/10 text-brand">
            <Building2 size={22} />
          </span>
          <div>
            <h1 className="text-xl font-bold">{company.company}</h1>
            <p className="text-sm text-muted">{company.domain}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <SegmentBadge segment={company.segment} />
              {company.niche && (
                <span className="rounded-full border border-border px-2.5 py-0.5 text-xs capitalize">
                  {company.niche}
                </span>
              )}
              {company.googleVerifiedLive && (
                <span className="inline-flex items-center gap-1 rounded-full border border-success/30 bg-success/10 px-2.5 py-0.5 text-xs font-medium text-success">
                  <BadgeCheck size={12} /> Google-verified live advertiser
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:flex-col sm:items-end">
          <span className="text-xs text-muted">Lead score</span>
          <ScoreBadge score={company.score} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <section className="rounded-2xl border border-border bg-surface p-6">
            <h2 className="mb-4 flex items-center gap-2 font-semibold">
              <Layers size={16} className="text-brand" /> Signal status
            </h2>
            <div className="flex flex-wrap gap-2">
              <StatusPill icon={Target} label="Google Ads" active={company.googleAds} />
              <StatusPill icon={LineChart} label="Conversion tracking" active={company.convTracking} />
              <StatusPill icon={Fingerprint} label="Meta Pixel" active={company.metaPixel} />
            </div>
            {company.issueFlags.length > 0 && (
              <div className="mt-4 flex flex-col gap-2 border-t border-border pt-4">
                <p className="flex items-center gap-1.5 text-sm font-medium text-warning">
                  <AlertTriangle size={14} /> {company.qualityIssues} quality issue
                  {company.qualityIssues === 1 ? "" : "s"} detected
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {company.issueFlags.map((flag) => (
                    <span
                      key={flag}
                      className="rounded-md border border-warning/30 bg-warning/10 px-2 py-0.5 text-xs text-warning"
                    >
                      {flag.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-border bg-surface p-6">
            <h2 className="mb-4 flex items-center gap-2 font-semibold">
              <FileText size={16} className="text-brand" /> AI findings &amp; recommendations
            </h2>
            <AnalysisView htmlFi={htmlFi} htmlEn={htmlEn} />
          </section>
        </div>

        <div className="flex flex-col gap-6">
          <section className="rounded-2xl border border-border bg-surface p-6">
            <h2 className="mb-4 font-semibold">Company info</h2>
            <div className="flex flex-col gap-3">
              <InfoRow icon={MapPin} label="City" value={company.city} />
              <InfoRow icon={Users} label="Employees" value={company.employees} />
              <InfoRow icon={Wrench} label="Platform" value={company.platform} />
              <InfoRow
                icon={BadgeCheck}
                label="Advertiser name"
                value={company.googleAdvertiserName}
              />
              <InfoRow icon={Target} label="Ads status" value={company.adsStatus} />
              <InfoRow
                icon={Layers}
                label="Niche confidence"
                value={
                  company.nicheConfidence
                    ? `${Math.round(company.nicheConfidence * 100)}%`
                    : ""
                }
              />
            </div>
          </section>

          <EmailFinder
            domain={company.domain}
            initialEmail={company.email || undefined}
            initialPhone={company.phone || undefined}
          />
        </div>
      </div>
    </div>
  );
}
