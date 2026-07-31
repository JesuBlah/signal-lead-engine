"use client";

import { useMemo, useState } from "react";
import { SearchX } from "lucide-react";
import type { BooleanFilter, Company, SegmentFilter } from "@/lib/types";
import FilterBar from "./FilterBar";
import CompanyCard from "./CompanyCard";
import ExportCsvButton from "./ExportCsvButton";

function matchesBool(filter: BooleanFilter, value: boolean) {
  if (filter === "all") return true;
  return filter === "yes" ? value : !value;
}

export default function DashboardClient({
  companies,
  niches,
}: {
  companies: Company[];
  niches: string[];
}) {
  const [query, setQuery] = useState("");
  const [niche, setNiche] = useState("all");
  const [segment, setSegment] = useState<SegmentFilter>("all");
  const [googleAds, setGoogleAds] = useState<BooleanFilter>("all");
  const [convTracking, setConvTracking] = useState<BooleanFilter>("all");
  const [metaPixel, setMetaPixel] = useState<BooleanFilter>("all");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return companies
      .filter((c) => {
        if (q) {
          const haystack = `${c.company} ${c.domain} ${c.city}`.toLowerCase();
          if (!haystack.includes(q)) return false;
        }
        if (niche !== "all" && c.niche !== niche) return false;
        if (segment !== "all" && c.segment.split("_")[0] !== segment) return false;
        if (!matchesBool(googleAds, c.googleAds)) return false;
        if (!matchesBool(convTracking, c.convTracking)) return false;
        if (!matchesBool(metaPixel, c.metaPixel)) return false;
        return true;
      })
      .sort((a, b) => b.score - a.score);
  }, [companies, query, niche, segment, googleAds, convTracking, metaPixel]);

  function resetFilters() {
    setQuery("");
    setNiche("all");
    setSegment("all");
    setGoogleAds("all");
    setConvTracking("all");
    setMetaPixel("all");
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex justify-end">
        <ExportCsvButton companies={filtered} />
      </div>

      <FilterBar
        query={query}
        onQueryChange={setQuery}
        niche={niche}
        onNicheChange={setNiche}
        niches={niches}
        segment={segment}
        onSegmentChange={setSegment}
        googleAds={googleAds}
        onGoogleAdsChange={setGoogleAds}
        convTracking={convTracking}
        onConvTrackingChange={setConvTracking}
        metaPixel={metaPixel}
        onMetaPixelChange={setMetaPixel}
        resultCount={filtered.length}
        onReset={resetFilters}
      />

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border bg-surface py-20 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand/10 text-brand">
            <SearchX size={22} />
          </span>
          <p className="font-medium">No companies match your filters</p>
          <p className="max-w-sm text-sm text-muted">
            Try widening your search, clearing a filter, or resetting everything below.
          </p>
          <button
            onClick={resetFilters}
            className="mt-1 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-foreground hover:opacity-90"
          >
            Reset filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((c) => (
            <CompanyCard key={c.domain} company={c} />
          ))}
        </div>
      )}
    </div>
  );
}
