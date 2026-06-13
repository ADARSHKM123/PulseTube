import { useState } from "react";
import { ThumbsUp } from "lucide-react";
import clsx from "clsx";
import SentimentBar from "../ui/SentimentBar.jsx";
import { fmtCompact, fmtPct } from "../../lib/format.js";

const LABEL_STYLES = {
  positive: "bg-success/12 text-success border-success/25",
  negative: "bg-danger/12 text-danger border-danger/25",
  neutral: "bg-muted/12 text-muted border-line",
};

// Order matches the donut sweep; pctKey reads the aggregate distribution.
const CATEGORIES = [
  { id: "positive", label: "Positive", color: "var(--c-success)", pctKey: "positive_pct" },
  { id: "neutral", label: "Neutral", color: "var(--c-muted)", pctKey: "neutral_pct" },
  { id: "negative", label: "Negative", color: "var(--c-danger)", pctKey: "negative_pct" },
];

/** "What people think" — aggregate distribution + filterable per-comment list. */
export default function SentimentPanel({ sentiment }) {
  // Click a category to show only those comments; click it again for all.
  const [filter, setFilter] = useState("all");

  if (!sentiment || sentiment.comments_analyzed === 0) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm text-muted">
        No sentiment yet — comments may be disabled, or this video hasn't been analyzed in a run.
      </div>
    );
  }

  const comments = sentiment.sample_comments || [];
  // Counts reflect the comments actually stored/shown (so the filter chip
  // numbers always match the list length below).
  const counts = { positive: 0, neutral: 0, negative: 0 };
  comments.forEach((c) => {
    if (counts[c.label] !== undefined) counts[c.label] += 1;
  });
  const filtered = filter === "all" ? comments : comments.filter((c) => c.label === filter);

  // Conic-gradient donut — no chart lib needed for a single ring.
  let acc = 0;
  const stops = CATEGORIES.map((c) => {
    const v = sentiment[c.pctKey] || 0;
    const start = acc;
    acc += v;
    return `rgb(${c.color}) ${start}% ${acc}%`;
  }).join(", ");

  const toggle = (id) => setFilter((cur) => (cur === id ? "all" : id));

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div className="flex items-center gap-4">
        <div
          className="relative h-24 w-24 shrink-0 rounded-full"
          style={{ background: `conic-gradient(${stops})` }}
        >
          <div className="absolute inset-[10px] flex flex-col items-center justify-center rounded-full bg-surface">
            <span className="num font-display text-xl font-bold text-success">
              {fmtPct(sentiment.positive_pct, 0)}
            </span>
            <span className="text-[10px] font-medium text-muted">positive</span>
          </div>
        </div>

        {/* Clickable category filters */}
        <div className="min-w-0 flex-1 space-y-1">
          {CATEGORIES.map((c) => {
            const active = filter === c.id;
            return (
              <button
                key={c.id}
                onClick={() => toggle(c.id)}
                title={active ? "Show all comments" : `Show only ${c.label.toLowerCase()} comments`}
                className={clsx(
                  "flex w-full items-center justify-between rounded-lg border px-2 py-1 text-sm transition-colors",
                  active ? "border-primary/40 bg-primary/5" : "border-transparent hover:bg-raised"
                )}
              >
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: `rgb(${c.color})` }} />
                  {c.label}
                  <span className="text-xs text-muted">({counts[c.id]})</span>
                </span>
                <span className="num font-semibold">{fmtPct(sentiment[c.pctKey])}</span>
              </button>
            );
          })}
          <div className="border-t border-line pt-1.5 text-xs text-muted">
            {fmtCompact(sentiment.comments_analyzed)} comments analyzed · avg score{" "}
            <span className="num font-semibold text-fg">{sentiment.avg_compound?.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <SentimentBar
        positive={sentiment.positive_pct}
        neutral={sentiment.neutral_pct}
        negative={sentiment.negative_pct}
        className="px-0.5"
      />

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted">
            {filter === "all" ? "All comments" : `${filter} comments`} ({filtered.length})
          </h4>
          {filter !== "all" && (
            <button
              onClick={() => setFilter("all")}
              className="text-xs font-semibold text-primary hover:underline"
            >
              Show all
            </button>
          )}
        </div>

        <div className="space-y-2">
          {filtered.length === 0 ? (
            <div className="rounded-xl border border-line bg-raised p-4 text-center text-sm text-muted">
              No {filter} comments in the captured set.
            </div>
          ) : (
            filtered.map((c, i) => (
              <div key={i} className="rounded-xl border border-line bg-raised p-3">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="truncate text-xs font-semibold">{c.author || "Anonymous"}</span>
                  <span
                    className={clsx(
                      "chip shrink-0 border capitalize",
                      LABEL_STYLES[c.label] || LABEL_STYLES.neutral
                    )}
                  >
                    {c.label}
                  </span>
                </div>
                <p className="text-[13px] leading-relaxed text-fg/90">{c.text}</p>
                {c.like_count > 0 && (
                  <div className="mt-1.5 flex items-center gap-1 text-[11px] text-muted">
                    <ThumbsUp size={11} /> <span className="num">{fmtCompact(c.like_count)}</span>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
