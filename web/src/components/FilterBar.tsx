"use client";

import { Search } from "lucide-react";
import clsx from "clsx";
import type { BooleanFilter, SegmentFilter } from "@/lib/types";

interface FilterBarProps {
  query: string;
  onQueryChange: (v: string) => void;
  niche: string;
  onNicheChange: (v: string) => void;
  niches: string[];
  segment: SegmentFilter;
  onSegmentChange: (v: SegmentFilter) => void;
  googleAds: BooleanFilter;
  onGoogleAdsChange: (v: BooleanFilter) => void;
  convTracking: BooleanFilter;
  onConvTrackingChange: (v: BooleanFilter) => void;
  metaPixel: BooleanFilter;
  onMetaPixelChange: (v: BooleanFilter) => void;
  resultCount: number;
  onReset: () => void;
}

function ToggleGroup<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="inline-flex rounded-lg border border-border bg-background p-0.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={clsx(
            "rounded-md px-2.5 py-1 text-xs font-medium transition",
            value === opt.value
              ? "bg-brand text-brand-foreground"
              : "text-muted hover:text-foreground"
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export default function FilterBar(props: FilterBarProps) {
  const yesNo: { value: BooleanFilter; label: string }[] = [
    { value: "all", label: "All" },
    { value: "yes", label: "Yes" },
    { value: "no", label: "No" },
  ];

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border bg-surface p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search
            size={16}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
          />
          <input
            value={props.query}
            onChange={(e) => props.onQueryChange(e.target.value)}
            placeholder="Search company, domain, or city…"
            className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm outline-none ring-brand/40 placeholder:text-muted focus:ring-2"
          />
        </div>

        <select
          value={props.niche}
          onChange={(e) => props.onNicheChange(e.target.value)}
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none ring-brand/40 focus:ring-2"
        >
          <option value="all">All niches</option>
          {props.niches.map((n) => (
            <option key={n} value={n} className="capitalize">
              {n}
            </option>
          ))}
        </select>

        <ToggleGroup
          value={props.segment}
          onChange={props.onSegmentChange}
          options={[
            { value: "all", label: "All segments" },
            { value: "A", label: "A · Weak site" },
            { value: "B", label: "B · No tracking" },
            { value: "C", label: "C · Solid" },
          ]}
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-border pt-4">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted">Google Ads</span>
          <ToggleGroup value={props.googleAds} onChange={props.onGoogleAdsChange} options={yesNo} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted">Conv. tracking</span>
          <ToggleGroup
            value={props.convTracking}
            onChange={props.onConvTrackingChange}
            options={yesNo}
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted">Meta Pixel</span>
          <ToggleGroup value={props.metaPixel} onChange={props.onMetaPixelChange} options={yesNo} />
        </div>

        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-muted">{props.resultCount} results</span>
          <button
            onClick={props.onReset}
            className="text-xs font-medium text-brand hover:underline"
          >
            Reset filters
          </button>
        </div>
      </div>
    </div>
  );
}
