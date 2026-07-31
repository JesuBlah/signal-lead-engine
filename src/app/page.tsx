import { Suspense } from "react";
import { getCompanies, getNiches } from "@/lib/data";
import DashboardClient from "@/components/DashboardClient";
import DashboardSkeleton from "@/components/DashboardSkeleton";
import StatsRow from "@/components/StatsRow";

async function DashboardContent() {
  const companies = getCompanies();
  const niches = getNiches();

  return (
    <div className="flex flex-col gap-6">
      <StatsRow companies={companies} />
      <DashboardClient companies={companies} niches={niches} />
    </div>
  );
}

export default function Home() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Advertiser Signal Dashboard</h1>
        <p className="mt-1 text-sm text-muted">
          Verified live advertisers, scored by ad-tracking gaps and site quality.
        </p>
      </div>

      <Suspense fallback={<DashboardSkeleton />}>
        <DashboardContent />
      </Suspense>
    </div>
  );
}
