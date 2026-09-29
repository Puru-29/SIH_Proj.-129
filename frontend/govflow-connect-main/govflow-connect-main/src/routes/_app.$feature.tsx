import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useCallback, useEffect, useState, type ReactNode } from "react";
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
import { AIDocumentVerifier } from "@/components/govflow/ai-document-verifier";
import { InteroperabilityHub } from "@/components/govflow/interoperability-hub";
import {
  type Application,
  type Department,
  type FieldMap,
  type Integration,
  type PlatformUser,
  type Service,
  type Workflow,
} from "@/lib/govflow/data";
import { useGovFlow, useScopedApplications } from "@/lib/govflow/store";
import {
  api,
  type AuditLogFilters,
  type MeshApplication,
  type MeshAuditLog,
  type MeshException,
} from "@/lib/api";
import { auditService } from "@/services/auditService";

export const Route = createFileRoute("/_app/$feature")({
  validateSearch: (search: Record<string, unknown>): { transaction?: string } =>
    typeof search["transaction"] === "string" ? { transaction: search["transaction"] } : {},
  component: FeatureRoute,
});

function FeatureRoute() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const { feature } = Route.useParams();
  const { transaction } = Route.useSearch();
  return pathname.split("/").filter(Boolean).length > 1 ? (
    <Outlet />
  ) : (
    <FeaturePage
      key={feature ?? "workspace"}
      {...(transaction ? { transactionId: transaction } : {})}
    />
  );
}

const META: Record<
  string,
  { title: string; description: string; icon: typeof Activity; eyebrow?: string }
> = {
  services: {
    title: "Services",
    description: "Manage citizen services and their connected workflows.",
    icon: Landmark,
    eyebrow: "Service Registry",
  },
  workflows: {
    title: "Workflows",
    description: "Monitor and operate cross-department service orchestration.",
    icon: GitBranch,
    eyebrow: "Workflow Orchestration",
  },
  applications: {
    title: "Applications",
    description: "Track citizen applications across every processing stage.",
    icon: FileStack,
    eyebrow: "Application Track",
  },
  departments: {
    title: "Departments",
    description: "View department ownership, service coverage and system health.",
    icon: Building2,
    eyebrow: "Department View",
  },
  integrations: {
    title: "Integrations",
    description: "Operate the systems connected to the GovFlow network.",
    icon: Boxes,
    eyebrow: "Connected Systems",
  },
  "data-mapping": {
    title: "Data Mapping",
    description: "Review how fields move between connected government systems.",
    icon: Shuffle,
    eyebrow: "Schema Mapping",
  },
  consent: {
    title: "Consent Management",
    description: "Review and manage citizen data-sharing permissions.",
    icon: ShieldCheck,
    eyebrow: "Consent Controls",
  },
  monitoring: {
    title: "Monitoring",
    description: "Observe API health, response time and platform reliability.",
    icon: Activity,
    eyebrow: "Operations Monitor",
  },
  exceptions: {
    title: "Exceptions",
    description: "Recover failed workflow stages and escalate operational issues.",
    icon: TriangleAlert,
    eyebrow: "Operations Console",
  },
  "audit-logs": {
    title: "Audit Logs",
    description: "Trace every access, workflow change and system event.",
    icon: FileText,
    eyebrow: "Compliance Trail",
  },
  reports: {
    title: "Reports",
    description: "Review operational performance across services and departments.",
    icon: Gauge,
    eyebrow: "Performance Reports",
  },
  users: {
    title: "Users",
    description: "Manage platform access for officers and operators.",
    icon: Users,
    eyebrow: "Access Control",
  },
  settings: {
    title: "Profile / Settings",
    description: "Review account details and adjust workspace preferences.",
    icon: Settings,
    eyebrow: "Account Controls",
  },
  "ai-document-verification": {
    title: "AI Document Verification",
    description:
      "Verify identity, document, and fraud signals across connected government systems.",
    icon: ShieldCheck,
    eyebrow: "Trust Verification",
  },
  notifications: {
    title: "Notifications",
    description: "Review platform alerts and workflow updates.",
    icon: TriangleAlert,
    eyebrow: "Alert Center",
  },
  profile: {
    title: "Profile",
    description: "Review your GovFlow account and access details.",
    icon: Users,
    eyebrow: "Identity & Access",
  },
};

