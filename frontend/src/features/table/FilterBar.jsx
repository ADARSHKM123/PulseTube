import { RotateCcw, SlidersHorizontal } from "lucide-react";
import { Field, Input, Select } from "../../components/ui/Input.jsx";
import Button from "../../components/ui/Button.jsx";

/** Numeric/threshold deep-filter controls for the trends table. */
export default function FilterBar({ filters, setFilter, reset, activeCount }) {
  return (
    <div className="card p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <SlidersHorizontal size={15} className="text-primary" />
          Filters
          {activeCount > 0 && (
            <span className="chip bg-primary/12 text-primary">{activeCount} active</span>
          )}
        </div>
        {activeCount > 0 && (
          <Button size="sm" variant="ghost" onClick={reset}>
            <RotateCcw size={13} /> Reset
          </Button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        <Field label="Search" className="col-span-2 sm:col-span-3 lg:col-span-2">
          <Input
            value={filters.q}
            onChange={(e) => setFilter("q", e.target.value)}
            placeholder="Title or channel…"
          />
        </Field>
        <Field label="Min views">
          <Input
            type="number"
            min="0"
            value={filters.min_views}
            onChange={(e) => setFilter("min_views", e.target.value)}
            placeholder="e.g. 100000"
          />
        </Field>
        <Field label="Min likes">
          <Input
            type="number"
            min="0"
            value={filters.min_likes}
            onChange={(e) => setFilter("min_likes", e.target.value)}
            placeholder="e.g. 5000"
          />
        </Field>
        <Field label="Min comments">
          <Input
            type="number"
            min="0"
            value={filters.min_comments}
            onChange={(e) => setFilter("min_comments", e.target.value)}
            placeholder="e.g. 500"
          />
        </Field>
        <Field label="Min like ratio %">
          <Input
            type="number"
            min="0"
            max="100"
            step="0.1"
            value={filters.min_like_ratio}
            onChange={(e) => setFilter("min_like_ratio", e.target.value)}
            placeholder="e.g. 4"
          />
        </Field>
        <Field label="Min view velocity /hr">
          <Input
            type="number"
            min="0"
            value={filters.min_velocity}
            onChange={(e) => setFilter("min_velocity", e.target.value)}
            placeholder="e.g. 2000"
          />
        </Field>
        <Field label="Min positive %">
          <Input
            type="number"
            min="0"
            max="100"
            step="1"
            value={filters.min_positive_pct}
            onChange={(e) => setFilter("min_positive_pct", e.target.value)}
            placeholder="e.g. 60"
          />
        </Field>
        <Field label="Max negative %">
          <Input
            type="number"
            min="0"
            max="100"
            step="1"
            value={filters.max_negative_pct}
            onChange={(e) => setFilter("max_negative_pct", e.target.value)}
            placeholder="e.g. 20"
          />
        </Field>
        <Field label="Published within">
          <Select
            value={filters.published_within_days}
            onChange={(e) => setFilter("published_within_days", e.target.value)}
          >
            <option value="">Any time</option>
            <option value="1">Last 24 hours</option>
            <option value="3">Last 3 days</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
          </Select>
        </Field>
        <Field label="Transcript">
          <Select
            value={filters.has_transcript}
            onChange={(e) => setFilter("has_transcript", e.target.value)}
          >
            <option value="">Any</option>
            <option value="true">Has script</option>
            <option value="false">No script</option>
          </Select>
        </Field>
      </div>
    </div>
  );
}
