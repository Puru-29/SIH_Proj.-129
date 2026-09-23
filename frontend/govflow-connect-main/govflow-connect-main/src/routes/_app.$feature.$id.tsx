import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowLeft, Boxes, FileStack, GitBranch, Landmark } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EventFeed, useWorkflowRun, WorkflowCanvas } from "@/components/govflow/workflow";
import { PageHeader, StatusPill, Surface } from "@/components/govflow/bits";
import { LINEAGE_EVENTS, getService, type Workflow } from "@/lib/govflow/data";
import { useGovFlow } from "@/lib/govflow/store";

export const Route = createFileRoute("/_app/$feature/$id")({ component: FeatureDetailPage });

function FeatureDetailPage() {
  const { feature, id } = Route.useParams();
  const {
    applications,
    workflows,
    integrations,
    consents,
    exceptions,
    consentHistory,
    createWorkflow,
    pushNotification,
  } = useGovFlow();
  const service = feature === "services" ? getService(id) : undefined;
  const workflow = feature === "workflows" ? workflows.find((item) => item.id === id) : undefined;
  const application =
    feature === "applications" ? applications.find((item) => item.id === id) : undefined;
  const integration =
    feature === "integrations" ? integrations.find((item) => item.id === id) : undefined;
  const applicationWorkflow = application
    ? workflows.find((item) => item.id === getService(application.serviceId)?.workflowId)
    : undefined;
  const activeWorkflow = applicationWorkflow ?? workflow ?? workflows[0];
  const runner = useWorkflowRun(activeWorkflow?.stages ?? [], { speed: 1.4 });
  const [draftName, setDraftName] = useState("New citizen service workflow");
  const [draftError, setDraftError] = useState("");
  const [draftSaved, setDraftSaved] = useState("");
  const title =
    service?.name ??
    workflow?.name ??
    application?.id ??
    integration?.name ??
    (feature === "workflows" && id === "builder" ? "Workflow Builder" : "Workspace item");
  const icon =
    feature === "services"
      ? Landmark
      : feature === "workflows"
        ? GitBranch
        : feature === "integrations"
          ? Boxes
          : FileStack;
  const Icon = icon;

  const createDraft = () => {
    const name = draftName.trim();
    if (!name) {
      setDraftError("Enter a workflow name before saving.");
      return;
    }
    const draft: Workflow = {
      id: `wf-custom-${Date.now()}`,
      name,
      serviceId: workflows[0]?.serviceId ?? "scholarship",
      version: "v1.0",
      status: "Draft",
      runs: 0,
      successRate: 100,
      avgMinutes: workflows[0]?.avgMinutes ?? 5,
      stages: workflows[0]?.stages ?? [],
    };
    createWorkflow(draft);
    pushNotification({
      title: "Workflow draft created",
      body: `${name} is ready for configuration.`,
      kind: "Workflow",
    });
    setDraftError("");
    setDraftSaved(`${name} saved as a draft. Open Workflows to view it.`);
    setDraftName("");
  };

  if (feature === "workflows" && id === "builder") {
    return (
      <>
        <PageHeader
          eyebrow="Workflow Orchestrator"
          title="Workflow Builder"
          subtitle="Create, inspect and run a cross-department orchestration flow."
          actions={
            <Button variant="outline" asChild>
              <Link to="/$feature" params={{ feature: "workflows" }}>
                <ArrowLeft className="mr-2 size-4" /> Back to workflows
              </Link>
            </Button>
          }
        />
        <Surface>
          <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
            <Input
              value={draftName}
              onChange={(event) => setDraftName(event.target.value)}
              placeholder="Workflow name"
            />
            <Button onClick={createDraft}>
              <GitBranch className="mr-2 size-4" /> Save draft
            </Button>
          </div>
          {draftError ? <p className="mt-2 text-sm text-danger">{draftError}</p> : null}
          {draftSaved ? (
            <p className="mt-2 rounded-lg border border-success/25 bg-success/10 px-3 py-2 text-sm font-medium text-success">
              {draftSaved}
            </p>
          ) : null}
          <p className="mt-3 text-xs text-muted-foreground">
            New drafts start from the scholarship orchestration template and can be edited before
            backend publishing.
          </p>
        </Surface>
        <WorkflowWorkspace
          workflow={activeWorkflow as Workflow}
          runner={runner}
          onRun={() => {
            runner.run();
            pushNotification({
              title: "Workflow run started",
              body: `${activeWorkflow?.name ?? "Workflow"} is running.`,
              kind: "Workflow",
            });
          }}
        />
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="GovFlow Workspace"
        title={title}
        subtitle={service?.summary ?? integration?.protocol ?? "Connected GovFlow state"}
        actions={
          <Button variant="outline" asChild>
            <Link to="/$feature" params={{ feature }}>
              <ArrowLeft className="mr-2 size-4" /> Back to {feature}
            </Link>
          </Button>
        }
      />
      <Surface>
        <div className="flex items-start gap-4">
          <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
            <Icon className="size-6" />
          </span>
          <div className="min-w-0">
            <h2 className="text-lg font-bold">
              {application ? "Unified citizen journey" : "Operational details"}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {application
                ? `${application.citizen} · ${application.id}`
                : "This workspace is connected to the shared GovFlow state."}
            </p>
          </div>
        </div>
        {service ? (
          <DetailGrid
            items={[
              ["Category", service.category],
              ["Department", service.department],
              ["SLA", service.sla],
              ["Fee", service.fee],
              ["Connected systems", service.systems.join(", ")],
            ]}
          />
        ) : null}
        {workflow ? (
          <DetailGrid
            items={[
              ["Version", workflow.version],
              ["Status", workflow.status],
              ["Runs", workflow.runs.toLocaleString()],
              ["Success rate", `${workflow.successRate}%`],
              ["Stages", String(workflow.stages.length)],
            ]}
          />
        ) : null}
        {application ? (
          <DetailGrid
            items={[
              ["Citizen", application.citizen],
              ["Service", getService(application.serviceId)?.name ?? "—"],
              ["Submitted", application.submitted],
              ["Status", application.status],
              [
                "Current stage",
                applicationWorkflow?.stages.find((stage) => stage.id === application.stageId)
                  ?.name ?? "—",
              ],
            ]}
          />
        ) : null}
        {integration ? (
          <DetailGrid
            items={[
              ["Protocol", integration.protocol],
              ["Owner", integration.owner],
              ["Health", integration.health],
              ["Success rate", `${integration.successRate}%`],
              ["Base URL", integration.baseUrl],
            ]}
          />
        ) : null}
      </Surface>
      {applicationWorkflow ? (
        <WorkflowWorkspace
          workflow={applicationWorkflow}
          runner={runner}
          onRun={() => {
            runner.run();
            pushNotification({
              title: "Workflow run started",
              body: `${applicationWorkflow.name} is running.`,
              kind: "Workflow",
            });
          }}
        />
      ) : workflow ? (
        <WorkflowWorkspace
          workflow={workflow}
          runner={runner}
          onRun={() => {
            runner.run();
            pushNotification({
              title: "Workflow run started",
              body: `${workflow.name} is running.`,
              kind: "Workflow",
            });
          }}
        />
      ) : null}
      {application ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Surface>
            <h2 className="text-base font-bold">Consent trail</h2>
            <div className="mt-4 space-y-3">
              {consents
                .filter((item) => item.applicationId === application.id)
                .map((item) => (
                  <div key={item.id} className="rounded-lg border border-border p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold">{item.recipient}</span>
                      <StatusPill status={item.status} />
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.dataRequested} · {item.purpose}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      History:{" "}
                      {(consentHistory[item.id] ?? [])
                        .map((entry) => `${entry.status} · ${entry.timestamp}`)
                        .join(" → ")}
                    </p>
                  </div>
                ))}
            </div>
          </Surface>
          <Surface>
            <h2 className="text-base font-bold">Exception trail</h2>
            <div className="mt-4 space-y-3">
              {exceptions
                .filter((item) => item.applicationId === application.id)
                .map((item) => (
                  <div key={item.id} className="rounded-lg border border-border p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold">{item.stage}</span>
                      <StatusPill status={item.status} />
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.code} · {item.message}
                    </p>
                  </div>
                ))}
            </div>
          </Surface>
        </div>
      ) : null}
      {application ? <LineagePanel /> : null}
    </>
  );
}

