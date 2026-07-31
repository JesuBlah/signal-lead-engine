import { LucideIcon, Check, X } from "lucide-react";
import clsx from "clsx";

export function StatusPill({
  icon: Icon,
  label,
  active,
}: {
  icon: LucideIcon;
  label: string;
  active: boolean;
}) {
  return (
    <span
      title={`${label}: ${active ? "detected" : "not detected"}`}
      className={clsx(
        "inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium",
        active
          ? "border-success/30 bg-success/10 text-success"
          : "border-danger/30 bg-danger/10 text-danger"
      )}
    >
      <Icon size={12} />
      {label}
      {active ? <Check size={12} /> : <X size={12} />}
    </span>
  );
}

export function SegmentBadge({ segment }: { segment: string }) {
  const letter = segment.split("_")[0] || "?";
  const styles: Record<string, string> = {
    A: "bg-danger/10 text-danger border-danger/30",
    B: "bg-warning/10 text-warning border-warning/30",
    C: "bg-success/10 text-success border-success/30",
  };
  const labels: Record<string, string> = {
    A: "Weak site",
    B: "No tracking",
    C: "Solid site",
  };
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        styles[letter] ?? "border-border bg-surface text-muted"
      )}
      title={labels[letter] ?? segment}
    >
      Segment {letter}
    </span>
  );
}

export function ScoreBadge({ score }: { score: number }) {
  return (
    <span className="inline-flex items-center rounded-full bg-brand px-2.5 py-0.5 text-xs font-bold text-brand-foreground">
      {score}
    </span>
  );
}
