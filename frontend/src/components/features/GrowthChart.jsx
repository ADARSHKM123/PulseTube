import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtCompact, fmtDateTime } from "../../lib/format.js";

const css = (name) => `rgb(${getComputedStyle(document.documentElement).getPropertyValue(name).trim()})`;

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="card px-3 py-2 text-xs shadow-pop">
      <div className="mb-1 font-semibold">{fmtDateTime(label)}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5" style={{ color: p.color }}>
            <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
            {p.name}
          </span>
          <span className="num font-semibold">{fmtCompact(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

/**
 * Dual-axis time-series of views (area, left) + likes (line, right).
 * This is how the user pinpoints exactly when a product started spiking.
 */
export default function GrowthChart({ history }) {
  if (!history || history.length < 2) {
    return (
      <div className="flex h-full min-h-[220px] items-center justify-center text-sm text-muted">
        Not enough history yet — the growth curve appears after a few ingestion runs.
      </div>
    );
  }

  const data = history.map((h) => ({
    t: h.captured_at,
    views: h.view_count,
    likes: h.like_count,
  }));
  const primary = css("--c-primary");
  const accent = css("--c-accent");
  const border = css("--c-border");
  const muted = css("--c-muted");

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="viewsFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={primary} stopOpacity={0.35} />
            <stop offset="100%" stopColor={primary} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={border} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="t"
          tickFormatter={fmtDateTime}
          tick={{ fontSize: 11, fill: muted }}
          stroke={border}
          minTickGap={40}
        />
        <YAxis
          yAxisId="left"
          tickFormatter={fmtCompact}
          tick={{ fontSize: 11, fill: muted }}
          stroke={border}
          width={48}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          tickFormatter={fmtCompact}
          tick={{ fontSize: 11, fill: muted }}
          stroke={border}
          width={48}
        />
        <Tooltip content={<ChartTooltip />} />
        <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" />
        <Area
          yAxisId="left"
          type="monotone"
          dataKey="views"
          name="Views"
          stroke={primary}
          strokeWidth={2}
          fill="url(#viewsFill)"
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="likes"
          name="Likes"
          stroke={accent}
          strokeWidth={2}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