function LineagePanel() {
  return (
    <Surface>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-bold">Data lineage</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Exactly how application data travels across the governed journey.
          </p>
        </div>
        <span className="text-xs font-semibold text-teal">Consent-bound trace</span>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-4">
        {LINEAGE_EVENTS.map((event, index) => (
          <div key={event.id} className="relative rounded-xl border border-border bg-card p-4">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] font-bold uppercase text-primary">Hop {index + 1}</span>
              <span className="text-[10px] text-muted-foreground">{event.timestamp}</span>
            </div>
            <p className="mt-3 text-sm font-semibold">{event.source}</p>
            <p className="my-2 text-xs text-teal">↓ {event.destination}</p>
            <p className="text-xs text-muted-foreground">{event.api}</p>
            <p className="mt-3 text-xs">
              <span className="font-semibold">Fields:</span> {event.fields.join(", ")}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              <span className="font-semibold">Consent:</span> {event.consentRef}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              <span className="font-semibold">Transform:</span> {event.transformation}
            </p>
          </div>
        ))}
      </div>
    </Surface>
  );
}

function WorkflowWorkspace({
  workflow,
  runner,
  onRun,
}: {
  workflow: Workflow;
  runner: ReturnType<typeof useWorkflowRun>;
  onRun: () => void;
}) {
  const [selectedStage, setSelectedStage] = useState<string | null>(null);

  return (
    <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
      <Surface>
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold">Live orchestration</h2>
            <p className="text-sm text-muted-foreground">
              {workflow.stages.length} connected stages
            </p>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Button size="sm" onClick={onRun} disabled={runner.running}>
              {runner.running ? "Running..." : "Start"}
            </Button>
            {runner.running ? (
              <Button size="sm" variant="outline" onClick={runner.pause}>
                Pause
              </Button>
            ) : null}
            {runner.paused ? (
              <Button size="sm" variant="outline" onClick={runner.resume}>
                Resume
              </Button>
            ) : null}
            <Button
              size="sm"
              variant="outline"
              onClick={runner.simulateFailure}
              disabled={runner.failureRequested}
            >
              Simulate failure
            </Button>
            <Button size="sm" variant="ghost" onClick={runner.reset}>
              Reset
            </Button>
          </div>
        </div>
        <div className="mt-4">
          <WorkflowCanvas
            stages={workflow.stages}
            states={runner.states}
            activeId={runner.activeId}
            onSelect={(stage) =>
              setSelectedStage(`${stage.name} · ${stage.department} · ${stage.system}`)
            }
          />
        </div>
        {selectedStage ? (
          <p className="mt-3 rounded-lg bg-muted/60 px-3 py-2 text-xs text-muted-foreground">
            Selected stage: {selectedStage}
          </p>
        ) : null}
      </Surface>
      <Surface>
        <h2 className="text-base font-bold">Event stream</h2>
        <div className="mt-4 max-h-130 overflow-y-auto">
          <EventFeed events={runner.events} />
        </div>
      </Surface>
    </div>
  );
}

function DetailGrid({ items }: { items: [string, string][] }) {
  return (
    <dl className="mt-6 grid gap-4 border-t border-border pt-5 sm:grid-cols-2 lg:grid-cols-3">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt className="text-xs font-semibold text-muted-foreground uppercase">{label}</dt>
          <dd className="mt-1 text-sm font-medium wrap-break-word">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
