import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  FileText,
  Play,
  Settings2,
  Smile,
} from "lucide-react";
import clsx from "clsx";
import Button from "../../components/ui/Button.jsx";
import Badge, { statusTone } from "../../components/ui/Badge.jsx";
import Skeleton from "../../components/ui/Skeleton.jsx";
import { useApi } from "../../hooks/useApi.js";
import { api } from "../../lib/api.js";
import { useStatus } from "../../context/StatusContext.jsx";
import { fmtCompact, fmtDateTime, fmtNum, fmtRunDuration, relTime } from "../../lib/format.js";

function InfoCard({ icon: Icon, title, children }) {
  return (
    <div className="card p-5">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <Icon size={16} className="text-primary" />
        {title}
      </div>
      {children}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between py-1.5 text-sm">
      <span className="text-muted">{label}</span>
      <span className="num font-semibold">{value}</span>
    </div>
  );
}

export default function SystemPage() {
  const { status, triggerRun } = useStatus();
  const { data: runs, loading: runsLoading, refetch: refetchRuns } = useApi(() => api.runs(20), []);

  const running = status?.pipeline_running;
  const quota = status?.quota;
  const cfg = status?.config;
  const totals = status?.totals;
  const quotaPct = quota ? Math.min(100, Math.round((quota.used / quota.budget) * 100)) : 0;

  return (
    <div className="space-y-6">
      {/* API key warning */}
      {cfg && !cfg.api_key_configured && (
        <div className="card flex items-start gap-3 border-warning/40 bg-warning/10 p-4">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-warning" />
          <div className="text-sm">
            <span className="font-semibold">YouTube API key not configured.</span> Add{" "}
            <code className="rounded bg-raised px-1.5 py-0.5 text-xs">YOUTUBE_API_KEY</code> to{" "}
            <code className="rounded bg-raised px-1.5 py-0.5 text-xs">backend/.env</code> and restart the backend
            to enable live ingestion. The dashboard is currently showing demo / previously-collected data.
          </div>
        </div>
      )}

      {/* Top status row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <InfoCard icon={Cpu} title="Pipeline">
          {!status ? (
            <Skeleton className="h-20 w-full" />
          ) : (
            <>
              <div className="mb-3 flex items-center gap-2">
                <span className={clsx("h-2.5 w-2.5 rounded-full", running ? "pt-pulse bg-accent" : "bg-success")} />
                <span className="font-semibold">{running ? "Running now" : "Idle"}</span>
              </div>
              <Row label="Last run" value={status.last_run ? relTime(status.last_run.started_at) : "—"} />
              <Row label="Next run" value={status.next_run_at ? relTime(status.next_run_at) : "—"} />
              <Row label="Interval" value={cfg ? `${cfg.interval_minutes} min` : "—"} />
              <Button
                size="sm"
                variant="primary"
                className="mt-3 w-full"
                onClick={triggerRun}
                disabled={running}
                loading={running}
              >
                {!running && <Play size={13} />}
                {running ? "Running…" : "Run ingestion now"}
              </Button>
            </>
          )}
        </InfoCard>

        <InfoCard icon={Database} title="YouTube API quota (today)">
          {!quota ? (
            <Skeleton className="h-20 w-full" />
          ) : (
            <>
              <div className="mb-1 flex items-end justify-between">
                <span className="num font-display text-2xl font-bold">{fmtNum(quota.used)}</span>
                <span className="text-sm text-muted">/ {fmtCompact(quota.budget)} units</span>
              </div>
              <div className="mb-3 h-2 w-full overflow-hidden rounded-full bg-raised">
                <div
                  className={clsx(
                    "h-full rounded-full transition-all",
                    quotaPct > 85 ? "bg-danger" : quotaPct > 60 ? "bg-warning" : "bg-accent"
                  )}
                  style={{ width: `${quotaPct}%` }}
                />
              </div>
              <Row label="Remaining" value={`${fmtNum(quota.remaining)} units`} />
              <Row label="Daily limit" value={fmtCompact(quota.limit)} />
              <Row label="Resets" value="Midnight PT" />
            </>
          )}
        </InfoCard>

        <InfoCard icon={Settings2} title="Configuration">
          {!cfg ? (
            <Skeleton className="h-20 w-full" />
          ) : (
            <>
              <Row label="Keywords / run" value={cfg.keywords_per_run} />
              <Row label="Search order" value={cfg.search_order} />
              <Row label="Region" value={cfg.region_code} />
              <Row label="Discovery window" value={`${cfg.published_within_days} days`} />
              <Row label="Transcripts" value={cfg.transcript_provider} />
              <Row
                label="API key"
                value={
                  cfg.api_key_configured ? (
                    <Badge tone="success">configured</Badge>
                  ) : (
                    <Badge tone="warning">missing</Badge>
                  )
                }
              />
            </>
          )}
        </InfoCard>
      </div>

      {/* Totals strip */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatMini icon={Database} label="Products tracked" value={totals ? fmtCompact(totals.videos) : "—"} />
        <StatMini icon={Settings2} label="Active keywords" value={totals ? totals.active_keywords : "—"} />
        <StatMini icon={FileText} label="Transcripts captured" value={totals ? fmtCompact(totals.transcripts_ok) : "—"} />
        <StatMini icon={Smile} label="With sentiment" value={totals ? fmtCompact(totals.with_sentiment) : "—"} />
      </div>

      {/* Run history */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Clock size={16} className="text-primary" /> Ingestion run history
          </div>
          <Button size="sm" variant="ghost" onClick={() => refetchRuns()}>
            Refresh
          </Button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold uppercase tracking-wide text-muted">
                <th className="px-5 py-2.5">Started</th>
                <th className="px-3 py-2.5">Status</th>
                <th className="px-3 py-2.5">Trigger</th>
                <th className="px-3 py-2.5 text-right">Duration</th>
                <th className="px-3 py-2.5 text-right">New</th>
                <th className="px-3 py-2.5 text-right">Refreshed</th>
                <th className="px-3 py-2.5 text-right">Sentiment</th>
                <th className="px-3 py-2.5 text-right">Scripts</th>
                <th className="px-5 py-2.5 text-right">Units</th>
              </tr>
            </thead>
            <tbody>
              {runsLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i} className="border-t border-line">
                    <td colSpan={9} className="px-5 py-3">
                      <Skeleton className="h-4 w-full" />
                    </td>
                  </tr>
                ))
              ) : !runs || runs.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-5 py-10 text-center text-sm text-muted">
                    No runs recorded yet.
                  </td>
                </tr>
              ) : (
                runs.map((run) => (
                  <tr key={run.id} className="border-t border-line align-top">
                    <td className="px-5 py-3">
                      <div className="font-medium">{fmtDateTime(run.started_at)}</div>
                      <div className="text-xs text-muted">{relTime(run.started_at)}</div>
                      {run.error && (
                        <div className="mt-1 max-w-md text-xs leading-snug text-warning" title={run.error}>
                          {run.error.length > 90 ? run.error.slice(0, 90) + "…" : run.error}
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <Badge tone={statusTone(run.status)}>
                        {run.status === "success" && <CheckCircle2 size={11} />}
                        {run.status.replace("_", " ")}
                      </Badge>
                    </td>
                    <td className="px-3 py-3 capitalize text-muted">{run.trigger}</td>
                    <td className="num px-3 py-3 text-right">{fmtRunDuration(run.started_at, run.finished_at)}</td>
                    <td className="num px-3 py-3 text-right font-semibold text-success">
                      {run.videos_discovered > 0 ? `+${run.videos_discovered}` : "—"}
                    </td>
                    <td className="num px-3 py-3 text-right">{run.videos_refreshed || "—"}</td>
                    <td className="num px-3 py-3 text-right">{run.sentiment_computed || "—"}</td>
                    <td className="num px-3 py-3 text-right">{run.transcripts_fetched || "—"}</td>
                    <td className="num px-5 py-3 text-right text-muted">{run.quota_units_used}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatMini({ icon: Icon, label, value }) {
  return (
    <div className="card flex items-center gap-3 p-4">
      <Icon size={18} className="text-muted" />
      <div>
        <div className="num font-display text-xl font-bold">{value}</div>
        <div className="text-xs text-muted">{label}</div>
      </div>
    </div>
  );
}
