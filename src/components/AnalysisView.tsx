"use client";

import { useState } from "react";

export default function AnalysisView({
  htmlFi,
  htmlEn,
}: {
  htmlFi: string | null;
  htmlEn: string | null;
}) {
  const [lang, setLang] = useState<"fi" | "en">("fi");

  if (!htmlFi && !htmlEn) {
    return (
      <p className="text-sm text-muted">
        No AI analysis has been generated for this company yet.
      </p>
    );
  }

  const html = lang === "en" ? htmlEn ?? htmlFi : htmlFi ?? htmlEn;
  const showToggle = Boolean(htmlFi && htmlEn);

  return (
    <div>
      {showToggle && (
        <div className="mb-4 inline-flex rounded-lg border border-border p-0.5 text-xs font-medium">
          <button
            type="button"
            onClick={() => setLang("fi")}
            className={`rounded-md px-2.5 py-1 transition ${
              lang === "fi"
                ? "bg-brand text-white"
                : "text-muted hover:text-foreground"
            }`}
          >
            Suomi
          </button>
          <button
            type="button"
            onClick={() => setLang("en")}
            className={`rounded-md px-2.5 py-1 transition ${
              lang === "en"
                ? "bg-brand text-white"
                : "text-muted hover:text-foreground"
            }`}
          >
            English
          </button>
        </div>
      )}
      <div className="markdown-body" dangerouslySetInnerHTML={{ __html: html ?? "" }} />
    </div>
  );
}