import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";
import {
  Activity,
  ArrowRight,
  Boxes,
  Building2,
  FileStack,
  FileText,
  GitBranch,
  Gauge,
  Landmark,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Shuffle,
  TriangleAlert,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, StatusPill, Surface, HealthPill } from "@/components/govflow/bits";
import {
  APPLICATIONS,
  AUDIT_LOGS,
  BOTTLENECKS,
  CONSENTS,
  DEPENDENCY_EDGES,
  DEPENDENCY_NODES,
  DEPARTMENTS,
  EXCEPTIONS,
  INTEGRATIONS,
  LOCATIONS,
  IMPACT_METRICS,
  SERVICES,
  USERS,
  WORKFLOWS,
  getService,
  getWorkflow,
  type FieldMap,
} from "@/lib/govflow/data";
import { useGovFlow, useScopedApplications } from "@/lib/govflow/store";

export const Route = createFileRoute("/_app/$feature")({
  component: FeatureRoute,
});

function FeatureRoute() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  return pathname.split("/").filter(Boolean).length > 1 ? <Outlet /> : <FeaturePage />;
}

const META: Record<string, { title: string; description: string; icon: typeof Activity }> = {
  services: {
    title: "Services",
    description: "Manage citizen services and their connected workflows.",
    icon: Landmark,
  },
  workflows: {
    title: "Workflows",
    description: "Monitor and operate cross-department service orchestration.",
    icon: GitBranch,
  },
  applications: {
    title: "Applications",
    description: "Track citizen applications across every processing stage.",
    icon: FileStack,
  },
  departments: {
    title: "Departments",
    description: "View department ownership, service coverage and system health.",
    icon: Building2,
  },
  integrations: {
    title: "Integrations",
    description: "Operate the systems connected to the GovFlow network.",
    icon: Boxes,
  },
  "data-mapping": {
    title: "Data Mapping",
    description: "Review how fields move between connected government systems.",
    icon: Shuffle,
  },
  consent: {
    title: "Consent Management",
    description: "Review and manage citizen data-sharing permissions.",
    icon: ShieldCheck,
  },
  monitoring: {
    title: "Monitoring",
    description: "Observe API health, response time and platform reliability.",
    icon: Activity,
  },
  exceptions: {
    title: "Exceptions",
    description: "Recover failed workflow stages and escalate operational issues.",
    icon: TriangleAlert,
  },
  "audit-logs": {
    title: "Audit Logs",
    description: "Trace every access, workflow change and system event.",
    icon: FileText,
  },
  reports: {
    title: "Reports",
    description: "Review operational performance across services and departments.",
    icon: Gauge,
  },
  users: {
    title: "Users",
    description: "Manage platform access for officers and operators.",
    icon: Users,
  },
  settings: {
    title: "Settings",
    description: "Configure the workspace and operational preferences.",
    icon: Settings,
  },
  notifications: {
    title: "Notifications",
    description: "Review platform alerts and workflow updates.",
    icon: TriangleAlert,
  },
  profile: {
    title: "Profile",
    description: "Review your GovFlow account and access details.",
    icon: Users,
  },
};

