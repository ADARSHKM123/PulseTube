import { ThumbsUp } from "lucide-react";
import clsx from "clsx";
import SentimentBar from "../ui/SentimentBar.jsx";
import { fmtCompact, fmtPct } from "../../lib/format.js";

const LABEL_STYLES = {
  positive: "bg-success/12 text-success border-success/25",
  negative: "bg-danger/12 text-danger border-danger/25",
  neutral: "bg-muted/12 text-muted border-line",
};

/** "What people think" — aggregate distribution + the most-liked sample comments. */
export default function SentimentPanel({ sentiment }) {
  if (!sentiment || sentiment.comments_analyzed === 0) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm text-muted">
        No sentiment yet — comments may be disabled, or this video hasn't been analyzed in a run.
      </div>
    );
  }

  const donut = [
    { label: "Positive", value: sentiment.positive_pct, color: "var(--c-success)" },
    { label: "Neutral", value: sentiment.neutral_pct, color: "var(--c-muted)" },
    { label: "Negative", value: sentiment.negative_pct, color: "var(--c-danger)" },
  ];
  // Conic gradient donut — no chart lib needed for a single ring.
  let acc = 0;
  const stops = donut
    .map((d) => {
      const start = acc;
      acc += d.value;
      return `rgb(${d.color}) ${start}% ${acc}%`;
    })
    .join(", ");

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
        <div className="min-w-0 flex-1 space-y-1.5">
          {donut.map((d) => (
            <div key={d.label} className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: `rgb(${d.color})` }} />
                {d.label}
              </span>
              <span className="num font-semibold">{fmtPct(d.value)}</span>
            </div>
          ))}
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
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Top comments</h4>
        <div className="space-y-2">
          {(sentiment.sample_comments || []).map((c, i) => (
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
          ))}
        </div>
      </div>
    </div>
  );
}
