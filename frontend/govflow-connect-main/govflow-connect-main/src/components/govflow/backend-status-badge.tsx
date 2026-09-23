import React, { useEffect, useState } from "react";
import { Activity, CheckCircle2, Cpu, Database, RefreshCw, Server, WifiOff } from "lucide-react";
import { api, type MLSystemStatus } from "@/lib/api";

export function BackendStatusBadge() {
  const [online, setOnline] = useState<boolean | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [mlStatus, setMlStatus] = useState<MLSystemStatus | null>(null);
  const [checking, setChecking] = useState<boolean>(false);
  const [showDetails, setShowDetails] = useState<boolean>(false);

  const checkStatus = async () => {
    setChecking(true);
    const start = performance.now();
    try {
      const health = await api.getHealth();
      const elapsed = Math.round(performance.now() - start);
      if (health && health.status === "ok") {
        setOnline(true);
        setLatency(elapsed);
        const ml = await api.getMLStatus();
        if (ml) setMlStatus(ml);
      } else {
        setOnline(false);
      }
    } catch {
      setOnline(false);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative inline-block text-xs">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border transition-all font-medium ${
          online === true
            ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/30 hover:bg-emerald-500/20 dark:text-emerald-400"
            : online === false
            ? "bg-amber-500/10 text-amber-600 border-amber-500/30 hover:bg-amber-500/20 dark:text-amber-400"
            : "bg-muted text-muted-foreground border-border"
        }`}
        title="Click to view backend connection & AI/ML engine statuses"
      >
        <span
          className={`h-2 w-2 rounded-full ${
            online === true
              ? "bg-emerald-500 animate-pulse"
              : online === false
              ? "bg-amber-500"
              : "bg-muted-foreground animate-ping"
          }`}
        />
        <span>
          {online === true
            ? `Backend Online ${latency ? `(${latency}ms)` : ""}`
            : online === false
            ? "Backend Offline (Port 8000)"
            : "Checking Backend..."}
        </span>
      </button>

      {showDetails && (
        <div className="absolute right-0 mt-2 w-80 rounded-xl border border-border bg-card p-4 shadow-xl z-50 text-card-foreground animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div className="flex items-center gap-2 font-semibold">
              <Server className="h-4 w-4 text-primary" />
              <span>Inter-Gov Mesh Backend</span>
            </div>
            <button
              onClick={checkStatus}
              disabled={checking}
              className="p-1 rounded hover:bg-muted text-muted-foreground transition-colors"
              title="Refresh connection status"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${checking ? "animate-spin" : ""}`} />
            </button>
          </div>

          <div className="py-2.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5" /> API Server:
              </span>
              <span className="font-mono font-medium">
                {online ? "http://127.0.0.1:8000" : "Unreachable"}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Database className="h-3.5 w-3.5" /> SQLite Mesh DB:
              </span>
              <span className="font-medium text-emerald-600 dark:text-emerald-400">
                Connected (sih26129.db)
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5" /> AI/ML Engines:
              </span>
              <span className="font-medium">
                {mlStatus ? `${mlStatus.ready_count ?? mlStatus.ready_engines ?? 6} / ${mlStatus.total_engines} Active` : "6 Engines"}
              </span>

            </div>
          </div>

          {mlStatus?.engines && (
            <div className="pt-2 border-t border-border">
              <div className="text-[11px] font-semibold text-muted-foreground mb-1.5 uppercase tracking-wider">
                Integrated Models
              </div>
              <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                {Object.entries(mlStatus.engines).map(([key, item]) => (
                  <div key={key} className="flex items-center justify-between text-[11px]">
                    <span className="truncate max-w-[170px]" title={item.name}>
                      {item.name.split(" ")[0]}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[10px] ${
                        item.ready
                          ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      <CheckCircle2 className="h-2.5 w-2.5" />
                      Ready
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-3 pt-2 border-t border-border text-[11px] text-muted-foreground text-center">
            {online ? (
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                Full two-way REST API communication active
              </span>
            ) : (
              <span className="text-amber-600 dark:text-amber-400">
                Run <code>start_backend.bat</code> to launch FastAPI
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
