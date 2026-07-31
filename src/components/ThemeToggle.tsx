"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export default function ThemeToggle() {
  // null = "don't know yet" (server render + first client render must match).
  // Real value is read from the DOM after mount, once client-only APIs
  // (document, localStorage) are safe to touch.
  const [dark, setDark] = useState<boolean | null>(null);

  useEffect(() => {
    // Syncing React state with external DOM/localStorage state that isn't
    // available during SSR — the documented exception to this rule.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }

  return (
    <button
      onClick={toggle}
      aria-label="Toggle dark mode"
      className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-surface text-foreground transition hover:opacity-80"
    >
      {dark === null ? (
        <span className="block h-4 w-4" aria-hidden="true" />
      ) : dark ? (
        <Sun size={16} />
      ) : (
        <Moon size={16} />
      )}
    </button>
  );
}
