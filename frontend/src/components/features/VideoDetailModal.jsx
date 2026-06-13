import { useState } from "react";
import {
  ExternalLink,
  Eye,
  Gauge,
  MessageSquare,
  RefreshCw,
  ThumbsUp,
  Trash2,
} from "lucide-react";
import Modal from "../ui/Modal.jsx";
import Button from "../ui/Button.jsx";
import Badge, { statusTone } from "../ui/Badge.jsx";
import Skeleton from "../ui/Skeleton.jsx";
import GrowthChart from "./GrowthChart.jsx";
import TranscriptPanel from "./TranscriptPanel.jsx";
import SentimentPanel from "./SentimentPanel.jsx";
import { useApi } from "../../hooks/useApi.js";
import { api } from "../../lib/api.js";
import { useToast } from "../../context/ToastContext.jsx";
import { fmtCompact, fmtNum, fmtPct, fmtVelocity, relTime } from "../../lib/format.js";

function HeadlineMetric({ icon: Icon, label, value }) {
  return (
    <div className="rounded-xl border border-line bg-raised px-3 py-2">
      <div className="flex items-center gap-1.5 text-[11px] font-medium text-muted">
        <Icon size={12} /> {label}
      </div>
      <div className="num mt-0.5 font-display text-lg font-bold tracking-tight">{value}</div>
    </div>
  );
}

const TABS = [
  { id: "transcript", label: "Video Script" },
  { id: "sentiment", label: "Audience Sentiment" },
];

export default function VideoDetailModal({ videoId, open, onClose, onChanged }) {
  const toast = useToast();
  const [tab, setTab] = useState("transcript");
  const [refreshing, setRefreshing] = useState(false);

  const { data: video, loading, refetch } = useApi(
    () => api.video(videoId),
    [videoId]
  );
  const { data: history, refetch: refetchHistory } = useApi(
    () => api.history(videoId),
    [videoId]
  );
  const { data: transcript } = useApi(() => api.transcript(videoId), [videoId]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.refreshVideo(videoId);
      await Promise.all([refetch(), refetchHistory()]);
      onChanged?.();
      toast("Live metrics & sentiment refreshed", "success");
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setRefreshing(false);
    }
  };

  const handleUntrack = async () => {
    if (!confirm("Stop tracking this video and delete its history?")) return;
    try {
      await api.untrackVideo(videoId);
      toast("Video removed from tracking", "info");
      onChanged?.();
      onClose();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  return (
    <Modal open={open} onClose={onClose} wide>
      {loading || !video ? (
        <div className="space-y-4 p-6">
          <Skeleton className="h-7 w-3/4" />
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : (
        <div className="flex max-h-[88vh] flex-col">
          {/* Header */}
          <div className="border-b border-line p-5 pr-12">
            <div className="flex flex-wrap items-center gap-2 pb-2">
              {video.keyword && <Badge tone="primary">{video.keyword}</Badge>}
              <Badge tone={statusTone(video.transcript_status)}>script: {video.transcript_status}</Badge>
              <span className="text-xs text-muted">
                Published {relTime(video.published_at)} · tracked since {relTime(video.first_seen_at)}
              </span>
            </div>
            <h2 className="font-display text-xl font-bold leading-tight">{video.title}</h2>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
              <span className="font-semibold text-fg/80">{video.channel_title}</span>
              <a
                href={video.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-accent hover:underline"
              >
                Watch on YouTube <ExternalLink size={13} />
              </a>
            </div>
          </div>

          <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2">
            {/* Left pane: metrics + growth chart */}
            <div className="flex min-h-0 flex-col gap-4 border-line p-5 lg:border-r">
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                <HeadlineMetric icon={Eye} label="Views" value={fmtCompact(video.latest_view_count)} />
                <HeadlineMetric icon={ThumbsUp} label="Likes" value={fmtCompact(video.latest_like_count)} />
                <HeadlineMetric
                  icon={MessageSquare}
                  label="Comments"
                  value={fmtCompact(video.latest_comment_count)}
                />
                <HeadlineMetric
                  icon={Gauge}
                  label="View velocity"
                  value={fmtVelocity(video.view_velocity)}
                />
              </div>

              <div className="flex items-center justify-between text-xs text-muted">
                <span>
                  Like ratio <span className="num font-semibold text-fg">{fmtPct(video.like_ratio, 2)}</span>
                </span>
                <span>
                  Exact views <span className="num font-semibold text-fg">{fmtNum(video.latest_view_count)}</span>
                </span>
              </div>

              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
                  Growth — views & likes over time
                </h3>
                <div className="h-[260px] rounded-xl border border-line bg-raised/40 p-2">
                  <GrowthChart history={history} />
                </div>
              </div>

              <div className="mt-auto flex flex-wrap gap-2 pt-1">
                <Button size="sm" variant="primary" onClick={handleRefresh} loading={refreshing}>
                  {!refreshing && <RefreshCw size={13} />} Refresh live
                </Button>
                <Button size="sm" variant="danger" onClick={handleUntrack}>
                  <Trash2 size={13} /> Untrack
                </Button>
              </div>
            </div>

            {/* Right pane: tabbed transcript / sentiment (split-pane on large screens) */}
            <div className="flex min-h-0 flex-col">
              <div className="flex shrink-0 gap-1 border-b border-line p-2">
                {TABS.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className={
                      "flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition-colors " +
                      (tab === t.id ? "bg-primary/10 text-primary" : "text-muted hover:bg-raised hover:text-fg")
                    }
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <div className="min-h-[420px] flex-1 overflow-hidden">
                {tab === "transcript" ? (
                  <TranscriptPanel transcript={transcript} />
                ) : (
                  <SentimentPanel sentiment={video.sentiment} />
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
