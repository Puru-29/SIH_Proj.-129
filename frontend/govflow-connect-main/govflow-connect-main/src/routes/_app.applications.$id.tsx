import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  FileText,
  RefreshCw,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader, StatusPill, Surface } from "@/components/govflow/bits";
import { api, type ApplicationWorkspace } from "@/lib/api";
import { useGovFlow } from "@/lib/govflow/store";

export const Route = createFileRoute("/_app/applications/$id")({
  component: ApplicationDetailsPage,
});

function ApplicationDetailsPage() {
  const { id } = Route.useParams();
  const { user } = useGovFlow();
  const [workspace, setWorkspace] = useState<ApplicationWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [pendingAction, setPendingAction] = useState(false);

  const loadWorkspace = useCallback(async () => {
    setError("");
    try {
      setWorkspace(await api.getApplicationWorkspace(id));
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Application workspace could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadWorkspace();
  }, [loadWorkspace]);

  const application = workspace?.application;
  const role = user?.backendRole;
  const isOfficer = role === "officer" || role === "department_officer";
  const isPrivileged = [
    "admin",
    "system_admin",
    "developer",
    "operator",
    "interoperability_admin",
  ].includes(role || "");
  const activeStep =
    workspace?.workflow.find((step) => step.status === "in_progress") ??
    workspace?.workflow.find((step) => step.status === "pending");
  const officerCanAct = Boolean(
    isOfficer &&
    application?.assigned_officer_id === user?.id &&
    activeStep?.department &&
    sameDepartment(activeStep.department, user?.department || ""),
  );
  const canActOnStep = Boolean(activeStep && (isPrivileged || officerCanAct));
  const canAssignToSelf = Boolean(
    isOfficer && user?.id && application && !application.assigned_officer_id,
  );

  const runAction = async (action: () => Promise<unknown>) => {
    setPendingAction(true);
    setActionError("");
    try {
      await action();
      await loadWorkspace();
    } catch (actionFailure) {
      setActionError(
        actionFailure instanceof Error
          ? actionFailure.message
          : "The action could not be completed.",
      );
    } finally {
      setPendingAction(false);
    }
  };

  if (loading) {
    return (
      <div className="grid min-h-96 place-items-center text-sm text-muted-foreground">
        Loading application workspace…
      </div>
    );
  }

  if (error || !workspace || !application) {
    return (
      <Surface>
        <p role="alert" className="text-sm text-danger">
          {error || "Application not found."}
        </p>
        <Button className="mt-4" variant="outline" asChild>
          <Link to="/$feature" params={{ feature: "applications" }}>
            <ArrowLeft className="mr-2 size-4" /> Back to applications
          </Link>
        </Button>
      </Surface>
    );
  }

  const info = workspace.application_information;
  const terminalStatuses = ["completed", "recovered", "skipped"];
  const completedSteps = workspace.workflow.filter((step) =>
    terminalStatuses.includes(step.status),
  ).length;
  const progress = workspace.workflow.length
    ? Math.round((completedSteps / workspace.workflow.length) * 100)
    : 0;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Application Workspace"
        title={info.reference_id}
        subtitle="Application information, verification records and its complete operational history."
        actions={
          <Button variant="outline" asChild>
            <Link to="/$feature" params={{ feature: "applications" }}>
              <ArrowLeft className="mr-2 size-4" /> Back to applications
            </Link>
          </Button>
        }
      />

      {actionError ? (
        <p
          role="alert"
          className="rounded-lg border border-danger/30 bg-danger/5 p-3 text-sm text-danger"
        >
          {actionError}
        </p>
      ) : null}

      <Surface>
        <h2 className="flex items-center gap-2 text-base font-bold">
          <UserRound className="size-4 text-primary" /> Citizen information
        </h2>
        <DetailGrid
          items={[
            ["Name", workspace.citizen.full_name],
            ["Email", workspace.citizen.email],
            ["Phone", workspace.citizen.phone || "—"],
            [
              "Aadhaar (last 4)",
              workspace.citizen.aadhaar_last4
                ? `•••• ${workspace.citizen.aadhaar_last4}`
                : "Not provided",
            ],
            ["Citizen record ID", String(workspace.citizen.id)],
          ]}
        />
      </Surface>

      <Surface>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h2 className="text-base font-bold">Application information</h2>
          <StatusPill status={formatStatus(info.status)} />
        </div>
        <DetailGrid
          items={[
            ["Application ID", info.reference_id],
            ["Service", info.service_name || "—"],
            ["Department", info.department_name || "—"],
            ["Submitted", formatDate(info.submitted_at)],
            ["Current workflow step", application.current_workflow_step?.name || "—"],
            ["SLA due", formatDate(info.sla_due_at)],
            ["Assigned officer", info.assigned_officer_name || "Unassigned"],
            ["Location", application.location || "—"],
          ]}
        />
        {Object.keys(info.form_data).length ? (
          <div className="mt-5 border-t border-border pt-4">
            <h3 className="text-sm font-semibold">Submitted application data</h3>
            <DetailGrid
              items={Object.entries(info.form_data).map(([key, value]) => [
                key,
                formatValue(value),
              ])}
            />
          </div>
        ) : null}
        {canAssignToSelf ? (
          <Button
            className="mt-5"
            disabled={pendingAction}
            onClick={() => void runAction(() => api.assignApplicationToMe(application.id))}
          >
            Assign application to me
          </Button>
        ) : null}
      </Surface>

      <Surface>
        <h2 className="text-base font-bold">Verified records</h2>
        {workspace.verified_records.length ? (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {workspace.verified_records.map((record) => (
              <div key={record.id} className="rounded-lg border border-border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">{record.record_type}</span>
                  <StatusPill status={formatStatus(record.status)} />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {record.department || "Department unavailable"} · Source record{" "}
                  {record.source_record_id}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Verified {formatDate(record.verified_at)}
                </p>
                <DetailGrid
                  items={Object.entries(record.values).map(([key, value]) => [key, value])}
                />
              </div>
            ))}
          </div>
        ) : (
          <EmptyMessage>No verified records are linked to this application.</EmptyMessage>
        )}
      </Surface>

      <Surface>
        <h2 className="flex items-center gap-2 text-base font-bold">
          <FileText className="size-4 text-primary" /> Documents
        </h2>
        {workspace.documents.length ? (
          <div className="mt-4 space-y-2">
            {workspace.documents.map((document) => (
              <div
                key={document.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border p-3"
              >
                <div>
                  <p className="font-semibold">{document.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {document.doc_type} · Added {formatDate(document.created_at)}
                  </p>
                  {document.verification_score !== null ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Verification score: {document.verification_score}
                    </p>
                  ) : null}
                  {document.fraud_risk_level ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Fraud risk: {document.fraud_risk_level}
                    </p>
                  ) : null}
                </div>
                <StatusPill status={document.is_verified ? "Verified" : "Pending verification"} />
              </div>
            ))}
          </div>
        ) : (
          <EmptyMessage>No documents are linked to this application.</EmptyMessage>
        )}
      </Surface>

      <Surface>
        <h2 className="flex items-center gap-2 text-base font-bold">
          <ShieldCheck className="size-4 text-primary" /> Consent status
        </h2>
        {workspace.consents.length ? (
          <div className="mt-4 space-y-2">
            {workspace.consents.map((consent) => (
              <div key={consent.id} className="rounded-lg border border-border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">{consent.purpose}</span>
                  <StatusPill status={formatStatus(consent.status)} />
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{consent.requested_data}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {consent.source_department || "Source department unavailable"} · Granted{" "}
                  {formatDate(consent.granted_at)} · Expires {formatDate(consent.expires_at)}
                  {consent.revoked_at ? ` · Revoked ${formatDate(consent.revoked_at)}` : ""}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyMessage>No consent records were returned for this application.</EmptyMessage>
        )}
      </Surface>

      <Surface>
        <h2 className="text-base font-bold">Interoperability transactions</h2>
        {workspace.transactions.length ? (
          <div className="mt-4 space-y-3">
            {workspace.transactions.map((transaction) => (
              <div key={transaction.transaction_id} className="rounded-lg border border-border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">
                    {transaction.source_department} → {transaction.requesting_department}
                  </span>
                  <StatusPill status={formatStatus(transaction.status)} />
                </div>
                <p className="mt-1 text-sm">{transaction.data_requested}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {transaction.transaction_id} · Requested {formatDate(transaction.requested_at)} ·
                  Completed {formatDate(transaction.completed_at)}
                </p>
                {transaction.error_message ? (
                  <p className="mt-1 text-sm text-danger">{transaction.error_message}</p>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <EmptyMessage>
            No interoperability transactions are linked to this application.
          </EmptyMessage>
        )}
        {workspace.transaction_events.length ? (
          <div className="mt-4 border-t border-border pt-4">
            <h3 className="text-sm font-semibold">Transaction events</h3>
            <div className="mt-2 space-y-2">
              {workspace.transaction_events.map((event) => (
                <div key={event.id} className="rounded-lg bg-muted/50 p-3 text-sm">
                  <div className="flex flex-wrap justify-between gap-2">
                    <span className="font-medium">{event.event_type}</span>
                    <StatusPill status={formatStatus(event.status)} />
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {event.detail || event.error_message || event.error_code || "—"} ·{" "}
                    {formatDate(event.occurred_at)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </Surface>

      <Surface>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold">Workflow timeline</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {completedSteps} of {workspace.workflow.length} steps completed · {progress}%
            </p>
          </div>
          {activeStep ? <StatusPill status={formatStatus(activeStep.status)} /> : null}
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
        {workspace.workflow.length ? (
          <div className="mt-5 space-y-3">
            {workspace.workflow.map((step, index) => (
              <div
                key={step.step_id || step.key}
                className="flex gap-3 rounded-lg border border-border p-3"
              >
                <span className="mt-0.5">
                  {terminalStatuses.includes(step.status) ? (
                    <CheckCircle2 className="size-5 text-success" />
                  ) : (
                    <Clock3 className="size-5 text-warning" />
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold">
                      {index + 1}. {step.label}
                    </span>
                    <StatusPill status={formatStatus(step.status)} />
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {step.detail || step.error || "No additional step detail."}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {[step.department, step.type, step.attempts ? `${step.attempts} attempts` : ""]
                      .filter(Boolean)
                      .join(" · ")}
                    {step.started_at ? ` · Started ${formatDate(step.started_at)}` : ""}
                    {step.completed_at ? ` · Updated ${formatDate(step.completed_at)}` : ""}
                  </p>
                  {canActOnStep && activeStep?.key === step.key && application ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {step.status === "pending" ? (
                        <Button
                          size="sm"
                          disabled={pendingAction}
                          onClick={() =>
                            void runAction(() =>
                              api.updateWorkflowStage(
                                application.id,
                                step.key,
                                "in_progress",
                                "Work started by assigned officer.",
                              ),
                            )
                          }
                        >
                          Start step
                        </Button>
                      ) : step.status === "in_progress" ? (
                        <>
                          <Button
                            size="sm"
                            disabled={pendingAction}
                            onClick={() =>
                              void runAction(() =>
                                api.updateWorkflowStage(
                                  application.id,
                                  step.key,
                                  "completed",
                                  "Step completed by assigned officer.",
                                ),
                              )
                            }
                          >
                            Complete step
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={pendingAction}
                            onClick={() =>
                              void runAction(() =>
                                api.updateWorkflowStage(
                                  application.id,
                                  step.key,
                                  "failed",
                                  "Step requires operational review.",
                                  "Marked failed by assigned officer.",
                                ),
                              )
                            }
                          >
                            Flag as failed
                          </Button>
                        </>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyMessage>No workflow steps have been recorded.</EmptyMessage>
        )}
        {isOfficer && application.assigned_officer_id !== user?.id ? (
          <p className="mt-4 text-sm text-muted-foreground">
            Workflow actions are available only after you assign this application to yourself.
          </p>
        ) : null}
        {!isOfficer && !isPrivileged ? (
          <p className="mt-4 text-sm text-muted-foreground">
            Your role is read-only for application workflow actions.
          </p>
        ) : null}
      </Surface>

      <Surface>
        <h2 className="text-base font-bold">Exceptions</h2>
        {workspace.exceptions.length ? (
          <div className="mt-4 space-y-2">
            {workspace.exceptions.map((exception) => (
              <div key={exception.id} className="rounded-lg border border-border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">
                    {exception.system} · {exception.category}
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">{exception.severity}</span>
                    <StatusPill status={formatStatus(exception.status)} />
                  </span>
                </div>
                <p className="mt-1 text-sm">{exception.message}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatDate(exception.created_at)}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyMessage>No exceptions are associated with this application.</EmptyMessage>
        )}
      </Surface>

      <Surface>
        <h2 className="text-base font-bold">Audit events</h2>
        {workspace.audit_events.length ? (
          <div className="mt-4 space-y-2">
            {workspace.audit_events.map((event) => (
              <div
                key={`${event.entity_type}-${event.id}`}
                className="flex gap-3 rounded-lg border border-border p-3"
              >
                <Clock3 className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <div className="min-w-0">
                  <p className="font-semibold">{event.action}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {event.details || event.entity_type}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatDate(event.created_at)} ·{" "}
                    {event.actor_id ? `Actor #${event.actor_id}` : "System"}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyMessage>No audit events were returned for this application.</EmptyMessage>
        )}
      </Surface>
    </div>
  );
}

function sameDepartment(left: string, right: string) {
  const normalizedLeft = left.toLowerCase().replace(/[^a-z0-9]/g, "");
  const normalizedRight = right.toLowerCase().replace(/[^a-z0-9]/g, "");
  return Boolean(
    normalizedLeft &&
    normalizedRight &&
    (normalizedLeft.includes(normalizedRight) || normalizedRight.includes(normalizedLeft)),
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

function formatValue(value: unknown) {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function DetailGrid({ items }: { items: [string, string][] }) {
  return (
    <dl className="mt-4 grid gap-4 border-t border-border pt-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map(([label, value]) => (
        <div key={label} className="min-w-0">
          <dt className="text-xs font-semibold uppercase text-muted-foreground">{label}</dt>
          <dd className="mt-1 break-words text-sm font-medium">{value || "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

function EmptyMessage({ children }: { children: string }) {
  return <p className="mt-3 text-sm text-muted-foreground">{children}</p>;
}
