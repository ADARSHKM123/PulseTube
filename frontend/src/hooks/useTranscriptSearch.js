import { useMemo } from "react";

/** Split transcript into matched / unmatched segments for highlight rendering. */
export function useMemoizedSearch(content, query) {
  return useMemo(() => {
    const text = content || "";
    const q = query.trim();
    if (!q) return [{ text, match: false }];
    // Escape regex metacharacters from user input
    const safe = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`(${safe})`, "gi");
    const lowerQ = q.toLowerCase();
    // String.split with a capture group keeps the delimiters; a piece is a
    // match when it equals the query case-insensitively (no shared regex state).
    return text
      .split(re)
      .filter((s) => s !== "")
      .map((s) => ({ text: s, match: s.toLowerCase() === lowerQ }));
  }, [content, query]);
}
