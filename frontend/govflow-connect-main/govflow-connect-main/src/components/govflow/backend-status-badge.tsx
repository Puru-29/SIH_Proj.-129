import { useCallback, useEffect, useState } from "react";
import { Activity, RefreshCw } from "lucide-react";
import type { SystemHealth } from "@/lib/api";
import { connectorService } from "@/services/connectorService";

export function BackendStatusBadge() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [checking, setChecking] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const checkStatus = useCallback(async () => {
    setChecking(true);
    try {
      setHealth(await connectorService.runConnectorHealthChecks());
    } catch {
      setHealth(null);
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    void checkStatus();
    const interval = window.setInterval(() => void checkStatus(), 30_000);
    return () => window.clearInterval(interval);
  }, [checkStatus]);

  const healthyCount =
    health?.integrations.filter((integration) => integration.status === "healthy").length ?? 0;
  const statusLabel = health
    ? `${healthyCount}/${health.integrations.length} connectors healthy`
    : checking
      ? "Checking connector health"
      : "Connector health unavailable";

  return (
    <div className="relative inline-block text-xs">
      <button
        onClick={() => setShowDetails((visible) => !visible)}
        className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-medium transition-all ${
          health?.status === "healthy"
            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400"
            : "border-border bg-muted text-muted-foreground"
        }`}
        title="Live connector health-check results"
      >
        <span
          className={`h-2 w-2 rounded-full ${
            health?.status === "healthy" ? "animate-pulse bg-emerald-500" : "bg-muted-foreground"
          }`}
        />
        <span>{statusLabel}</span>
      </button>

      {showDetails ? (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-border bg-card p-4 text-card-foreground shadow-xl">
          <div className="flex items-center justify-between border-b border-border pb-2">
            <div className="flex items-center gap-2 font-semibold">
              <Activity className="size-4 text-primary" />
              <span>Connector health</span>
            </div>
            <button
              onClick={() => void checkStatus()}
              disabled={checking}
              className="rounded p-1 text-muted-foreground transition-colors hover:bg-muted"
              title="Refresh connector health"
            >
              <RefreshCw className={`size-3.5 ${checking ? "animate-spin" : ""}`} />
            </button>
          </div>
          {health ? (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-muted-foreground">
                {health.status.toUpperCase()} · {healthyCount}/{health.integrations.length} healthy
              </p>
              {health.integrations.map((integration) => (
                <div
                  key={integration.id}
                  className="flex items-center justify-between gap-2 text-xs"
                >
                  <span className="truncate">{integration.name}</span>
                  <span className="shrink-0 text-muted-foreground">
                    {integration.status} · {integration.response_time} ms
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-xs text-muted-foreground">
              Connector health could not be retrieved. Try again later.
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
