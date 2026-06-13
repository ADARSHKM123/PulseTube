import { useMemoizedSearch } from "../../hooks/useTranscriptSearch.js";
import { Search } from "lucide-react";
import { useState } from "react";
import { Input } from "../ui/Input.jsx";

const STATUS_COPY = {
  pending: "Transcript not fetched yet — the next ingestion run will attempt it.",
  unavailable: "No transcript available — this video has captions disabled.",
  error: "Transcript fetch failed — it will be retried on an upcoming run.",
};

/** Full video script with in-text search + highlight (the "video script" deliverable). */
export default function TranscriptPanel({ transcript }) {
  const [query, setQuery] = useState("");
  const status = transcript?.status || "pending";
  // Hook must run unconditionally — compute before any early return.
  const segments = useMemoizedSearch(transcript?.content || "", query);

  if (status !== "ok" || !transcript?.content) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm text-muted">
        {STATUS_COPY[status] || STATUS_COPY.pending}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-line p-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search transcript…"
            className="h-8 pl-8 text-xs"
          />
        </div>
        <span className="num shrink-0 text-[11px] text-muted">{transcript.word_count} words</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-fg/90">
          {segments.map((seg, i) =>
            seg.match ? (
              <mark key={i} className="rounded bg-warning/40 px-0.5 text-fg">
                {seg.text}
              </mark>
            ) : (
              <span key={i}>{seg.text}</span>
            )
          )}
        </p>
      </div>
      <div className="border-t border-line px-4 py-2 text-[11px] text-muted">
        Source: {transcript.source || "—"}
        {transcript.language ? ` · ${transcript.language}` : ""}
      </div>
    </div>
  );
}