function FeaturePage({ transactionId }: { transactionId?: string }) {
  const { feature } = Route.useParams();
  const meta: { title: string; description: string; icon: typeof Activity; eyebrow?: string } =
    META[feature] ?? {
      title: "Workspace",
      description: "GovFlow workspace",
      icon: Activity,
      eyebrow: "GovFlow Workspace",
    };
  const Icon = meta.icon;
  const [query, setQuery] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    setQuery("");
    setNotice("");
  }, [feature]);
  const {
    consents,
    notifications,
    markRead,
    user,
    workflows,
    integrations,
    mappings,
    services,
    departments,
    users,
    lastUpdated,
    ready,
    loadError,
    liveStats,
  } = useGovFlow();
  const scopedApplications = useScopedApplications();
  const scopedApplicationIds = new Set(scopedApplications.map((application) => application.id));
  const lowerQuery = query.toLowerCase();

  const showNotice = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 2400);
  };

  if (feature === "applications") {
    return <ApplicationsPage user={user} query={query} setQuery={setQuery} notice={notice} />;
  }
  if (feature === "audit-logs") {
    return <AuditLogsPage query={query} setQuery={setQuery} notice={notice} />;
  }
  if (feature === "exceptions") {
    return <ExceptionsPage user={user} query={query} setQuery={setQuery} notice={notice} />;
  }
  if (feature === "monitoring" || feature === "integrations") {
    return (
      <InteroperabilityHub
        query={query}
        setQuery={setQuery}
        systemsOnly={feature === "integrations"}
        {...(transactionId ? { initialTransactionId: transactionId } : {})}
      />
    );
  }

  if (feature === "data-mapping") {
    const integrationId = query.startsWith("integration:")
      ? query.slice("integration:".length)
      : (integrations[0]?.id ?? "");
    const currentMapping = mappings[integrationId] ?? [];
    const mappedRows = currentMapping.filter((item) =>
      `${item.source} ${item.target} ${item.status}`
        .toLowerCase()
        .includes(lowerQuery.replace(`integration:${integrationId}`, "")),
    );
    return (
      <MappingStudio
        key={integrationId}
        integrationId={integrationId}
        integrations={integrations}
        mapping={mappedRows}
        onSelect={(id) => setQuery(`integration:${id}`)}
      />
    );
  }

  function AuditLogsPage({
    query,
    setQuery,
    notice,
  }: {
    query: string;
    setQuery: (value: string) => void;
    notice: string;
  }) {
    const [logs, setLogs] = useState<MeshAuditLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [appliedFilters, setAppliedFilters] = useState<AuditLogFilters>({
      limit: 200,
    });
    const [draft, setDraft] = useState({
      date: "",
      actor: "",
      department: "",
      action: "",
      transaction: "",
      resource: "",
      result: "",
    });

    const loadAuditLogs = useCallback(async () => {
      setLoading(true);
      setError("");
      try {
        setLogs(await auditService.getLogs(appliedFilters));
      } catch (loadError) {
        setError(
          loadError instanceof Error ? loadError.message : "Audit logs could not be loaded.",
        );
      } finally {
        setLoading(false);
      }
    }, [appliedFilters]);

    useEffect(() => {
      void loadAuditLogs();
    }, [loadAuditLogs]);

    const visibleLogs = logs.filter((log) =>
      [
        log.action,
        log.actor_name,
        log.actor_role,
        log.resource_type,
        log.resource_id,
        log.transaction_id,
        log.result,
        JSON.stringify(log.metadata),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
    );

    const input = (key: keyof typeof draft, label: string, type = "text", placeholder = "") => (
      <label className="grid gap-1.5 text-xs font-semibold text-muted-foreground" key={key}>
        <span>{label}</span>
        <Input
          type={type}
          value={draft[key]}
          placeholder={placeholder}
          onChange={(event) => setDraft((current) => ({ ...current, [key]: event.target.value }))}
        />
      </label>
    );

    return (
      <FeatureFrame
        meta={META["audit-logs"]!}
        query={query}
        setQuery={setQuery}
        notice={notice}
        action={
          <Button variant="outline" onClick={() => void loadAuditLogs()} disabled={loading}>
            <RefreshCw className={`mr-2 size-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <Surface>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {input("date", "Date", "date")}
            {input("actor", "Actor ID", "number", "User ID")}
            {input("department", "Department ID", "number", "Department ID")}
            {input("action", "Action", "text", "e.g. APPLICATION_CREATED")}
            {input("transaction", "Transaction", "text", "Transaction ID")}
            {input("resource", "Resource", "text", "Type or resource ID")}
            {input("result", "Result", "text", "success / failure / conflict")}
            <div className="flex items-end gap-2">
              <Button
                onClick={() =>
                  setAppliedFilters({
                    ...draft,
                    limit: 200,
                  })
                }
              >
                Apply filters
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setDraft({
                    date: "",
                    actor: "",
                    department: "",
                    action: "",
                    transaction: "",
                    resource: "",
                    result: "",
                  });
                  setAppliedFilters({ limit: 200 });
                }}
              >
                Clear
              </Button>
            </div>
          </div>
        </Surface>
        {error ? (
          <Surface>
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
            <Button className="mt-3" variant="outline" onClick={() => void loadAuditLogs()}>
              Retry
            </Button>
          </Surface>
        ) : loading ? (
          <Surface>
            <p className="text-sm text-muted-foreground">Loading audit events…</p>
          </Surface>
        ) : (
          <Surface className="overflow-x-auto p-0">
            <table className="w-full min-w-[1200px] text-left text-sm">
              <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                <tr>
                  {[
                    "Timestamp",
                    "Actor",
                    "Department",
                    "Action",
                    "Resource",
                    "Transaction",
                    "Result",
                    "Metadata",
                  ].map((heading) => (
                    <th key={heading} className="px-4 py-3 font-semibold">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleLogs.map((log) => (
                  <tr key={log.id} className="border-b border-border/60 last:border-0">
                    <td className="px-4 py-3 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        {log.actor_name ?? (log.actor_id ? `User #${log.actor_id}` : "System")}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {log.actor_role ?? "system"}
                      </div>
                    </td>
                    <td className="px-4 py-3">{log.department_id ?? "—"}</td>
                    <td className="px-4 py-3 font-semibold">{log.action}</td>
                    <td className="px-4 py-3">
                      {log.resource_type} · {log.resource_id}
                    </td>
                    <td className="px-4 py-3">{log.transaction_id ?? "—"}</td>
                    <td className="px-4 py-3">
                      <StatusPill status={log.result} />
                    </td>
                    <td className="max-w-64 truncate px-4 py-3 font-mono text-xs">
                      <span title={JSON.stringify(log.metadata)}>
                        {JSON.stringify(log.metadata)}
                      </span>
                    </td>
                  </tr>
                ))}
                {visibleLogs.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                      No audit events match these filters.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </Surface>
        )}
      </FeatureFrame>
    );
  }

  function ApplicationsPage({
    user,
    query,
    setQuery,
    notice,
  }: {
    user: ReturnType<typeof useGovFlow>["user"];
    query: string;
    setQuery: (value: string) => void;
    notice: string;
  }) {
    const role = user?.backendRole;
    const isOfficer = role === "officer" || role === "department_officer";
    const [applications, setApplications] = useState<MeshApplication[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [assignedOnly, setAssignedOnly] = useState(false);
    const [actionError, setActionError] = useState("");
    const [assigningId, setAssigningId] = useState<number | null>(null);

    const loadApplications = useCallback(async () => {
      setLoading(true);
      setError("");
      try {
        const results = await api.getApplications({
          limit: 200,
          search: query.trim(),
          assigned_to_me: isOfficer && assignedOnly,
        });
        setApplications(results);
      } catch (loadError) {
        setError(
          loadError instanceof Error ? loadError.message : "Applications could not be loaded.",
        );
      } finally {
        setLoading(false);
      }
    }, [query, isOfficer, assignedOnly]);

    useEffect(() => {
      const timer = window.setTimeout(() => void loadApplications(), query ? 250 : 0);
      return () => window.clearTimeout(timer);
    }, [loadApplications, query]);

    const assignToMe = async (id: number) => {
      setAssigningId(id);
      setActionError("");
      try {
        await api.assignApplicationToMe(id);
        await loadApplications();
      } catch (actionFailure) {
        setActionError(
          actionFailure instanceof Error ? actionFailure.message : "Application assignment failed.",
        );
      } finally {
        setAssigningId(null);
      }
    };

    return (
      <FeatureFrame
        meta={META["applications"]!}
        query={query}
        setQuery={setQuery}
        notice={notice}
        action={
          isOfficer ? (
            <Button
              variant={assignedOnly ? "default" : "outline"}
              onClick={() => setAssignedOnly((value) => !value)}
            >
              {assignedOnly ? "Showing assigned to me" : "Assigned to me"}
            </Button>
          ) : undefined
        }
      >
        {error ? (
          <Surface>
            <p className="text-sm text-danger">{error}</p>
            <Button className="mt-3" variant="outline" onClick={() => void loadApplications()}>
              <RefreshCw className="mr-2 size-4" /> Retry
            </Button>
          </Surface>
        ) : null}
        {actionError ? (
          <p role="alert" className="text-sm text-danger">
            {actionError}
          </p>
        ) : null}
        {loading ? (
          <Surface>
            <p className="text-sm text-muted-foreground">Loading applications…</p>
          </Surface>
        ) : error ? null : applications.length === 0 ? (
          <Surface>
            <p className="text-sm text-muted-foreground">No applications found.</p>
          </Surface>
        ) : (
          <div className="surface overflow-x-auto">
            <table className="w-full min-w-[1050px] text-left text-sm">
              <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                <tr>
                  {[
                    "Application ID",
                    "Citizen",
                    "Service",
                    "Department",
                    "Status",
                    "Current workflow step",
                    "SLA",
                    "Assigned officer",
                    "Action",
                  ].map((heading) => (
                    <th key={heading} className="px-3 py-3 font-semibold">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {applications.map((application) => (
                  <tr key={application.id} className="align-top">
                    <td className="px-3 py-3 font-semibold">
                      <Link
                        className="text-primary hover:underline"
                        to="/applications/$id"
                        params={{ id: String(application.id) }}
                      >
                        {application.reference_id}
                      </Link>
                    </td>
                    <td className="px-3 py-3">
                      {application.citizen_name || `Citizen #${application.citizen_id}`}
                    </td>
                    <td className="px-3 py-3">{application.service_name || "—"}</td>
                    <td className="px-3 py-3">{application.department_name || "—"}</td>
                    <td className="px-3 py-3">
                      <StatusPill status={formatBackendStatus(application.status)} />
                    </td>
                    <td className="px-3 py-3">
                      {application.current_workflow_step?.name || "—"}
                      {application.current_workflow_step?.department ? (
                        <span className="block text-xs text-muted-foreground">
                          {application.current_workflow_step.department}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-3 py-3">{formatSla(application.sla_due_at)}</td>
                    <td className="px-3 py-3">
                      {application.assigned_officer_name || "Unassigned"}
                    </td>
                    <td className="px-3 py-3">
                      {isOfficer && !application.assigned_officer_id ? (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={assigningId === application.id}
                          onClick={() => void assignToMe(application.id)}
                        >
                          {assigningId === application.id ? "Assigning…" : "Assign to me"}
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </FeatureFrame>
    );
  }

  function ExceptionsPage({
    user,
    query,
    setQuery,
    notice,
  }: {
    user: ReturnType<typeof useGovFlow>["user"];
    query: string;
    setQuery: (value: string) => void;
    notice: string;
  }) {
    const [rows, setRows] = useState<MeshException[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [pendingId, setPendingId] = useState<number | null>(null);
    const role = user?.backendRole;
    const canManage = [
      "officer",
      "department_officer",
      "developer",
      "operator",
      "interoperability_admin",
      "admin",
      "system_admin",
    ].includes(role || "");

    const loadExceptions = useCallback(async () => {
      setError("");
      try {
        setRows(await api.getExceptions());
      } catch (loadError) {
        setError(
          loadError instanceof Error ? loadError.message : "Exceptions could not be loaded.",
        );
      } finally {
        setLoading(false);
      }
    }, []);

    useEffect(() => {
      void loadExceptions();
    }, [loadExceptions]);

    const updateStatus = async (id: number, status: MeshException["status"]) => {
      setPendingId(id);
      setError("");
      try {
        await api.updateException(id, { status });
        await loadExceptions();
      } catch (actionError) {
        setError(
          actionError instanceof Error ? actionError.message : "Exception could not be updated.",
        );
      } finally {
        setPendingId(null);
      }
    };

    const filtered = rows.filter((item) =>
      `${item.id} ${item.applicationId || ""} ${item.transactionId || ""} ${item.system} ${item.type || item.category} ${item.message} ${item.status}`
        .toLowerCase()
        .includes(query.toLowerCase()),
    );

    return (
      <FeatureFrame meta={META["exceptions"]!} query={query} setQuery={setQuery} notice={notice}>
        {error ? (
          <Surface>
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
            <Button className="mt-3" variant="outline" onClick={() => void loadExceptions()}>
              <RefreshCw className="mr-2 size-4" /> Retry
            </Button>
          </Surface>
        ) : null}
        {loading ? (
          <Surface>
            <p className="text-sm text-muted-foreground">Loading backend exceptions…</p>
          </Surface>
        ) : filtered.length ? (
          <div className="space-y-3">
            {filtered.map((item) => (
              <Surface key={item.id} className="grid gap-4 lg:grid-cols-[1fr_auto]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold">Exception #{item.id}</span>
                    <StatusPill status={formatBackendStatus(item.status)} />
                    <span className="text-xs text-muted-foreground">
                      {item.severity} · {item.category}
                      {` · ${item.retryCount} retries`}
                    </span>
                  </div>
                  <p className="mt-2 font-medium">{item.message}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {item.system} · {formatBackendDate(item.createdAt)}
                    {item.applicationId ? ` · Application ${item.applicationId}` : ""}
                  </p>
                  {item.details ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      {JSON.stringify(item.details)}
                    </p>
                  ) : null}
                  {item.applicationId && /^\d+$/.test(item.applicationId) ? (
                    <Link
                      className="mt-2 inline-block text-xs font-semibold text-primary hover:underline"
                      to="/applications/$id"
                      params={{ id: item.applicationId }}
                    >
                      Open application
                    </Link>
                  ) : null}
                </div>
                {canManage ? (
                  <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                    {item.status === "OPEN" ? (
                      <Button
                        size="sm"
                        disabled={pendingId === item.id}
                        onClick={() => void updateStatus(item.id, "ESCALATED")}
                      >
                        Escalate
                      </Button>
                    ) : null}
                    {item.status === "ESCALATED" || item.status === "IGNORED" ? (
                      <Button
                        size="sm"
                        disabled={pendingId === item.id}
                        onClick={() => void updateStatus(item.id, "OPEN")}
                      >
                        Reopen
                      </Button>
                    ) : null}
                    {item.status === "OPEN" || item.status === "ESCALATED" ? (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={pendingId === item.id}
                        onClick={() => void updateStatus(item.id, "IGNORED")}
                      >
                        Ignore
                      </Button>
                    ) : null}
                  </div>
                ) : null}
              </Surface>
            ))}
          </div>
        ) : !error ? (
          <Surface>
            <p className="text-sm text-muted-foreground">No matching backend exceptions.</p>
          </Surface>
        ) : null}
        {!canManage ? (
          <p className="text-xs text-muted-foreground">
            Your role has read-only access to exceptions.
          </p>
        ) : null}
      </FeatureFrame>
    );
  }

  function formatBackendStatus(status: string) {
    return status.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function formatBackendDate(value?: string | null) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime())
      ? "—"
      : date.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
  }

  function formatSla(value?: string | null) {
    if (!value) return "Not set";
    const dueAt = new Date(value);
    if (Number.isNaN(dueAt.getTime())) return "Invalid SLA";
    return `${dueAt.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}${dueAt.getTime() < Date.now() ? " · Overdue" : ""}`;
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
          headers={["Consent", "Application", "Source system", "Recipient", "Status"]}
          rows={rows.map((item) => [
            item.id,
            item.applicationId,
            item.requestedBy,
            item.recipient,
            <StatusPill key="status" status={item.status} />,
          ])}
        />
        <p className="mt-3 text-xs text-muted-foreground">
          Consent decisions are made by the citizen through their portal. Government staff can
          review status but cannot approve or revoke consent.
        </p>
      </FeatureFrame>
    );
  }

  if (feature === "ai-document-verification") {
    return <AIDocumentVerifier />;
  }

  if (feature === "notifications") {
    const rows = notifications.filter((item) =>
      `${item.title} ${item.body}`.toLowerCase().includes(lowerQuery),
    );
    return (
      <FeatureFrame meta={meta} query={query} setQuery={setQuery} notice={notice}>
        <div className="space-y-2">
          {rows.map((item) => (
            <div key={item.id} className="surface flex w-full items-start gap-3 p-4 text-left">
              <span
                className={`mt-1 size-2 shrink-0 rounded-full ${item.read ? "bg-border" : "bg-primary"}`}
              />
              <span className="min-w-0">
                <span className="block font-semibold">{item.title}</span>
                <span className="mt-1 block text-sm text-muted-foreground">{item.body}</span>
                <span className="mt-1 block text-xs text-muted-foreground">{item.time}</span>
                {item.applicationId ? (
                  <Link
                    to="/applications/$id"
                    params={{ id: String(item.applicationId) }}
                    className="mt-2 inline-block text-xs font-semibold text-primary hover:underline"
                  >
                    Open application {item.applicationReference ?? ""}
                  </Link>
                ) : null}
                {item.transactionId ? (
                  <Link
                    to="/$feature"
                    params={{ feature: "monitoring" }}
                    search={{ transaction: item.transactionId }}
                    className="mt-2 inline-block text-xs font-semibold text-primary hover:underline"
                  >
                    Open transaction {item.transactionId}
                  </Link>
                ) : null}
                {!item.read ? (
                  <button
                    type="button"
                    className="mt-2 block text-xs font-semibold text-primary hover:underline"
                    onClick={() => void markRead(item.id)}
                  >
                    Mark as read
                  </button>
                ) : null}
              </span>
            </div>
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
                Application and service totals from the connected records
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => {
                const csv = [
                  "service,category,department,sla",
                  ...services.map((service) =>
                    [service.name, service.category ?? "", service.department, service.sla ?? ""]
                      .map((value) => `"${String(value).replaceAll('"', '""')}"`)
                      .join(","),
                  ),
                ].join("\n");
                const url = URL.createObjectURL(
                  new Blob([csv], { type: "text/csv;charset=utf-8" }),
                );
                const link = document.createElement("a");
                link.href = url;
                link.download = "service-catalog.csv";
                link.click();
                URL.revokeObjectURL(url);
                showNotice("Report exported as CSV");
              }}
            >
              Export CSV
            </Button>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <Info label="Services" value={String(liveStats?.total_services ?? services.length)} />
            <Info
              label="Applications"
              value={String(liveStats?.total_applications ?? scopedApplications.length)}
            />
            <Info label="Audit events" value={String(liveStats?.total_audit_events ?? "—")} />
          </div>
        </Surface>
      </FeatureFrame>
    );

  if (feature === "settings")
    return (
      <FeatureFrame meta={meta} query={query} setQuery={setQuery} notice={notice}>
        <Surface>
          <h2 className="text-base font-bold">Account settings</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Account scope and access settings are managed by your administrator.
          </p>
        </Surface>
      </FeatureFrame>
    );

  const content = getRows(
    feature,
    scopedApplications,
    workflows,
    integrations,
    services,
    departments,
    users,
  );
  const filtered = content.rows.filter((row) => row.search.toLowerCase().includes(lowerQuery));
  return (
    <FeatureFrame meta={meta} query={query} setQuery={setQuery} notice={notice}>
      {loadError ? (
        <p role="alert" className="text-sm text-danger">
          {loadError}
        </p>
      ) : null}
      {!ready && !loadError ? (
        <p className="text-sm text-muted-foreground">Loading records…</p>
      ) : null}
      {lastUpdated ? (
        <div className="flex justify-end text-xs text-muted-foreground">
          Data refreshed {lastUpdated.toLocaleTimeString("en-IN")}
        </div>
      ) : null}
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
  meta: { title: string; description: string; icon: typeof Activity; eyebrow?: string };
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
        eyebrow={meta.eyebrow ?? "GovFlow Workspace"}
        title={meta.title}
        subtitle={meta.description}
        actions={action}
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Icon className="size-4 text-primary" />
          <span>{meta.eyebrow ? `${meta.eyebrow} workspace` : "Live workspace"}</span>
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
  onSelect,
}: {
  integrationId: string;
  integrations: Integration[];
  mapping: FieldMap[];
  onSelect: (id: string) => void;
}) {
  return (
    <>
      <PageHeader
        eyebrow="Data Mapping Studio"
        title="Universal schema mapper"
        subtitle="Backend-configured field mappings."
      />
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
          Mapping definitions are read from the backend.
        </span>
      </div>
      <Surface className="overflow-x-auto p-0">
        <table className="w-full min-w-180 text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted-foreground uppercase">
              <th className="px-5 py-3">Source field</th>
              <th className="px-5 py-3">Target field</th>
              <th className="px-5 py-3">Transform</th>
              <th className="px-5 py-3">Required</th>
              <th className="px-5 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {mapping.map((item) => (
              <tr key={item.id} className="border-b border-border/60 last:border-0">
                <td className="px-5 py-3">{item.source}</td>
                <td className="px-5 py-3">{item.target}</td>
                <td className="px-5 py-3">{item.transform}</td>
                <td className="px-5 py-3">{item.required ? "Yes" : "No"}</td>
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
  applications: Application[],
  workflows: Workflow[],
  integrations: Integration[],
  services: Service[],
  departments: Department[],
  users: PlatformUser[],
) {
  if (feature === "services")
    return {
      headers: ["Service", "Code", "Department", "Description", "Status"],
      rows: services.map((item) => ({
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
          item.code,
          item.department,
          item.summary || "—",
          <StatusPill key="status" status={item.active ? "Active" : "Inactive"} />,
        ],
      })),
    };
  if (feature === "workflows")
    return {
      headers: ["Workflow", "Version", "Status", "Runs", "Success rate"],
      rows: workflows.map((item) => ({
        search: `${item.name} ${item.status}`,
        cells: [
          item.name,
          item.version,
          <StatusPill key="status" status={item.status} />,
          item.runs !== undefined ? item.runs.toLocaleString() : "—",
          item.successRate !== undefined ? `${item.successRate}%` : "—",
        ],
      })),
    };
  if (feature === "applications")
    return {
      headers: ["Application", "Citizen", "Service", "Stage", "Status"],
      rows: applications.map((item) => {
        const service = services.find((entry) => entry.id === item.serviceId);
        const workflow = workflows.find((entry) => entry.id === service?.workflowId);
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
            workflow?.stages.find((stage) => stage.id === item.stageId)?.name ?? "—",
            <StatusPill key="status" status={item.status} />,
          ] as ReactNode[],
        };
      }),
    };
  if (feature === "departments")
    return {
      headers: ["Department", "Head", "Services", "Response", "Uptime"],
      rows: departments.map((item) => ({
        search: `${item.name} ${item.head}`,
        cells: [
          item.name,
          item.head ?? "—",
          item.services.length,
          item.responseMs !== undefined ? `${item.responseMs} ms` : "—",
          item.uptime !== undefined ? `${item.uptime}%` : "—",
        ],
      })),
    };
  if (feature === "integrations")
    return {
      headers: ["Integration", "Protocol", "Health", "Success", "Latency"],
      rows: integrations.map((item) => ({
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
          item.successRate !== undefined ? `${item.successRate}%` : "—",
          item.latencyMs !== undefined ? `${item.latencyMs} ms` : "—",
        ],
      })),
    };
  if (feature === "monitoring")
    return {
      headers: ["System", "Health", "Success rate", "Latency", "Failures (24h)"],
      rows: integrations.map((item) => ({
        search: `${item.name} ${item.health}`,
        cells: [
          item.name,
          <HealthPill key="health" health={item.health} />,
          item.successRate !== undefined ? `${item.successRate}%` : "—",
          item.latencyMs !== undefined ? `${item.latencyMs} ms` : "—",
          item.failures24h ?? "—",
        ],
      })),
    };
  if (feature === "users")
    return {
      headers: ["User", "Role", "Department", "Status", "Last active"],
      rows: users.map((item) => ({
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