function FeaturePage() {
  const { feature } = Route.useParams();
  const meta = META[feature] ?? {
    title: "Workspace",
    description: "GovFlow workspace",
    icon: Activity,
  };
  const Icon = meta.icon;
  const [query, setQuery] = useState("");
  const [notice, setNotice] = useState("");
  const {
    exceptions,
    updateException,
    consents,
    updateConsent,
    notifications,
    markRead,
    user,
    location,
    workflows,
    integrations,
    mappings,
    saveMapping,
    lastUpdated,
    locationId,
    setLocationId,
    consentHistory,
  } = useGovFlow();
  const scopedApplications = useScopedApplications();
  const scopedApplicationIds = new Set(scopedApplications.map((application) => application.id));
  const lowerQuery = query.toLowerCase();
  const [sessionTimeout, setSessionTimeout] = useState("30");
  const [auditRetention, setAuditRetention] = useState("7");

  const showNotice = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 2400);
  };

  if (feature === "data-mapping") {
    const integrationId = query.startsWith("integration:")
      ? query.slice("integration:".length)
      : "int-aadhaar";
    const currentMapping = mappings[integrationId] ?? [];
    const mappedRows = currentMapping.filter((item) =>
      `${item.source} ${item.target} ${item.status}`
        .toLowerCase()
        .includes(lowerQuery.replace(`integration:${integrationId}`, "")),
    );
    const validate = (mappingToValidate = currentMapping) =>
      showNotice(
        mappingToValidate.every((item) => item.status === "Mapped")
          ? "Mapping validated successfully"
          : "Validation found fields requiring review",
      );
    return (
      <MappingStudio
        key={integrationId}
        integrationId={integrationId}
        integrations={integrations}
        mapping={mappedRows}
        notice={notice}
        onSelect={(id) => setQuery(`integration:${id}`)}
        onSave={(mapping) => {
          saveMapping(integrationId, mapping);
          showNotice("Mapping saved to workspace");
        }}
        onAutoMap={(mapping) => {
          saveMapping(integrationId, mapping);
          showNotice("Fields auto-mapped and ready for validation");
        }}
        onValidate={validate}
      />
    );
  }

  if (feature === "exceptions") {
    const rows = exceptions.filter(
      (item) =>
        scopedApplicationIds.has(item.applicationId) &&
        `${item.id} ${item.system} ${item.message}`.toLowerCase().includes(lowerQuery),
    );
    return (
      <FeatureFrame meta={meta} query={query} setQuery={setQuery} notice={notice}>
        <div className="space-y-3">
          {rows.map((item) => (
            <Surface key={item.id} className="grid gap-4 lg:grid-cols-[1fr_auto]">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-bold">{item.id}</span>
                  <StatusPill status={item.status} />
                  <span className="text-xs text-muted-foreground">
                    {item.severity} · {item.code}
                  </span>
                </div>
                <p className="mt-2 font-medium">{item.message}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {item.system} · {item.stage} · {item.detectedAt}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">Recovery: {item.recovery}</p>
              </div>
              <div className="flex items-center gap-2 lg:flex-col lg:items-stretch lg:justify-center">
                {item.status === "Open" ? (
                  <Button
                    size="sm"
                    onClick={() => {
                      updateException(item.id, {
                        status: "Recovered",
                        attempts: item.attempts + 1,
                      });
                      showNotice(`${item.id} marked recovered`);
                    }}
                  >
                    <RefreshCw className="mr-2 size-4" /> Retry recovery
                  </Button>
                ) : null}
                {item.status !== "Escalated" ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      updateException(item.id, { status: "Escalated" });
                      showNotice(`${item.id} escalated`);
                    }}
                  >
                    Escalate
                  </Button>
                ) : null}
              </div>
            </Surface>
          ))}
        </div>
      </FeatureFrame>
    );
  }

  if (feature === "consent") {
    const rows = consents.filter(
      (item) =>
        scopedApplicationIds.has(item.applicationId) &&
        `${item.id} ${item.applicationId} ${item.recipient}`.toLowerCase().includes(lowerQuery),
    );
    return (
      <FeatureFrame meta={meta} query={query} setQuery={setQuery} notice={notice}>
        <DataTable
          headers={[
            "Consent",
            "Application",
            "Requested by",
            "Recipient",
            "Status",
            "History",
            "Action",
          ]}
          rows={rows.map((item) => [
            item.id,
            item.applicationId,
            item.requestedBy,
            item.recipient,
            <StatusPill key="status" status={item.status} />,
            <span key="history" className="text-xs text-muted-foreground">
              {(consentHistory[item.id] ?? [])
                .map((entry) => `${entry.status} · ${entry.timestamp}`)
                .join(" → ")}
            </span>,
            item.status === "Pending" ? (
              <Button
                key="action"
                size="sm"
                variant="outline"
                onClick={() => {
                  updateConsent(item.id, "Active");
                  showNotice(`${item.id} approved`);
                }}
              >
                Approve
              </Button>
            ) : item.status === "Active" ? (
              <Button
                key="action"
                size="sm"
                variant="ghost"
                onClick={() => {
                  updateConsent(item.id, "Revoked");
                  showNotice(`${item.id} revoked`);
                }}
              >
                Revoke
              </Button>
            ) : null,
          ])}
        />
      </FeatureFrame>
    );
  }

  if (feature === "monitoring")
    return (
      <MonitoringStudio
        integrations={integrations}
        load={location.load}
        lastUpdated={lastUpdated}
      />
    );

  if (feature === "notifications") {
    const rows = notifications.filter((item) =>
      `${item.title} ${item.body}`.toLowerCase().includes(lowerQuery),
    );
    return (
      <FeatureFrame meta={meta} query={query} setQuery={setQuery} notice={notice}>
        <div className="space-y-2">
          {rows.map((item) => (
            <button
              key={item.id}
              className="surface flex w-full items-start gap-3 p-4 text-left hover:border-primary/40"
              onClick={() => {
                markRead(item.id);
                showNotice("Notification marked as read");
              }}
            >
              <span
                className={`mt-1 size-2 shrink-0 rounded-full ${item.read ? "bg-border" : "bg-primary"}`}
              />
              <span className="min-w-0">
                <span className="block font-semibold">{item.title}</span>
                <span className="mt-1 block text-sm text-muted-foreground">{item.body}</span>
                <span className="mt-1 block text-xs text-muted-foreground">{item.time}</span>
              </span>
            </button>
          ))}
        </div>
      </FeatureFrame>
    );
  }

  if (feature === "profile")
    return (
      <FeatureFrame meta={meta} query={query} setQuery={setQuery} notice={notice}>
        <Surface>
          <div className="flex items-center gap-4">
            <span className="grid size-14 place-items-center rounded-full bg-primary text-xl font-bold text-primary-foreground">
              {user?.avatarInitial}
            </span>
            <div>
              <h2 className="text-lg font-bold">{user?.name}</h2>
              <p className="text-sm text-muted-foreground">{user?.email}</p>
            </div>
          </div>
          <dl className="mt-6 grid gap-4 sm:grid-cols-2">
            <Info label="Role" value={user?.role} />
            <Info label="Department" value={user?.department} />
            <Info label="Mobile" value={user?.mobile} />
            <Info label="Workspace" value={`${location?.city ?? "—"}, ${location?.state ?? "—"}`} />
          </dl>
        </Surface>
      </FeatureFrame>
    );

  if (feature === "reports")
    return (
      <FeatureFrame meta={meta} query={query} setQuery={setQuery} notice={notice}>
        <Surface>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-bold">Service volume report</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                September 2026 · All departments · {scopedApplications.length} applications in scope
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => {
                const csv = [
                  "service,category,department,volume",
                  ...SERVICES.map((service) =>
                    [service.name, service.category, service.department, service.volume]
                      .map((value) => `"${String(value).replaceAll('"', '""')}"`)
                      .join(","),
                  ),
                ].join("\n");
                const url = URL.createObjectURL(
                  new Blob([csv], { type: "text/csv;charset=utf-8" }),
                );
                const link = document.createElement("a");
                link.href = url;
                link.download = "govflow-service-volume-september-2026.csv";
                link.click();
                URL.revokeObjectURL(url);
                showNotice("Report exported as CSV");
              }}
            >
              Export CSV
            </Button>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <Info label="Services" value={String(SERVICES.length)} />
            <Info label="Applications" value={String(scopedApplications.length)} />
            <Info label="Generated" value={new Date().toLocaleDateString("en-IN")} />
          </div>
          <ImpactSimulator />
        </Surface>
      </FeatureFrame>
    );

  if (feature === "settings")
    return (
      <FeatureFrame meta={meta} query={query} setQuery={setQuery} notice={notice}>
        <Surface>
          <div className="grid gap-5 sm:grid-cols-2">
            <label className="grid gap-2 text-sm font-semibold">
              Default location
              <select
                value={locationId}
                onChange={(event) => {
                  setLocationId(event.target.value);
                  showNotice("Default location updated");
                }}
                className="rounded-lg border border-border bg-background px-3 py-2 font-normal"
              >
                {LOCATIONS.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.city}, {item.state}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2 text-sm font-semibold">
              Session timeout
              <select
                value={sessionTimeout}
                onChange={(event) => setSessionTimeout(event.target.value)}
                className="rounded-lg border border-border bg-background px-3 py-2 font-normal"
              >
                {["15", "30", "60", "120"].map((minutes) => (
                  <option key={minutes} value={minutes}>
                    {minutes} minutes
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2 text-sm font-semibold">
              Audit retention
              <select
                value={auditRetention}
                onChange={(event) => setAuditRetention(event.target.value)}
                className="rounded-lg border border-border bg-background px-3 py-2 font-normal"
              >
                {["1", "3", "7", "10"].map((years) => (
                  <option key={years} value={years}>
                    {years} years
                  </option>
                ))}
              </select>
            </label>
          </div>
          <Button
            className="mt-5"
            onClick={() => {
              localStorage.setItem(
                "govflow.preferences.v1",
                JSON.stringify({ locationId, sessionTimeout, auditRetention }),
              );
              showNotice("Workspace preferences saved");
            }}
          >
            Save preferences
          </Button>
        </Surface>
      </FeatureFrame>
    );

  const content = getRows(feature, scopedApplications, workflows, integrations, locationId);
  const filtered = content.rows.filter((row) => row.search.toLowerCase().includes(lowerQuery));
  return (
    <FeatureFrame
      meta={meta}
      query={query}
      setQuery={setQuery}
      notice={notice}
      action={
        feature === "workflows" ? (
          <Button asChild>
            <Link to="/$feature/$id" params={{ feature: "workflows", id: "builder" }}>
              Create workflow <ArrowRight className="ml-2 size-4" />
            </Link>
          </Button>
        ) : undefined
      }
    >
      <div className="flex justify-end text-xs text-muted-foreground">
        Live data updated {lastUpdated.toLocaleTimeString("en-IN")}
      </div>
      <DataTable
        headers={content.headers}
        rows={filtered.map((row) => row.cells)}
        empty="No matching records found."
      />
    </FeatureFrame>
  );
}

function FeatureFrame({
  meta,
  query,
  setQuery,
  notice,
  action,
  children,
}: {
  meta: { title: string; description: string; icon: typeof Activity };
  query: string;
  setQuery: (value: string) => void;
  notice: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  const Icon = meta.icon;
  return (
    <>
      <PageHeader
        eyebrow="GovFlow Workspace"
        title={meta.title}
        subtitle={meta.description}
        actions={action}
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Icon className="size-4 text-primary" /> Live workspace
        </div>
        <div className="relative w-full sm:w-auto">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={`Search ${meta.title.toLowerCase()}...`}
            className="w-full pl-9 sm:w-72"
          />
        </div>
      </div>
      {notice ? (
        <div className="rounded-lg border border-success/25 bg-success/10 px-4 py-3 text-sm font-medium text-success">
          {notice}
        </div>
      ) : null}
      {children}
    </>
  );
}

function MappingStudio({
  integrationId,
  integrations,
  mapping,
  notice,
  onSelect,
  onSave,
  onAutoMap,
  onValidate,
}: {
  integrationId: string;
  integrations: typeof INTEGRATIONS;
  mapping: FieldMap[];
  notice: string;
  onSelect: (id: string) => void;
  onSave: (mapping: FieldMap[]) => void;
  onAutoMap: (mapping: FieldMap[]) => void;
  onValidate: (mapping: FieldMap[]) => void;
}) {
  const [draft, setDraft] = useState(mapping);
  const update = (id: string, patch: Partial<FieldMap>) =>
    setDraft((previous) => previous.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  return (
    <>
      <PageHeader
        eyebrow="Data Mapping Studio"
        title="Universal schema mapper"
        subtitle="Source System → GovFlow Normalization → Validation → Transformation → Target System"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() =>
                (() => {
                  const mapped = draft.map((item) => ({
                    ...item,
                    status: "Mapped" as FieldMap["status"],
                    confidence: Math.max(item.confidence, 94),
                  }));
                  setDraft(mapped);
                  onAutoMap(mapped);
                })()
              }
            >
              Auto Map
            </Button>
            <Button variant="outline" onClick={() => onValidate(draft)}>
              Validate
            </Button>
            <Button onClick={() => onSave(draft)}>Save Mapping</Button>
          </div>
        }
      />
      {notice ? (
        <div className="mb-4 rounded-lg border border-success/25 bg-success/10 px-4 py-3 text-sm font-medium text-success">
          {notice}
        </div>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-5">
        {[
          "Source System",
          "GovFlow Normalization",
          "Validation",
          "Transformation",
          "Target System",
        ].map((label, index) => (
          <div key={label} className="surface flex items-center gap-2 p-4">
            <span className="grid size-7 shrink-0 place-items-center rounded-full bg-accent text-xs font-bold text-accent-foreground">
              {index + 1}
            </span>
            <span className="text-xs font-semibold">{label}</span>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card p-4">
        <label className="text-sm font-semibold" htmlFor="mapping-integration">
          Source system
        </label>
        <select
          id="mapping-integration"
          value={integrationId}
          onChange={(event) => onSelect(event.target.value)}
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
        >
          {integrations.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <span className="text-xs text-muted-foreground">
          Edit fields below, validate the contract, then save it to this workspace.
        </span>
      </div>
      <Surface className="overflow-x-auto p-0">
        <table className="w-full min-w-180 text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted-foreground uppercase">
              <th className="px-5 py-3">Source field</th>
              <th className="px-5 py-3">Target field</th>
              <th className="px-5 py-3">Transform</th>
              <th className="px-5 py-3">Confidence</th>
              <th className="px-5 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {draft.map((item) => (
              <tr key={item.id} className="border-b border-border/60 last:border-0">
                <td className="px-5 py-3">
                  <Input
                    value={item.source}
                    onChange={(event) => update(item.id, { source: event.target.value })}
                  />
                </td>
                <td className="px-5 py-3">
                  <Input
                    value={item.target}
                    onChange={(event) => update(item.id, { target: event.target.value })}
                  />
                </td>
                <td className="px-5 py-3">
                  <Input
                    value={item.transform}
                    onChange={(event) => update(item.id, { transform: event.target.value })}
                  />
                </td>
                <td className="px-5 py-3">{item.confidence}%</td>
                <td className="px-5 py-3">
                  <StatusPill status={item.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Surface>
    </>
  );
}

function MonitoringStudio({
  integrations,
  load,
  lastUpdated,
}: {
  integrations: typeof INTEGRATIONS;
  load: number;
  lastUpdated: Date;
}) {
  const [selected, setSelected] = useState(DEPENDENCY_NODES[0]!.id);
  const nodes = DEPENDENCY_NODES.map((node) => ({
    ...node,
    latencyMs: Math.round(node.latencyMs * load),
    failures24h: Math.round(node.failures24h * load),
    health: load > 2 && node.health === "Healthy" ? ("Degraded" as const) : node.health,
  }));
  const selectedNode = nodes.find((node) => node.id === selected) ?? nodes[0]!;
  const successRate = Math.max(92, Math.min(99.9, 99.1 - (load - 1) * 0.7));
  const failedRequests = Math.round(
    integrations.reduce((total, item) => total + item.failures24h, 0) * load,
  );
  return (
    <>
      <PageHeader
        eyebrow="Interoperability Command Centre"
        title="Monitoring & dependency intelligence"
        subtitle="Live-style health, latency, recovery and bottleneck signals for the selected jurisdiction."
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ["API success rate", `${successRate.toFixed(1)}%`],
          ["Failed requests", String(failedRequests)],
          ["Retries", String(Math.round(failedRequests * 1.7))],
          ["Recovery rate", "96.4%"],
          ["Active workflows", String(Math.round(142 * load))],
        ].map(([label, value]) => (
          <Surface key={label}>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="mt-2 text-2xl font-bold">{value}</p>
          </Surface>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Surface>
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold">System dependency graph</h2>
              <p className="text-xs text-muted-foreground">
                Select a node to inspect health, latency and failures.
              </p>
            </div>
            <span className="text-xs text-muted-foreground">
              Updated {lastUpdated.toLocaleTimeString("en-IN")}
            </span>
          </div>
          <div className="relative mt-5 min-h-107.5 overflow-hidden rounded-xl border border-border bg-muted/20">
            {DEPENDENCY_EDGES.map(([from, to]) => (
              <div
                key={`${from}-${to}`}
                className="absolute left-1/2 top-1/2 hidden h-px w-1/3 origin-left bg-border md:block"
                style={{
                  transform: `rotate(${from === "govflow" ? (to === "aadhaar" ? "-145deg" : to === "revenue" ? "-35deg" : to === "education" ? "145deg" : to === "pfms" ? "35deg" : to === "land" ? "-90deg" : "90deg") : "0deg"})`,
                }}
              />
            ))}
            {nodes.map((node) => (
              <button
                type="button"
                key={node.id}
                onClick={() => setSelected(node.id)}
                className={`absolute w-28 -translate-x-1/2 -translate-y-1/2 rounded-xl border bg-card p-3 text-left shadow-sm transition-all ${selected === node.id ? "border-primary ring-2 ring-primary/20" : "border-border"}`}
                style={{ left: `${node.x}%`, top: `${node.y}%` }}
              >
                <span className="block truncate text-xs font-bold">{node.name}</span>
                <span className="mt-1 block text-[10px] text-muted-foreground">
                  {node.latencyMs} ms
                </span>
                <HealthPill health={node.health} />
              </button>
            ))}
          </div>
        </Surface>
        <Surface>
          <h2 className="text-base font-bold">Selected dependency</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {selectedNode.name} · {selectedNode.kind}
          </p>
          <div className="mt-5 space-y-3">
            <Info label="Health" value={selectedNode.health} />
            <Info label="Latency" value={`${selectedNode.latencyMs} ms`} />
            <Info label="Failures (24h)" value={String(selectedNode.failures24h)} />
          </div>
          <div className="mt-6 border-t border-border pt-4">
            <p className="text-xs font-semibold uppercase text-muted-foreground">
              Connected through GovFlow
            </p>
            <p className="mt-2 text-sm">
              {
                DEPENDENCY_EDGES.filter(
                  ([from, to]) => from === selectedNode.id || to === selectedNode.id,
                ).length
              }{" "}
              dependency paths in scope
            </p>
          </div>
        </Surface>
      </div>
      <Surface>
        <h2 className="text-base font-bold">Workflow bottleneck intelligence</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Prioritized recommendations from current latency and failure signals.
        </p>
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {BOTTLENECKS.map((item) => (
            <div key={item.stage} className="rounded-xl border border-border p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="font-semibold">{item.stage}</span>
                <StatusPill status={item.impact} />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {item.workflow} · {item.latency} · {item.failureRate} failure rate
              </p>
              <p className="mt-3 text-sm">{item.recommendation}</p>
            </div>
          ))}
        </div>
      </Surface>
    </>
  );
}

function ImpactSimulator() {
  const [automated, setAutomated] = useState(true);
  return (
    <div className="mt-6 border-t border-border pt-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold">Impact simulator</h2>
          <p className="text-sm text-muted-foreground">
            Compare the citizen journey before and after GovFlow orchestration.
          </p>
        </div>
        <Button variant="outline" onClick={() => setAutomated((value) => !value)}>
          {automated ? "View before GovFlow" : "View after GovFlow"}
        </Button>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {IMPACT_METRICS.map((metric) => (
          <div key={metric.label} className="rounded-xl border border-border p-4">
            <p className="text-xs font-semibold uppercase text-muted-foreground">{metric.label}</p>
            <p className="mt-2 text-sm font-medium">{automated ? metric.after : metric.before}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function DataTable({
  headers,
  rows,
  empty = "No records found.",
}: {
  headers: string[];
  rows: ReactNode[][];
  empty?: string;
}) {
  return (
    <Surface className="overflow-x-auto p-0">
      <table className="w-full min-w-180 text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted-foreground uppercase">
            {headers.map((header) => (
              <th key={header} className="px-5 py-3 font-semibold">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row, index) => (
              <tr key={index} className="border-b border-border/60 last:border-0">
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className="px-5 py-3 align-middle">
                    {cell}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={headers.length} className="px-5 py-12 text-center text-muted-foreground">
                {empty}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </Surface>
  );
}

function Info({ label, value }: { label: string; value: string | undefined }) {
  return (
    <div>
      <dt className="text-xs font-semibold text-muted-foreground uppercase">{label}</dt>
      <dd className="mt-1 text-sm font-medium">{value ?? "—"}</dd>
    </div>
  );
}

function getRows(
  feature: string,
  applications: typeof APPLICATIONS,
  workflows: typeof WORKFLOWS,
  integrations: typeof INTEGRATIONS,
  locationId: string,
) {
  const locationIndex = Math.max(
    0,
    LOCATIONS.findIndex((location) => location.id === locationId),
  );
  const scopeCount = Math.min(LOCATIONS.length, 3 + (locationIndex % 4));
  if (feature === "services")
    return {
      headers: ["Service", "Category", "Department", "SLA", "Volume"],
      rows: SERVICES.slice(0, scopeCount + 2).map((item) => ({
        search: `${item.name} ${item.category} ${item.department}`,
        cells: [
          <Link
            key="name"
            className="font-semibold text-primary"
            to="/$feature/$id"
            params={{ feature: "services", id: item.id }}
          >
            {item.name}
          </Link>,
          item.category,
          item.department,
          item.sla,
          item.volume.toLocaleString(),
        ],
      })),
    };
  if (feature === "workflows")
    return {
      headers: ["Workflow", "Version", "Status", "Runs", "Success rate"],
      rows: workflows.slice(0, scopeCount).map((item) => ({
        search: `${item.name} ${item.status}`,
        cells: [
          item.name,
          item.version,
          <StatusPill key="status" status={item.status} />,
          item.runs.toLocaleString(),
          `${item.successRate}%`,
        ],
      })),
    };
  if (feature === "applications")
    return {
      headers: ["Application", "Citizen", "Service", "Stage", "Status"],
      rows: applications.map((item) => {
        const service = getService(item.serviceId);
        const workflow = getWorkflow(service?.workflowId ?? "");
        return {
          search: `${item.id} ${item.citizen} ${item.status}`,
          cells: [
            <Link
              key="id"
              className="font-semibold text-primary"
              to="/$feature/$id"
              params={{ feature: "applications", id: item.id }}
            >
              {item.id}
            </Link>,
            item.citizen,
            service?.name ?? "—",
            workflow.stages.find((stage) => stage.id === item.stageId)?.name ?? "—",
            <StatusPill key="status" status={item.status} />,
          ] as ReactNode[],
        };
      }),
    };
  if (feature === "departments")
    return {
      headers: ["Department", "Head", "Services", "Response", "Uptime"],
      rows: DEPARTMENTS.slice(0, scopeCount).map((item) => ({
        search: `${item.name} ${item.head}`,
        cells: [
          item.name,
          item.head,
          item.services.length,
          `${item.responseMs} ms`,
          `${item.uptime}%`,
        ],
      })),
    };
  if (feature === "integrations")
    return {
      headers: ["Integration", "Protocol", "Health", "Success", "Latency"],
      rows: integrations.slice(0, scopeCount + 1).map((item) => ({
        search: `${item.name} ${item.protocol} ${item.owner}`,
        cells: [
          <Link
            key="name"
            className="font-semibold text-primary"
            to="/$feature/$id"
            params={{ feature: "integrations", id: item.id }}
          >
            {item.name}
          </Link>,
          item.protocol,
          <HealthPill key="health" health={item.health} />,
          `${item.successRate}%`,
          `${item.latencyMs} ms`,
        ],
      })),
    };
  if (feature === "monitoring")
    return {
      headers: ["System", "Health", "Success rate", "Latency", "Failures (24h)"],
      rows: integrations.slice(0, scopeCount + 1).map((item) => ({
        search: `${item.name} ${item.health}`,
        cells: [
          item.name,
          <HealthPill key="health" health={item.health} />,
          `${item.successRate}%`,
          `${item.latencyMs} ms`,
          item.failures24h,
        ],
      })),
    };
  if (feature === "audit-logs")
    return {
      headers: ["Time", "Actor", "Action", "Entity", "Result"],
      rows: AUDIT_LOGS.map((item) => ({
        search: `${item.actor} ${item.action} ${item.entity}`,
        cells: [
          item.time,
          item.actor,
          item.action,
          item.entity,
          <StatusPill key="result" status={item.result} />,
        ],
      })),
    };
  if (feature === "users")
    return {
      headers: ["User", "Role", "Department", "Status", "Last active"],
      rows: USERS.map((item) => ({
        search: `${item.name} ${item.email} ${item.role}`,
        cells: [
          item.name,
          item.role,
          item.department,
          <StatusPill key="status" status={item.status} />,
          item.lastActive,
        ],
      })),
    };
  return { headers: ["Name", "Details", "Status"], rows: [] };
}
