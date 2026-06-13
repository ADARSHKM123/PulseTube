import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";
import { useToast } from "./ToastContext.jsx";

const StatusContext = createContext(null);
const POLL_MS = 30_000;
const POLL_RUNNING_MS = 5_000; // tighten the loop while a cycle is in flight

/** Shared pipeline/quota status, polled app-wide (topbar + system page). */
export function StatusProvider({ children }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const toast = useToast();
  const timerRef = useRef(null);
  const wasRunningRef = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const s = await api.status();
      setStatus(s);
      setError(null);
      if (wasRunningRef.current && !s.pipeline_running) {
        toast(`Ingestion run finished: ${s.last_run?.status ?? "done"}`, "success");
      }
      wasRunningRef.current = s.pipeline_running;
      return s;
    } catch (err) {
      setError(err);
      return null;
    }
  }, [toast]);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      const s = await refresh();
      if (cancelled) return;
      timerRef.current = setTimeout(tick, s?.pipeline_running ? POLL_RUNNING_MS : POLL_MS);
    };
    tick();
    return () => {
      cancelled = true;
      clearTimeout(timerRef.current);
    };
  }, [refresh]);

  const triggerRun = useCallback(async () => {
    try {
      await api.triggerRun();
      toast("Ingestion run started — discovering products…", "info");
      wasRunningRef.current = true;
      setStatus((s) => (s ? { ...s, pipeline_running: true } : s));
      setTimeout(refresh, 1500);
    } catch (err) {
      toast(err.message, "error");
    }
  }, [refresh, toast]);

  return (
    <StatusContext.Provider value={{ status, error, refresh, triggerRun }}>{children}</StatusContext.Provider>
  );
}

export function useStatus() {
  const ctx = useContext(StatusContext);
  if (!ctx) throw new Error("useStatus must be used inside <StatusProvider>");
  return ctx;
}
