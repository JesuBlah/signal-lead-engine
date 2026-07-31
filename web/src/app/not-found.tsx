import Link from "next/link";
import { SearchX } from "lucide-react";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center gap-4 px-4 py-24 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-full bg-brand/10 text-brand">
        <SearchX size={26} />
      </span>
      <h1 className="text-xl font-bold">Company not found</h1>
      <p className="text-sm text-muted">
        We couldn&rsquo;t find that company in the verified advertiser list.
      </p>
      <Link
        href="/"
        className="mt-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-foreground hover:opacity-90"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
