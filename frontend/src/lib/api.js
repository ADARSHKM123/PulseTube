// Thin fetch wrapper — same-origin /api in dev (vite proxy) and prod (nginx).
const BASE = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export function qs(params = {}) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, value);
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

async function request(path, options = {}) {
  let resp;
  try {
    resp = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
  } catch {
    throw new ApiError("Backend unreachable — is the API server running on port 8000?", 0);
  }
  if (resp.status === 204) return null;
  let body = null;
  try {
    body = await resp.json();
  } catch {
    /* non-JSON error body */
  }
  if (!resp.ok) {
    const detail =
      typeof body?.detail === "string" ? body.detail : body?.detail?.[0]?.msg || `Request failed (${resp.status})`;
    throw new ApiError(detail, resp.status);
  }
  return body;
}

export const api = {
  trends: (params) => request(`/api/trends${qs(params)}`),
  exportUrl: (params) => `${BASE}/api/trends/export.csv${qs(params)}`,
  overview: () => request("/api/stats/overview"),

  video: (id) => request(`/api/videos/${id}`),
  history: (id) => request(`/api/videos/${id}/history`),
  transcript: (id) => request(`/api/videos/${id}/transcript`),
  refreshVideo: (id) => request(`/api/videos/${id}/refresh`, { method: "POST" }),
  untrackVideo: (id) => request(`/api/videos/${id}`, { method: "DELETE" }),

  keywords: () => request("/api/keywords"),
  addKeyword: (keyword) => request("/api/keywords", { method: "POST", body: JSON.stringify({ keyword }) }),
  patchKeyword: (id, patch) =>
    request(`/api/keywords/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  deleteKeyword: (id) => request(`/api/keywords/${id}`, { method: "DELETE" }),

  status: () => request("/api/system/status"),
  runs: (limit = 30) => request(`/api/system/runs${qs({ limit })}`),
  triggerRun: () => request("/api/system/run", { method: "POST" }),
};
