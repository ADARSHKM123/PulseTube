import { useMemo, useState } from "react";
import { useDebounced } from "../../hooks/useApi.js";

export const DEFAULT_FILTERS = {
  q: "",
  min_views: "",
  min_likes: "",
  min_comments: "",
  min_like_ratio: "",
  min_positive_pct: "",
  max_negative_pct: "",
  min_velocity: "",
  published_within_days: "",
  has_transcript: "",
};

/** Holds raw filter inputs + sort state, and derives the debounced API query. */
export function useTrendFilters() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [sort, setSort] = useState("views");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(1);

  const debouncedFilters = useDebounced(filters, 350);

  const setFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const reset = () => {
    setFilters(DEFAULT_FILTERS);
    setPage(1);
  };

  const toggleSort = (column) => {
    setPage(1);
    if (sort === column) {
      setOrder((o) => (o === "desc" ? "asc" : "desc"));
    } else {
      setSort(column);
      setOrder("desc");
    }
  };

  // Build the param object the API + CSV export both consume.
  const queryParams = useMemo(() => {
    const params = { sort, order };
    for (const [key, value] of Object.entries(debouncedFilters)) {
      if (value !== "" && value !== null) params[key] = value;
    }
    return params;
  }, [debouncedFilters, sort, order]);

  const activeCount = useMemo(
    () => Object.entries(debouncedFilters).filter(([, v]) => v !== "" && v !== null).length,
    [debouncedFilters]
  );

  return {
    filters,
    setFilter,
    reset,
    sort,
    order,
    toggleSort,
    page,
    setPage,
    queryParams,
    activeCount,
  };
}
