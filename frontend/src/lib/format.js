const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const full = new Intl.NumberFormat("en");

export function fmtCompact(n) {
  if (n === null || n === undefined) return "—";
  return compact.format(n);
}

export function fmtNum(n) {
  if (n === null || n === undefined) return "—";
  return full.format(n);
}

export function fmtPct(n, digits = 1) {
  if (n === null || n === undefined) return "—";
  return `${Number(n).toFixed(digits)}%`;
}

export function fmtVelocity(n) {
  if (n === null || n === undefined) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${compact.format(Math.round(n))}/hr`;
}

export function relTime(iso) {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const secs = Math.round((Date.now() - then) / 1000);
  const future = secs < 0;
  const s = Math.abs(secs);
  let label;
  if (s < 60) label = `${s}s`;
  else if (s < 3600) label = `${Math.floor(s / 60)}m`;
  else if (s < 86400) label = `${Math.floor(s / 3600)}h`;
  else label = `${Math.floor(s / 86400)}d`;
  return future ? `in ${label}` : `${label} ago`;
}

export function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtDuration(totalSeconds) {
  if (!totalSeconds && totalSeconds !== 0) return "";
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const mm = h > 0 ? String(m).padStart(2, "0") : String(m);
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

export function fmtRunDuration(startIso, endIso) {
  if (!startIso || !endIso) return "—";
  const ms = new Date(endIso) - new Date(startIso);
  if (Number.isNaN(ms) || ms < 0) return "—";
  const secs = Math.round(ms / 1000);
  return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m ${secs % 60}s`;
}
