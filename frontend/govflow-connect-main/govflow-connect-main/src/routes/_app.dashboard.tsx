import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
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
import { EventFeed, useWorkflowRun, WorkflowCanvas } from "@/components/govflow/workflow";
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
  const [selectedStage, setSelectedStage] = useState<string | null>(null);

  const runDemo = () => {
    completedRef.current = false;
    runner.run();
    pushNotification({
      title: "Demo workflow started",
      body: `Scholarship orchestration is running in ${location.city}.`,
      kind: "Workflow",
    });
  };

  useEffect(() => {
    if (
      !completedRef.current &&
      !runner.running &&
      runner.events.some((event) => event.stage === "Completed" && event.status === "Success")
    ) {
      completedRef.current = true;
      updateApplication("SCH-10291", { status: "Completed", stageId: "completed" });
    }
  }, [runner.running, runner.events, updateApplication]);

  const openExceptions = exceptions.filter((e) => e.status !== "Recovered").length;

  return (
    <>
      <PageHeader
        eyebrow={isLive ? "● Connected to FastAPI Live Backend (SQLite)" : "Government Interoperability Platform"}
        title={`Good morning, ${user?.name?.split(" ")[0] ?? "Officer"}`}
        subtitle={`Live e-Governance Interoperability Mesh · Real-time DB Records · ${location.city}, ${location.state}`}
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => navigate({ to: "/$feature", params: { feature: "reports" } })}
            >
              View reports
            </Button>
            <Button onClick={runDemo} disabled={runner.running}>
              {runner.running ? "Workflow running" : "Run demo workflow"}{" "}
              <ArrowRight className="ml-2 size-4" />
            </Button>
            {runner.running ? (
              <Button variant="outline" onClick={runner.pause}>
                Pause
              </Button>
            ) : null}
            {runner.paused ? (
              <Button variant="outline" onClick={runner.resume}>
                Resume
              </Button>
            ) : null}
            <Button
              variant="outline"
              onClick={runner.simulateFailure}
              disabled={runner.failureRequested}
            >
              Simulate failure
            </Button>
            <Button variant="ghost" onClick={runner.reset}>
              Reset
            </Button>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard
          icon={<Landmark className="size-5" />}
          label="Active Services"
          value={String(liveStats?.total_services ?? SERVICES.length)}
          delta={isLive ? "Live DB" : "+12%"}
          tone="teal"
        />
        <StatCard
          icon={<GitBranch className="size-5" />}
          label="Mesh Nodes"
          value={String(liveStats?.total_mesh_nodes ?? 6)}
          delta={isLive ? "6 Active" : "+8%"}
        />
        <StatCard
          icon={<Gauge className="size-5" />}
          label="API Success Rate"
          value={liveStats ? `${liveStats.api_success_rate.toFixed(1)}%` : "98.7%"}
          delta={isLive ? "FastAPI 200 OK" : "+0.4%"}
          tone="success"
        />
        <StatCard
          icon={<Building2 className="size-5" />}
          label="Departments Connected"
          value={String(liveStats?.total_departments ?? DEPARTMENTS.length)}
          delta={isLive ? "5 State Depts" : "+2"}
          tone="warning"
        />
        <StatCard
          icon={<FileStack className="size-5" />}
          label="Live Applications"
          value={String(liveStats?.total_applications ?? apps.length)}
          delta={isLive ? "Database Real-time" : "+18%"}
          tone="danger"
        />
      </div>


      <div className="grid gap-4 lg:grid-cols-3">
        <Surface className="lg:col-span-2">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
            <div className="min-w-0">
              <h2 className="truncate text-base font-bold">Live Workflow Execution</h2>
              <p className="truncate text-sm text-muted-foreground">
                Scholarship Application · #SCH-10291 · Ramesh Patil · {location.city}
              </p>
            </div>
            <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-success/25 bg-success/10 px-2.5 py-1 text-xs font-semibold text-success">
              <span className="size-1.5 animate-pulse rounded-full bg-current" /> Live
            </span>
          </div>
          <div className="mt-4">
            <WorkflowCanvas
              stages={hero.stages}
              states={runner.states}
              activeId={runner.activeId}
              onSelect={(stage) =>
                setSelectedStage(`${stage.name} · ${stage.department} · ${stage.system}`)
              }
              compact
            />
          </div>
          {selectedStage ? (
            <p className="mt-3 rounded-lg bg-muted/60 px-3 py-2 text-xs text-muted-foreground">
              Selected stage: {selectedStage}
            </p>
          ) : null}
          {runner.events.length ? (
            <div className="mt-4">
              <EventFeed events={runner.events.slice(-3)} />
            </div>
          ) : null}
          <div className="mt-4">
            <Button variant="outline" size="sm" asChild>
              <Link to="/applications/$id" params={{ id: "SCH-10291" }}>
                View citizen journey <ArrowRight className="ml-2 size-4" />
              </Link>
            </Button>
          </div>
        </Surface>

        <Surface>
          <h2 className="text-base font-bold">Interoperability Network</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {location.systems} connected systems in scope
          </p>
          <ul className="mt-4 space-y-3">
            {INTEGRATIONS.slice(0, 5).map((i) => (
              <li key={i.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{i.name}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {i.protocol} · {i.latencyMs} ms
                  </p>
                </div>
                <HealthPill health={i.health} />
              </li>
            ))}
          </ul>
          <Button variant="ghost" size="sm" className="mt-4 w-full" asChild>
            <Link to="/$feature" params={{ feature: "integrations" }}>
              Open integration workspace
            </Link>
          </Button>
        </Surface>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Surface className="lg:col-span-2">
          <h2 className="text-base font-bold">Application Statistics</h2>
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

        <Surface>
          <h2 className="text-base font-bold">Recent Activity</h2>
          <ul className="mt-4 space-y-3">
            {AUDIT_LOGS.slice(0, 6).map((a) => (
              <li key={a.id} className="flex items-start gap-3">
                {a.result === "Success" ? (
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" />
                ) : (
                  <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning" />
                )}
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{a.action}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {a.entity} · {a.time}
                  </p>
                </div>
              </li>
            ))}
          </ul>
          <Button variant="ghost" size="sm" className="mt-4 w-full" asChild>
            <Link to="/$feature" params={{ feature: "audit-logs" }}>
              View all audit logs
            </Link>
          </Button>
        </Surface>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Surface className="lg:col-span-2">
          <h2 className="text-base font-bold">Department System Health</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-130 text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground uppercase">
                  <th className="pb-2 font-semibold">Department</th>
                  <th className="pb-2 font-semibold">Status</th>
                  <th className="pb-2 font-semibold">Response</th>
                  <th className="pb-2 font-semibold">Uptime</th>
                </tr>
              </thead>
              <tbody>
                {DEPARTMENTS.map((d) => (
                  <tr key={d.id} className="border-b border-border/60 last:border-0">
                    <td className="py-2.5 font-medium">{d.name}</td>
                    <td className="py-2.5">
                      <HealthPill health={d.health} />
                    </td>
                    <td className="py-2.5">{d.responseMs} ms</td>
                    <td className="py-2.5">{d.uptime}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Surface>

        <div className="space-y-4">
          <Surface>
            <h2 className="text-base font-bold">Exceptions</h2>
            <p className="mt-1 text-3xl font-bold text-warning">{openExceptions}</p>
            <p className="text-sm text-muted-foreground">open exceptions awaiting recovery</p>
            <Button variant="outline" size="sm" className="mt-4 w-full" asChild>
              <Link to="/$feature" params={{ feature: "exceptions" }}>
                <TriangleAlert className="mr-2 size-4" /> Resolve exceptions
              </Link>
            </Button>
          </Surface>
          <Surface>
            <h2 className="text-base font-bold">Notifications</h2>
            <p className="mt-1 text-3xl font-bold text-primary">
              {notifications.filter((n) => !n.read).length}
            </p>
            <p className="text-sm text-muted-foreground">unread platform alerts</p>
            <Button variant="outline" size="sm" className="mt-4 w-full" asChild>
              <Link to="/$feature" params={{ feature: "notifications" }}>
                Open notifications
              </Link>
            </Button>
          </Surface>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Surface>
          <h2 className="text-base font-bold">API Latency &amp; Success (24h)</h2>
          <div className="mt-4 h-60">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={latency}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="t" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis tickLine={false} axisLine={false} fontSize={12} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid var(--border)" }} />
                <Line
                  type="monotone"
                  dataKey="latency"
                  stroke="var(--chart-1)"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="success"
                  stroke="var(--chart-2)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Surface>

        <Surface>
          <h2 className="text-base font-bold">Department Performance</h2>
          <div className="mt-4 h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={perf} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                <XAxis type="number" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={110}
                  tickLine={false}
                  axisLine={false}
                  fontSize={11}
                />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid var(--border)" }} />
                <Bar dataKey="processed" fill="var(--chart-1)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Surface>
      </div>

      <Surface>
        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
          <h2 className="truncate text-base font-bold">Applications in {location.city}</h2>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/$feature" params={{ feature: "applications" }}>
              View all
            </Link>
          </Button>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-160 text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground uppercase">
                <th className="pb-2 font-semibold">ID</th>
                <th className="pb-2 font-semibold">Citizen</th>
                <th className="pb-2 font-semibold">Service</th>
                <th className="pb-2 font-semibold">Stage</th>
                <th className="pb-2 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {apps.slice(0, 6).map((a) => {
                const service = getService(a.serviceId);
                const wf = service ? getWorkflow(service.workflowId) : WORKFLOWS[0]!;
                return (
                  <tr key={a.id} className="border-b border-border/60 last:border-0">
                    <td className="py-2.5">
                      <Link
                        to="/$feature/$id"
                        params={{ feature: "applications", id: a.id }}
                        className="font-semibold text-primary"
                      >
                        {a.id}
                      </Link>
                    </td>
                    <td className="py-2.5">{a.citizen}</td>
                    <td className="py-2.5">{service?.name || a.serviceId}</td>
                    <td className="py-2.5">{wf.stages.find((s) => s.id === a.stageId)?.name || a.stageId}</td>
                    <td className="py-2.5">
                      <StatusPill status={a.status} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Surface>

      <AIDocumentVerifier />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          { feature: "workflows", detail: "builder", icon: GitBranch, label: "Create Workflow" },
          { feature: "integrations", icon: Boxes, label: "Add Integration" },
          { feature: "data-mapping", icon: Activity, label: "Data Mapping" },
          { feature: "consent", icon: ShieldCheck, label: "Manage Consent" },
          { feature: "monitoring", icon: Gauge, label: "System Health" },
          { feature: "applications", icon: FileStack, label: "View Applications" },
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
