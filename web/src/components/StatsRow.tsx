import { Building2, AlertTriangle, LineChart, Fingerprint } from "lucide-react";
import type { Company } from "@/lib/types";

function StatCard({
  icon: Icon,
  label,
  value,
  tint,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  tint: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-border bg-surface p-4">
      <span
        className="flex h-10 w-10 items-center justify-center rounded-xl"
        style={{ backgroundColor: `${tint}1a`, color: tint }}
      >
        <Icon size={18} />
      </span>
      <div>
        <p className="text-xl font-bold leading-none">{value}</p>
        <p className="text-xs text-muted">{label}</p>
      </div>
    </div>
  );
}

export default function StatsRow({ companies }: { companies: Company[] }) {
  const total = companies.length;
  const weakSites = companies.filter((c) => c.segment.startsWith("A")).length;
  const noConvTracking = companies.filter((c) => !c.convTracking).length;
  const noMetaPixel = companies.filter((c) => !c.metaPixel).length;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <StatCard icon={Building2} label="Verified companies" value={total} tint="#4f46e5" />
      <StatCard icon={AlertTriangle} label="Weak-site (segment A)" value={weakSites} tint="#dc2626" />
      <StatCard icon={LineChart} label="Missing conv. tracking" value={noConvTracking} tint="#d97706" />
      <StatCard icon={Fingerprint} label="Missing Meta Pixel" value={noMetaPixel} tint="#16a34a" />
    </div>
  );
}
