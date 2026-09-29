import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  FileCheck2,
  RefreshCw,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader, StatusPill, Surface } from "@/components/govflow/bits";
import type { GovernmentDashboard } from "@/lib/api";
import { analyticsService } from "@/services/analyticsService";

export const Route = createFileRoute("/_app/dashboard")({
  component: GovernmentDashboardPage,
});

function GovernmentDashboardPage() {
  const [dashboard, setDashboard] = useState<GovernmentDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      setDashboard(await analyticsService.getGovernmentDashboard());
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Government dashboard could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), 15_000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  const counts = dashboard?.counts;
  const metrics = counts
    ? ([
        {
          label: "Pending Applications",
          value: counts.pending_applications,
          icon: ClipboardList,
          tone: "bg-primary/10 text-primary",
        },
        {
          label: "Assigned to Me",
          value: counts.assigned_to_me,
          icon: Users,
          tone: "bg-teal/15 text-teal",
        },
        {
          label: "SLA At Risk",
          value: counts.sla_at_risk,
          icon: AlertTriangle,
          tone: "bg-warning/20 text-warning",
        },
        {
          label: "Interdepartmental Requests",
          value: counts.interdepartmental_requests,
          icon: Activity,
          tone: "bg-primary/10 text-primary",
        },
        {
          label: "Data Verification Requests",
          value: counts.data_verification_requests,
          icon: FileCheck2,
          tone: "bg-teal/15 text-teal",
        },
        {
          label: "Exceptions",
          value: counts.open_exceptions,
          icon: AlertTriangle,
          tone: "bg-danger/15 text-danger",
        },
        {
          label: "Completed Today",
          value: counts.completed_today,
          icon: CheckCircle2,
          tone: "bg-success/15 text-success",
        },
      ] as const)
    : [];

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Government Operations"
        title="Overview"
        subtitle={
          dashboard?.department_name
            ? `${dashboard.department_name} · Live operational data`
            : "Live operational data from the government service backend."
        }
        actions={
          <Button variant="outline" onClick={() => void refresh()} disabled={loading}>
            <RefreshCw className="mr-2 size-4" /> Refresh
          </Button>
        }
      />

      {error ? (
        <Surface>
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
          {!dashboard ? (
            <Button className="mt-3" variant="outline" onClick={() => void refresh()}>
              Retry loading dashboard
            </Button>
          ) : null}
        </Surface>
      ) : null}

      {loading && !dashboard ? (
        <Surface>
          <p className="text-sm text-muted-foreground">Loading government dashboard…</p>
        </Surface>
      ) : null}

      {dashboard ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {metrics.map(({ label, value, icon: Icon, tone }) => (
              <Surface key={label} className="flex min-h-28 items-center gap-3">
                <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${tone}`}>
                  <Icon className="size-5" />
                </span>
                <div className="min-w-0">
                  <p className="text-2xl font-bold tabular-nums">{value.toLocaleString()}</p>
                  <p className="text-sm font-medium text-muted-foreground">{label}</p>
                </div>
              </Surface>
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
            <Surface>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-bold">Application queue</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Applications currently awaiting processing.
                  </p>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link to="/$feature" params={{ feature: "applications" }}>
                    View all <ArrowRight className="ml-1 size-4" />
                  </Link>
                </Button>
              </div>
              {dashboard.application_queue.length ? (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="px-2 py-2 font-semibold">Application</th>
                        <th className="px-2 py-2 font-semibold">Citizen / service</th>
                        <th className="px-2 py-2 font-semibold">Current step</th>
                        <th className="px-2 py-2 font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {dashboard.application_queue.map((application) => (
                        <tr key={application.id}>
                          <td className="px-2 py-3 font-semibold">
                            <Link
                              className="text-primary hover:underline"
                              to="/applications/$id"
                              params={{ id: String(application.id) }}
                            >
                              {application.reference_id}
                            </Link>
                          </td>
                          <td className="px-2 py-3">
                            <span className="block">{application.citizen_name || "Citizen"}</span>
                            <span className="text-xs text-muted-foreground">
                              {application.service_name}
                            </span>
                          </td>
                          <td className="px-2 py-3">
                            {application.current_step?.name || "—"}
                            {application.sla_due_at ? (
                              <span className="block text-xs text-muted-foreground">
                                Due {formatDate(application.sla_due_at)}
                              </span>
                            ) : null}
                          </td>
                          <td className="px-2 py-3">
                            <StatusPill status={formatStatus(application.status)} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted-foreground">
                  No pending applications in this scope.
                </p>
              )}
            </Surface>

            <Surface>
              <h2 className="text-base font-bold">Interdepartmental requests</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Latest open requests between departments.
              </p>
              <div className="mt-4 space-y-3">
                {dashboard.recent_requests.length ? (
                  dashboard.recent_requests.map((request) => (
                    <Link
                      key={request.transaction_id}
                      to="/applications/$id"
                      params={{ id: String(request.application_id) }}
                      className="block rounded-lg border border-border p-3 transition-colors hover:border-primary/40"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-semibold">{request.reference_id}</span>
                        <StatusPill status={formatStatus(request.status)} />
                      </div>
                      <p className="mt-1 text-sm">
                        {request.source_department} → {request.requesting_department}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {request.data_requested} · {request.service_name}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatDate(request.requested_at)}
                      </p>
                    </Link>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No open interdepartmental requests.
                  </p>
                )}
              </div>
            </Surface>
          </div>

          <p className="text-right text-xs text-muted-foreground">
            Backend data generated {formatDate(dashboard.generated_at)}
          </p>
        </>
      ) : null}
    </div>
  );
}

function formatStatus(status: string) {
  return status.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}
