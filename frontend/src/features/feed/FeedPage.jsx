import { useState } from "react";
import { Flame, Layers, Smile, TrendingUp } from "lucide-react";
import StatTile from "../../components/features/StatTile.jsx";
import TrendCard from "../../components/features/TrendCard.jsx";
import VideoDetailModal from "../../components/features/VideoDetailModal.jsx";
import { CardSkeleton } from "../../components/ui/Skeleton.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import Button from "../../components/ui/Button.jsx";
import { Input, Select } from "../../components/ui/Input.jsx";
import { useApi, useDebounced } from "../../hooks/useApi.js";
import { api } from "../../lib/api.js";
import { useStatus } from "../../context/StatusContext.jsx";
import { fmtCompact, fmtPct } from "../../lib/format.js";

const SORTS = [
  { value: "velocity", label: "Spiking now" },
  { value: "views", label: "Most viewed" },
  { value: "likes", label: "Most liked" },
  { value: "first_seen", label: "Recently discovered" },
  { value: "positive", label: "Most positive" },
];

export default function FeedPage() {
  const { triggerRun } = useStatus();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("velocity");
  const [openId, setOpenId] = useState(null);
  const debouncedSearch = useDebounced(search, 350);

  const { data: overview } = useApi(() => api.overview(), []);
  const { data, loading, error, refetch } = useApi(
    () => api.trends({ q: debouncedSearch, sort, order: "desc", page_size: 48 }),
    [debouncedSearch, sort]
  );

  const items = data?.items || [];

  return (
    <div className="space-y-6">
      {/* Overview stats */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          icon={Layers}
          label="Products tracked"
          value={overview ? fmtCompact(overview.videos_total) : "—"}
          tone="primary"
        />
        <StatTile
          icon={Flame}
          label="New in last 24h"
          value={overview ? fmtCompact(overview.videos_new_24h) : "—"}
          tone="accent"
        />
        <StatTile
          icon={TrendingUp}
          label="Total views tracked"
          value={overview ? fmtCompact(overview.total_views_tracked) : "—"}
          tone="success"
        />
        <StatTile
          icon={Smile}
          label="Avg positive sentiment"
          value={overview?.avg_positive_pct != null ? fmtPct(overview.avg_positive_pct) : "—"}
          tone="warning"
        />
      </div>

      {/* Controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex-1">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search products by title or channel…"
          />
        </div>
        <Select value={sort} onChange={(e) => setSort(e.target.value)} className="sm:w-52">
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </Select>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : error ? (
        <EmptyState
          icon={Flame}
          title="Couldn't load trends"
          hint={error.message}
          action={
            <Button variant="primary" onClick={() => refetch()}>
              Retry
            </Button>
          }
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Flame}
          title={debouncedSearch ? "No products match your search" : "No trends discovered yet"}
          hint={
            debouncedSearch
              ? "Try a broader search term."
              : "Run an ingestion cycle to pull the latest viral products from YouTube, or seed demo data."
          }
          action={
            !debouncedSearch && (
              <Button variant="primary" onClick={triggerRun}>
                Run ingestion now
              </Button>
            )
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {items.map((v) => (
            <TrendCard key={v.video_id} video={v} onOpen={setOpenId} />
          ))}
        </div>
      )}

      {openId && (
        <VideoDetailModal
          videoId={openId}
          open={!!openId}
          onClose={() => setOpenId(null)}
          onChanged={() => refetch(true)}
        />
      )}
    </div>
  );
}
