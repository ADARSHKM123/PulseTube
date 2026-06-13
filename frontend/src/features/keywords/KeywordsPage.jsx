import { useState } from "react";
import { Globe, Plus, Tag, Trash2 } from "lucide-react";
import Button from "../../components/ui/Button.jsx";
import { Input, Switch } from "../../components/ui/Input.jsx";
import Badge from "../../components/ui/Badge.jsx";
import Skeleton from "../../components/ui/Skeleton.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import { useApi } from "../../hooks/useApi.js";
import { api } from "../../lib/api.js";
import { useToast } from "../../context/ToastContext.jsx";
import { fmtCompact, relTime } from "../../lib/format.js";

function KeywordRow({ kw, onToggle, onDelete }) {
  const isGlobal = kw.kind === "global";
  return (
    <div className="flex items-center gap-3 border-t border-line px-4 py-3 first:border-t-0">
      <div className={isGlobal ? "text-accent" : "text-primary"}>
        {isGlobal ? <Globe size={16} /> : <Tag size={16} />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate font-semibold">{kw.keyword}</span>
          <Badge tone={isGlobal ? "accent" : "primary"}>{kw.kind}</Badge>
        </div>
        <div className="text-xs text-muted">
          {fmtCompact(kw.video_count)} products · searched {kw.search_count}× ·{" "}
          {kw.last_searched_at ? `last ${relTime(kw.last_searched_at)}` : "not searched yet"}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5" title={kw.is_active ? "Active in rotation" : "Paused"}>
          <Switch checked={kw.is_active} onChange={(v) => onToggle(kw, v)} />
          <span className="hidden text-xs text-muted sm:inline">{kw.is_active ? "Active" : "Paused"}</span>
        </div>
        {!isGlobal && (
          <button
            onClick={() => onDelete(kw)}
            className="rounded-lg p-1.5 text-muted transition-colors hover:bg-danger/10 hover:text-danger"
            aria-label="Delete keyword"
          >
            <Trash2 size={15} />
          </button>
        )}
      </div>
    </div>
  );
}

export default function KeywordsPage() {
  const toast = useToast();
  const [newKeyword, setNewKeyword] = useState("");
  const [adding, setAdding] = useState(false);
  const { data, loading, refetch } = useApi(() => api.keywords(), []);

  const keywords = data || [];
  const globals = keywords.filter((k) => k.kind === "global");
  const customs = keywords.filter((k) => k.kind === "custom");

  const add = async (e) => {
    e.preventDefault();
    const value = newKeyword.trim();
    if (value.length < 2) return;
    setAdding(true);
    try {
      await api.addKeyword(value);
      setNewKeyword("");
      toast(`Now tracking "${value}"`, "success");
      refetch(true);
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setAdding(false);
    }
  };

  const toggle = async (kw, active) => {
    try {
      await api.patchKeyword(kw.id, { is_active: active });
      refetch(true);
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const remove = async (kw) => {
    if (!confirm(`Delete keyword "${kw.keyword}"? Tracked products stay, but it won't be searched again.`)) return;
    try {
      await api.deleteKeyword(kw.id);
      toast(`Deleted "${kw.keyword}"`, "info");
      refetch(true);
    } catch (err) {
      toast(err.message, "error");
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Add custom keyword */}
      <div className="card p-5">
        <h2 className="font-display text-lg font-bold">Track a custom product</h2>
        <p className="mt-1 text-sm text-muted">
          Add a specific product name or niche. It enters the rotation immediately and is searched on the next
          ingestion cycle.
        </p>
        <form onSubmit={add} className="mt-4 flex gap-2">
          <Input
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            placeholder="e.g. portable blender, LED face mask…"
            maxLength={255}
          />
          <Button type="submit" variant="primary" loading={adding} disabled={newKeyword.trim().length < 2}>
            <Plus size={15} /> Add
          </Button>
        </form>
      </div>

      {/* Custom keywords */}
      <section>
        <h3 className="mb-2 px-1 text-sm font-semibold uppercase tracking-wide text-muted">
          Custom keywords ({customs.length})
        </h3>
        <div className="card overflow-hidden">
          {loading ? (
            <div className="space-y-3 p-4">
              {Array.from({ length: 2 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : customs.length === 0 ? (
            <EmptyState
              icon={Tag}
              title="No custom keywords yet"
              hint="Add a product above to track it alongside the global trend keywords."
            />
          ) : (
            customs.map((kw) => <KeywordRow key={kw.id} kw={kw} onToggle={toggle} onDelete={remove} />)
          )}
        </div>
      </section>

      {/* Global keywords */}
      <section>
        <h3 className="mb-2 px-1 text-sm font-semibold uppercase tracking-wide text-muted">
          Global trend keywords ({globals.length})
        </h3>
        <div className="card overflow-hidden">
          {loading ? (
            <div className="space-y-3 p-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            globals.map((kw) => <KeywordRow key={kw.id} kw={kw} onToggle={toggle} onDelete={remove} />)
          )}
        </div>
        <p className="mt-2 px-1 text-xs text-muted">
          Global keywords power broad discovery and can be paused but not deleted.
        </p>
      </section>
    </div>
  );
}
