import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef } from "react";
import {
  Activity,
  ArrowRight,
  Boxes,
  Building2,
  CheckCircle2,
  FileStack,
  Gauge,
  GitBranch,
  Landmark,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { Button } from "@/components/ui/button";
import { HealthPill, PageHeader, StatCard, StatusPill, Surface } from "@/components/govflow/bits";
import { EventFeed, useWorkflowRun } from "@/components/govflow/workflow";
import { AIDocumentVerifier } from "@/components/govflow/ai-document-verifier";
import { useGovFlow, useScopedApplications } from "@/lib/govflow/store";

import {
  AUDIT_LOGS,
  DEPARTMENTS,
  INTEGRATIONS,
  SERVICES,
  WORKFLOWS,
  applicationSeries,
  departmentPerf,
  getService,
  getWorkflow,
  latencySeries,
} from "@/lib/govflow/data";

export const Route = createFileRoute("/_app/dashboard")({
  head: () => ({
    meta: [
      { title: "Overview — GovFlow Control Centre" },
      {
        name: "description",
        content:
          "Live interoperability overview: active services, running workflows, system health, exceptions and department performance.",
      },
      { property: "og:title", content: "GovFlow Overview" },
      {
        property: "og:description",
        content: "Cross-department orchestration metrics in a single control centre.",
      },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const {
    user,
    location,
    exceptions,
    notifications,
    workflows,
    consents,
    updateApplication,
    pushNotification,
    isLive,
    liveStats,
  } = useGovFlow();
  const apps = useScopedApplications();
  const navigate = useNavigate();
  const load = location.load;

  const series = useMemo(() => applicationSeries(load), [load]);
  const latency = useMemo(() => latencySeries(load), [load]);
  const perf = useMemo(() => departmentPerf(load), [load]);

  const hero = workflows[0] ?? WORKFLOWS[0]!;
  const runner = useWorkflowRun(hero.stages, { speed: 1.25 });
  const completedRef = useRef(false);
  const workflowCompleted = runner.events.some(
    (event) => event.stage === "Completed" && event.status === "Success",
  );

  const runDemo = () => {
    completedRef.current = false;
    runner.run();
    pushNotification({
      title: "Workflow started",
      body: `Scholarship orchestration is running in ${location.city}.`,
      kind: "Workflow",
    });
  };

  useEffect(() => {
    if (!completedRef.current && !runner.running && workflowCompleted) {
      completedRef.current = true;
      updateApplication("SCH-10291", { status: "Completed", stageId: "completed" });
    }
  }, [runner.running, updateApplication, workflowCompleted]);

  const openExceptions = exceptions.filter((e) => e.status !== "Recovered").length;
  const completedStages = hero.stages.filter((stage) => runner.states[stage.id] === "done").length;
  const progressPercent = hero.stages.length
    ? Math.round((completedStages / hero.stages.length) * 100)
    : 0;
  const hasWorkflowErrors = runner.events.some((event) => event.status === "Failed");
  const workflowStatus = (() => {
    if (runner.running) {
      return hasWorkflowErrors
        ? "A stage encountered an error; recovery is in progress."
        : "Workflow is running.";
    }
    if (workflowCompleted) return "Workflow completed successfully.";
    if (hasWorkflowErrors) return "Workflow stopped with errors. Review the event feed.";
    return "Workflow stopped before completion.";
  })();
  const workflowStatusTone =
    hasWorkflowErrors && !runner.running && !workflowCompleted
      ? "text-danger"
      : "text-muted-foreground";

  const actualDepartment = user?.department ?? "Revenue Department";
  const roleView = user?.role === "Admin"
    ? "Interoperability Admin"
    : user?.role === "Department Officer"
      ? "Government Officer"
      : "System Admin";

  const pendingApplications = Math.max(12, apps.filter((application) => application.status === "Pending" || application.status === "In Progress").length || 12);
  const assignedToMe = Math.max(7, Math.round(pendingApplications * 0.56));
  const slaAtRisk = Math.max(3, Math.round(pendingApplications * 0.2));
  const interdepartmentalRequests = Math.max(5, consents.filter((consent) => consent.status === "Active").length + 2);
  const dataVerificationRequests = Math.max(4, Math.round(pendingApplications * 0.18));
  const completedToday = Math.max(8, Math.round(apps.length * 0.27));

  const connectedSystems = [
    { name: "Revenue", status: "Healthy", requests: 24, successRate: "99.3%", responseTime: "240ms", lastChecked: "2 mins ago" },
    { name: "Education", status: "Healthy", requests: 17, successRate: "98.9%", responseTime: "310ms", lastChecked: "3 mins ago" },
    { name: "Social Welfare", status: "Healthy", requests: 21, successRate: "99.1%", responseTime: "260ms", lastChecked: "1 min ago" },
    { name: "Transport", status: "Degraded", requests: 13, successRate: "98.7%", responseTime: "420ms", lastChecked: "4 mins ago" },
    { name: "Municipal", status: "Healthy", requests: 12, successRate: "98.5%", responseTime: "380ms", lastChecked: "5 mins ago" },
    { name: "Employment", status: "Healthy", requests: 10, successRate: "98.3%", responseTime: "460ms", lastChecked: "7 mins ago" },
  ];

  const queueItems = [
    { service: "Scholarship", stage: "Income verification", status: "Waiting for Revenue" },
    { service: "Driving Licence", stage: "Address verification", status: "Verified" },
    { service: "Pension", stage: "Employment verification", status: "Requires Review" },
  ];

  const recentTransactions = [
    { source: "Social Welfare", destination: "Revenue", dataType: "Income Certificate", status: "Completed", date: "2026-09-26" },
    { source: "Education", destination: "Social Welfare", dataType: "Education Record", status: "Completed", date: "2026-09-25" },
    { source: "Transport", destination: "Revenue", dataType: "Address Verification", status: "In Review", date: "2026-09-25" },
    { source: "Municipal", destination: "Employment", dataType: "Property Verification", status: "Completed", date: "2026-09-24" },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Government Interoperability Platform"
        title={`Department: ${actualDepartment}`}
        subtitle={`${user?.name ? `Officer: ${user.name} · ` : ""}${roleView} · ${location.city}, ${location.state}`}
        actions={
          <>
            <Button variant="outline" onClick={() => navigate({ to: "/$feature", params: { feature: "reports" } })}>
              View reports
            </Button>
            <Button
              onClick={runDemo}
              disabled={runner.running}
              aria-busy={runner.running}
              aria-label={
                runner.running
                  ? `${hero.name} workflow running`
                  : `Run ${hero.name} workflow`
              }
            >
              {runner.running ? "Workflow running" : "Run workflow"}
              <ArrowRight aria-hidden="true" className="ml-2 size-4" />
            </Button>
          </>
        }
      />

      <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={<Landmark className="size-5" />}
          label="Pending Applications"
          value={String(pendingApplications)}
          delta="Needs action"
          tone="warning"
          to="applications"
        />
        <StatCard
          icon={<FileStack className="size-5" />}
          label="Assigned to Me"
          value={String(assignedToMe)}
          delta="Current queue"
          tone="primary"
          to="applications"
        />
        <StatCard
          icon={<Gauge className="size-5" />}
          label="SLA At Risk"
          value={String(slaAtRisk)}
          delta="Escalate"
          tone="danger"
          to="exceptions"
        />
        <StatCard
          icon={<GitBranch className="size-5" />}
          label="Interdepartmental Requests"
          value={String(interdepartmentalRequests)}
          delta="Live"
          tone="teal"
          to="consent"
        />
        <StatCard
          icon={<ShieldCheck className="size-5" />}
          label="Data Verification Requests"
          value={String(dataVerificationRequests)}
          delta="Queue"
          tone="success"
          to="data-mapping"
        />
        <StatCard
          icon={<TriangleAlert className="size-5" />}
          label="Exceptions"
          value={String(openExceptions)}
          delta="Review"
          tone="danger"
          to="exceptions"
        />
        <StatCard
          icon={<CheckCircle2 className="size-5" />}
          label="Completed Today"
          value={String(completedToday)}
          delta="Processed"
          tone="success"
          to="reports"
        />
      </div>

      {runner.running || runner.events.length > 0 ? (
        <Surface className="mt-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-bold">Workflow run: {hero.name}</h2>
              <p role="status" aria-live="polite" className={`mt-1 text-sm ${workflowStatusTone}`}>
                {workflowStatus}
              </p>
            </div>
            <span className="text-sm font-semibold text-foreground">
              {completedStages} of {hero.stages.length} stages · {progressPercent}%
            </span>
          </div>
          <div
            className="mt-3 h-2 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-label="Workflow progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progressPercent}
          >
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <h3 className="mt-5 text-sm font-semibold">Run events</h3>
          <div className="mt-3 max-h-80 overflow-y-auto">
            <EventFeed events={runner.events} />
          </div>
        </Surface>
      ) : null}

      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)]">
        <Surface>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Interoperability Hub</p>
              <h2 className="mt-2 text-xl font-bold">Connected Government Systems</h2>
            </div>
            <span className="inline-flex items-center gap-2 rounded-full border border-success/25 bg-success/10 px-2.5 py-1 text-[11px] font-semibold text-success">
              <span className="size-1.5 rounded-full bg-current" /> Operational
            </span>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {connectedSystems.map((item) => (
              <div key={item.name} className="rounded-xl border border-border bg-muted/25 p-3">
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-sm font-semibold">{item.name}</strong>
                  <HealthPill health={item.status as "Healthy" | "Degraded" | "Down"} />
                </div>
                <div className="mt-3 space-y-2 text-[11px] text-muted-foreground">
                  <div className="flex justify-between"><span>Requests</span><span className="font-medium text-foreground">{item.requests}</span></div>
                  <div className="flex justify-between"><span>Success Rate</span><span className="font-medium text-foreground">{item.successRate}</span></div>
                  <div className="flex justify-between"><span>Response Time</span><span className="font-medium text-foreground">{item.responseTime}</span></div>
                  <div className="flex justify-between"><span>Last Checked</span><span className="font-medium text-foreground">{item.lastChecked}</span></div>
                </div>
              </div>
            ))}
          </div>
        </Surface>

        <Surface>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Live Transaction</p>
          <h2 className="mt-2 text-xl font-bold">TXN-2026-00821</h2>
          <div className="mt-4 space-y-3 rounded-xl border border-border bg-muted/20 p-3 text-sm">
            <div className="flex items-center justify-between"><span>Source</span><strong>Social Welfare</strong></div>
            <div className="text-center text-muted-foreground">↓</div>
            <div className="flex items-center justify-between"><span>Gateway</span><strong>GovFlow</strong></div>
            <div className="text-center text-muted-foreground">↓</div>
            <div className="flex items-center justify-between"><span>Destination</span><strong>Revenue</strong></div>
            <div className="text-center text-muted-foreground">↓</div>
            <div className="flex items-center justify-between"><span>Return</span><strong>GovFlow</strong></div>
            <div className="text-center text-muted-foreground">↓</div>
            <div className="flex items-center justify-between"><span>Recipient</span><strong>Social Welfare</strong></div>
          </div>
          <dl className="mt-4 grid gap-2 text-xs text-muted-foreground">
            <div className="flex justify-between"><dt>Data</dt><dd className="font-medium text-foreground">Income Certificate</dd></div>
            <div className="flex justify-between"><dt>Consent</dt><dd className="font-medium text-foreground">Granted</dd></div>
            <div className="flex justify-between"><dt>Validation</dt><dd className="font-medium text-foreground">Passed</dd></div>
            <div className="flex justify-between"><dt>Normalization</dt><dd className="font-medium text-foreground">Completed</dd></div>
            <div className="flex justify-between"><dt>Status</dt><dd className="font-medium text-success">Completed</dd></div>
          </dl>
        </Surface>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(300px,0.9fr)]">
        <Surface>
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-bold">Application Queue</h2>
            <Link to="/$feature" params={{ feature: "applications" }} className="text-xs font-semibold text-primary">
              View all queue
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {queueItems.map((item) => (
              <div key={item.service} className="rounded-xl border border-border bg-muted/20 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold">{item.service}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{item.stage}</div>
                  </div>
                  <StatusPill status={item.status} />
                </div>
              </div>
            ))}
          </div>
        </Surface>

        <Surface>
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-bold">Recent Transactions</h2>
            <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">Filters</span>
          </div>
          <div className="mt-4 overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/30 text-left text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                <tr>
                  <th className="px-3 py-2">Source</th>
                  <th className="px-3 py-2">Destination</th>
                  <th className="px-3 py-2">Data</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Date</th>
                </tr>
              </thead>
              <tbody>
                {recentTransactions.map((entry) => (
                  <tr key={`${entry.source}-${entry.date}`} className="border-t border-border">
                    <td className="px-3 py-2 text-xs">{entry.source}</td>
                    <td className="px-3 py-2 text-xs">{entry.destination}</td>
                    <td className="px-3 py-2 text-xs">{entry.dataType}</td>
                    <td className="px-3 py-2"><StatusPill status={entry.status} /></td>
                    <td className="px-3 py-2 text-xs">{entry.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Surface>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <Surface className="lg:col-span-2">
          <h2 className="text-base font-bold">Operational Summary</h2>
          <div className="mt-4 h-65">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="month" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis tickLine={false} axisLine={false} fontSize={12} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid var(--border)" }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="completed" fill="var(--chart-2)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="inProgress" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="pending" fill="var(--chart-3)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="failed" fill="var(--chart-4)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Surface>

        <div className="space-y-4">
          <Surface>
            <h2 className="text-base font-bold">Exceptions</h2>
            <p className="mt-1 text-3xl font-bold text-warning">{openExceptions}</p>
            <p className="text-sm text-muted-foreground">Open exceptions awaiting recovery</p>
            <Button variant="outline" size="sm" className="mt-4 w-full" asChild>
              <Link to="/$feature" params={{ feature: "exceptions" }}>
                <TriangleAlert className="mr-2 size-4" /> Resolve exceptions
              </Link>
            </Button>
          </Surface>
          <Surface>
            <h2 className="text-base font-bold">Audit Trail</h2>
            <p className="mt-1 text-3xl font-bold text-primary">{AUDIT_LOGS.length}</p>
            <p className="text-sm text-muted-foreground">Recent operational activity</p>
            <Button variant="outline" size="sm" className="mt-4 w-full" asChild>
              <Link to="/$feature" params={{ feature: "audit-logs" }}>
                Open audit trail
              </Link>
            </Button>
          </Surface>
        </div>
      </div>

      <AIDocumentVerifier />

      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          { feature: "workflows", detail: "builder", icon: GitBranch, label: "Workflow Engine" },
          { feature: "integrations", icon: Boxes, label: "Connected Systems" },
          { feature: "data-mapping", icon: Activity, label: "Data Mapping" },
          { feature: "consent", icon: ShieldCheck, label: "Consent Requests" },
          { feature: "monitoring", icon: Gauge, label: "System Health" },
          { feature: "applications", icon: FileStack, label: "My Queue" },
        ].map((q) => (
          <Link
            key={q.feature}
            to={q.detail ? "/$feature/$id" : "/$feature"}
            params={q.detail ? { feature: q.feature, id: q.detail } : { feature: q.feature }}
            className="surface flex items-center gap-3 p-4 transition-colors hover:bg-muted/50"
          >
            <span className="grid size-10 place-items-center rounded-xl bg-accent">
              <q.icon className="size-5 text-accent-foreground" />
            </span>
            <span className="text-sm font-semibold">{q.label}</span>
            <ArrowRight className="ml-auto size-4 text-muted-foreground" />
          </Link>
        ))}
      </div>
    </>
  );
}
