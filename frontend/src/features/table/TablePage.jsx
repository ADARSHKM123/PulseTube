import { useState } from "react";
import { ArrowDown, ArrowUp, ChevronsUpDown, Download, Table2 } from "lucide-react";
import clsx from "clsx";
import FilterBar from "./FilterBar.jsx";
import { useTrendFilters } from "./useTrendFilters.js";
import VideoDetailModal from "../../components/features/VideoDetailModal.jsx";
import SentimentBar from "../../components/ui/SentimentBar.jsx";
import Badge from "../../components/ui/Badge.jsx";
import Button from "../../components/ui/Button.jsx";
import Skeleton from "../../components/ui/Skeleton.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import { useApi } from "../../hooks/useApi.js";
import { api } from "../../lib/api.js";
import { fmtCompact, fmtPct, fmtVelocity, relTime } from "../../lib/format.js";

const COLUMNS = [
  { id: "title", label: "Product", sortable: true, align: "left", width: "min-w-[280px]" },
  { id: "views", label: "Views", sortable: true, align: "right" },
  { id: "likes", label: "Likes", sortable: true, align: "right" },
  { id: "comments", label: "Comments", sortable: true, align: "right" },
  { id: "like_ratio", label: "Like %", sortable: true, align: "right" },
  { id: "velocity", label: "Velocity", sortable: true, align: "right" },
  { id: "positive", label: "Sentiment", sortable: true, align: "left", width: "min-w-[150px]" },
  { id: "published", label: "Published", sortable: true, align: "right" },
];

function SortHeader({ col, sort, order, onSort }) {
  const active = sort === col.id;
  const Icon = !col.sortable ? null : active ? (order === "desc" ? ArrowDown : ArrowUp) : ChevronsUpDown;
  return (
    <th
      className={clsx(
        "sticky top-0 z-10 whitespace-nowrap bg-raised px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted",
        col.align === "right" ? "text-right" : "text-left",
        col.width
      )}
    >
      {col.sortable ? (
        <button
          onClick={() => onSort(col.id)}
          className={clsx(
            "inline-flex items-center gap-1 transition-colors hover:text-fg",
            col.align === "right" && "flex-row-reverse",
            active && "text-primary"
          )}
        >
          {col.label}
          {Icon && <Icon size={13} />}
        </button>
      ) : (
        col.label
      )}
    </th>
  );
}

export default function TablePage() {
  const f = useTrendFilters();
  const [openId, setOpenId] = useState(null);
  const pageSize = 25;

  const { data, loading, error, refetch } = useApi(
    () => api.trends({ ...f.queryParams, page: f.page, page_size: pageSize }),
    [f.queryParams, f.page]
  );

  const items = data?.items || [];
  const total = data?.total || 0;
  const pages = data?.pages || 1;

  return (
    <div className="space-y-4">
      <FilterBar filters={f.filters} setFilter={f.setFilter} reset={f.reset} activeCount={f.activeCount} />

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">
          {loading ? "Loading…" : <><span className="num font-semibold text-fg">{fmtCompact(total)}</span> products match</>}
        </p>
        {/* Export honors all active filters — server streams full filtered set */}
        <a href={api.exportUrl(f.queryParams)}>
          <Button size="sm" variant="outline" disabled={total === 0}>
            <Download size={14} /> Export CSV
          </Button>
        </a>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                {COLUMNS.map((col) => (
                  <SortHeader key={col.id} col={col} sort={f.sort} order={f.order} onSort={f.toggleSort} />
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="border-t border-line">
                    {COLUMNS.map((c) => (
                      <td key={c.id} className="px-3 py-3">
                        <Skeleton className="h-4 w-full" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={COLUMNS.length} className="p-0">
                    <EmptyState
                      icon={Table2}
                      title={error ? "Couldn't load data" : "No products match these filters"}
                      hint={error ? error.message : "Try loosening or resetting your filters."}
                      action={
                        error ? (
                          <Button variant="primary" onClick={() => refetch()}>
                            Retry
                          </Button>
                        ) : (
                          f.activeCount > 0 && (
                            <Button variant="outline" onClick={f.reset}>
                              Reset filters
                            </Button>
                          )
                        )
                      }
                    />
                  </td>
                </tr>
              ) : (
                items.map((v) => (
                  <tr
                    key={v.video_id}
                    onClick={() => setOpenId(v.video_id)}
                    className="cursor-pointer border-t border-line transition-colors hover:bg-raised/60"
                  >
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-3">
                        <img
                          src={v.thumbnail_url}
                          alt=""
                          loading="lazy"
                          className="h-9 w-16 shrink-0 rounded-md object-cover"
                        />
                        <div className="min-w-0">
                          <div className="line-clamp-1 font-semibold">{v.title}</div>
                          <div className="line-clamp-1 text-xs text-muted">{v.channel_title}</div>
                        </div>
                      </div>
                    </td>
                    <td className="num px-3 py-2.5 text-right font-semibold">{fmtCompact(v.latest_view_count)}</td>
                    <td className="num px-3 py-2.5 text-right">{fmtCompact(v.latest_like_count)}</td>
                    <td className="num px-3 py-2.5 text-right">{fmtCompact(v.latest_comment_count)}</td>
                    <td className="num px-3 py-2.5 text-right">{fmtPct(v.like_ratio, 1)}</td>
                    <td
                      className={clsx(
                        "num px-3 py-2.5 text-right font-semibold",
                        v.view_velocity > 0 ? "text-success" : "text-muted"
                      )}
                    >
                      {fmtVelocity(v.view_velocity)}
                    </td>
                    <td className="px-3 py-2.5">
                      {v.sentiment_positive_pct != null ? (
                        <div className="w-32">
                          <div className="mb-1 flex justify-between text-[10px] font-semibold">
                            <span className="text-success">{fmtPct(v.sentiment_positive_pct, 0)}</span>
                            <span className="text-danger">{fmtPct(v.sentiment_negative_pct, 0)}</span>
                          </div>
                          <SentimentBar
                            positive={v.sentiment_positive_pct}
                            neutral={v.sentiment_neutral_pct}
                            negative={v.sentiment_negative_pct}
                          />
                        </div>
                      ) : (
                        <Badge tone="muted">no data</Badge>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right text-xs text-muted">{relTime(v.published_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
            <span className="text-muted">
              Page <span className="num font-semibold text-fg">{f.page}</span> of{" "}
              <span className="num">{pages}</span>
            </span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={f.page <= 1} onClick={() => f.setPage(f.page - 1)}>
                Previous
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={f.page >= pages}
                onClick={() => f.setPage(f.page + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

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
