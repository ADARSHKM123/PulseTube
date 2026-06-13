import { fmtPct } from "../../lib/format.js";

/**
 * Tri-color positive/neutral/negative distribution bar.
 * Renders a quiet "no data" track when sentiment hasn't been computed yet.
 */
export default function SentimentBar({ positive, neutral, negative, showLabels = false, className = "" }) {
  const hasData = positive !== null && positive !== undefined;
  return (
    <div className={className}>
      {showLabels && hasData && (
        <div className="mb-1.5 flex justify-between text-[11px] font-semibold">
          <span className="text-success">{fmtPct(positive)} positive</span>
          <span className="text-muted">{fmtPct(neutral)} neutral</span>
          <span className="text-danger">{fmtPct(negative)} negative</span>
        </div>
      )}
      <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-raised">
        {hasData ? (
          <>
            <div className="bg-success transition-all" style={{ width: `${positive}%` }} />
            <div className="bg-muted/40 transition-all" style={{ width: `${neutral}%` }} />
            <div className="bg-danger transition-all" style={{ width: `${negative}%` }} />
          </>
        ) : null}
      </div>
    </div>
  );
}
