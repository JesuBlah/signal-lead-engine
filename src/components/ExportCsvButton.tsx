"use client";

import { useState } from "react";
import Papa from "papaparse";
import { Download, X } from "lucide-react";
import type { Company } from "@/lib/types";

interface ColumnDef {
  key: string;
  label: string;
  get: (c: Company) => string | number;
}

const COLUMNS: ColumnDef[] = [
  { key: "company", label: "Company name", get: (c) => c.company },
  { key: "domain", label: "Domain", get: (c) => c.domain },
  { key: "city", label: "City", get: (c) => c.city },
  { key: "niche", label: "Niche", get: (c) => c.niche },
  { key: "segment", label: "Segment", get: (c) => c.segment.split("_")[0] || "" },
  { key: "score", label: "Lead score", get: (c) => c.score },
  { key: "googleAds", label: "Google Ads", get: (c) => (c.googleAds ? "yes" : "no") },
  { key: "convTracking", label: "Conversion tracking", get: (c) => (c.convTracking ? "yes" : "no") },
  { key: "metaPixel", label: "Meta Pixel", get: (c) => (c.metaPixel ? "yes" : "no") },
  { key: "qualityIssues", label: "Quality issue count", get: (c) => c.qualityIssues },
  { key: "issueFlags", label: "Quality issue flags", get: (c) => c.issueFlags.join("; ") },
  { key: "platform", label: "Platform", get: (c) => c.platform },
  { key: "email", label: "Email", get: (c) => c.email },
  { key: "phone", label: "Phone", get: (c) => c.phone },
  { key: "googleVerifiedLive", label: "Google-verified live advertiser", get: (c) => (c.googleVerifiedLive ? "yes" : "no") },
  { key: "googleAdvertiserName", label: "Google advertiser name", get: (c) => c.googleAdvertiserName },
  { key: "adsStatus", label: "Ads status", get: (c) => c.adsStatus },
  { key: "revenueEur", label: "Revenue (EUR)", get: (c) => c.revenueEur },
  { key: "employees", label: "Employees", get: (c) => c.employees },
];

const DEFAULT_SELECTED = new Set([
  "company",
  "domain",
  "city",
  "niche",
  "segment",
  "score",
  "email",
  "phone",
]);

export default function ExportCsvButton({ companies }: { companies: Company[] }) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set(DEFAULT_SELECTED));

  function toggle(key: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function selectAll() {
    setSelected(new Set(COLUMNS.map((c) => c.key)));
  }

  function selectNone() {
    setSelected(new Set());
  }

  function download() {
    const cols = COLUMNS.filter((c) => selected.has(c.key));
    if (cols.length === 0) return;

    const rows = companies.map((c) => {
      const row: Record<string, string | number> = {};
      for (const col of cols) row[col.label] = col.get(c);
      return row;
    });

    const csv = Papa.unparse(rows);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const date = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `signal-lead-engine-export-${date}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setOpen(false);
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 py-2 text-xs font-medium transition hover:bg-surface"
      >
        <Download size={14} /> Export CSV
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="flex max-h-[85vh] w-full max-w-md flex-col rounded-2xl border border-border bg-surface p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold">Export to CSV</h2>
              <button
                onClick={() => setOpen(false)}
                className="rounded-md p-1 text-muted hover:bg-background hover:text-foreground"
              >
                <X size={16} />
              </button>
            </div>

            <p className="mb-3 text-xs text-muted">
              Choose which columns to include. Exports the {companies.length}{" "}
              compan{companies.length === 1 ? "y" : "ies"} matching your current filters.
            </p>

            <div className="mb-3 flex gap-3 text-xs font-medium text-brand">
              <button onClick={selectAll} className="hover:underline">
                Select all
              </button>
              <button onClick={selectNone} className="hover:underline">
                Select none
              </button>
            </div>

            <div className="flex-1 overflow-y-auto rounded-lg border border-border">
              {COLUMNS.map((col) => (
                <label
                  key={col.key}
                  className="flex cursor-pointer items-center gap-2 border-b border-border px-3 py-2 text-sm last:border-b-0 hover:bg-background"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(col.key)}
                    onChange={() => toggle(col.key)}
                    className="accent-brand"
                  />
                  {col.label}
                </label>
              ))}
            </div>

            <button
              onClick={download}
              disabled={selected.size === 0}
              className="mt-4 flex items-center justify-center gap-1.5 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Download size={14} />
              Download CSV ({selected.size} column{selected.size === 1 ? "" : "s"})
            </button>
          </div>
        </div>
      )}
    </>
  );
}  