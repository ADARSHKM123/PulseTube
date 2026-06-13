import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Menu, Moon, Play, Sun } from "lucide-react";
import clsx from "clsx";
import Button from "../ui/Button.jsx";
import { useStatus } from "../../context/StatusContext.jsx";
import { relTime } from "../../lib/format.js";

const TITLES = {
  "/": "Live Feed",
  "/table": "Trends Table",
  "/keywords": "Tracked Keywords",
  "/system": "System & Pipeline",
};

function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("pt-theme", next ? "dark" : "light");
    } catch {
      /* private mode */
    }
  };
  return [dark, toggle];
}

export default function Topbar({ onMenuClick }) {
  const { pathname } = useLocation();
  const { status, triggerRun } = useStatus();
  const [dark, toggleTheme] = useTheme();
  // Re-render every 30s so "next run in …" stays fresh without refetching
  const [, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 30_000);
    return () => clearInterval(t);
  }, []);

  const running = status?.pipeline_running;
  const quota = status?.quota;
  const quotaPct = quota ? Math.min(100, Math.round((quota.used / quota.budget) * 100)) : 0;

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-line bg-bg/85 px-4 backdrop-blur sm:px-6">
      <button
        onClick={onMenuClick}
        className="rounded-lg p-2 text-muted hover:bg-raised hover:text-fg md:hidden"
        aria-label="Open navigation"
      >
        <Menu size={19} />
      </button>

      <h1 className="truncate font-display text-lg font-bold tracking-tight">{TITLES[pathname] || "PulseTube"}</h1>

      <div className="ml-auto flex items-center gap-2.5 sm:gap-4">
        {/* Pipeline state pill */}
        <div className="hidden items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-semibold sm:flex">
          <span
            className={clsx(
              "h-2 w-2 rounded-full",
              running ? "pt-pulse bg-accent" : "bg-success"
            )}
          />
          {running ? (
            <span className="text-accent">Ingestion running…</span>
          ) : (
            <span className="text-muted">
              Next run {status?.next_run_at ? relTime(status.next_run_at) : "—"}
            </span>
          )}
        </div>

        {/* Quota meter */}
        {quota && (
          <div
            className="hidden flex-col gap-1 lg:flex"
            title={`YouTube API quota: ${quota.used} / ${quota.budget} units used today (resets midnight PT)`}
          >
            <div className="flex items-center justify-between text-[10px] font-semibold text-muted">
              <span>API quota</span>
              <span className="num">{quotaPct}%</span>
            </div>
            <div className="h-1.5 w-28 overflow-hidden rounded-full bg-raised">
              <div
                className={clsx(
                  "h-full rounded-full transition-all",
                  quotaPct > 85 ? "bg-danger" : quotaPct > 60 ? "bg-warning" : "bg-accent"
                )}
                style={{ width: `${quotaPct}%` }}
              />
            </div>
          </div>
        )}

        <Button size="sm" variant="primary" onClick={triggerRun} disabled={running} loading={running}>
          {!running && <Play size={13} />}
          {running ? "Running" : "Run now"}
        </Button>

        <button
          onClick={toggleTheme}
          className="rounded-lg p-2 text-muted transition-colors hover:bg-raised hover:text-fg"
          aria-label="Toggle theme"
        >
          {dark ? <Sun size={17} /> : <Moon size={17} />}
        </button>
      </div>
    </header>
  );
}
