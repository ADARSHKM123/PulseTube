import { Eye, MessageCircle, ThumbsUp, TrendingUp } from "lucide-react";
import Badge from "../ui/Badge.jsx";
import SentimentBar from "../ui/SentimentBar.jsx";
import { fmtCompact, fmtDuration, fmtVelocity, relTime } from "../../lib/format.js";

const FALLBACK_THUMB =
  "data:image/svg+xml;charset=utf-8," +
  encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='320' height='180'><rect width='100%' height='100%' fill='%23171b27'/><text x='50%' y='50%' fill='%235b647c' font-family='sans-serif' font-size='13' text-anchor='middle' dy='.3em'>thumbnail unavailable</text></svg>`
  );

function Metric({ icon: Icon, value, title }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted" title={title}>
      <Icon size={13} className="shrink-0" />
      <span className="num font-semibold text-fg/90">{value}</span>
    </span>
  );
}

/** A single discovered product — image, metrics, momentum, sentiment glance. */
export default function TrendCard({ video, onOpen }) {
  const spiking = video.view_velocity > 0;
  return (
    <button
      onClick={() => onOpen(video.video_id)}
      className="card group flex flex-col overflow-hidden text-left transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-pop focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
    >
      <div className="relative aspect-video w-full overflow-hidden bg-raised">
        <img
          src={video.thumbnail_url || FALLBACK_THUMB}
          alt=""
          loading="lazy"
          onError={(e) => {
            e.currentTarget.src = FALLBACK_THUMB;
          }}
          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
        {video.duration_seconds != null && (
          <span className="num absolute bottom-2 right-2 rounded-md bg-black/80 px-1.5 py-0.5 text-[11px] font-semibold text-white">
            {fmtDuration(video.duration_seconds)}
          </span>
        )}
        {spiking && (
          <span className="chip absolute left-2 top-2 bg-primary text-primary-fg shadow">
            <TrendingUp size={12} /> {fmtVelocity(video.view_velocity)}
          </span>
        )}
        {video.keyword && (
          <span className="chip absolute bottom-2 left-2 bg-black/70 text-white/90">{video.keyword}</span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2.5 p-3.5">
        <h3 className="line-clamp-2 text-sm font-semibold leading-snug group-hover:text-primary">
          {video.title}
        </h3>
        <div className="flex items-center justify-between text-xs text-muted">
          <span className="truncate pr-2">{video.channel_title}</span>
          <span className="shrink-0">{relTime(video.published_at)}</span>
        </div>

        <div className="mt-auto flex items-center gap-3 pt-1">
          <Metric icon={Eye} value={fmtCompact(video.latest_view_count)} title="Views" />
          <Metric icon={ThumbsUp} value={fmtCompact(video.latest_like_count)} title="Likes" />
          <Metric icon={MessageCircle} value={fmtCompact(video.latest_comment_count)} title="Comments" />
          {video.transcript_status === "ok" && (
            <Badge tone="accent" className="ml-auto">
              script
            </Badge>
          )}
        </div>

        <SentimentBar
          positive={video.sentiment_positive_pct}
          neutral={video.sentiment_neutral_pct}
          negative={video.sentiment_negative_pct}
        />
      </div>
    </button>
  );
}
