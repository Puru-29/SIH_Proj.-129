import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Boxes, FileStack, GitBranch, Landmark } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader, StatusPill, Surface } from "@/components/govflow/bits";
import { useGovFlow } from "@/lib/govflow/store";

export const Route = createFileRoute("/_app/$feature/$id")({ component: FeatureDetailPage });

function FeatureDetailPage() {
  const { feature, id } = Route.useParams();
  const { applications, workflows, integrations, services, ready, loadError } = useGovFlow();
  const service = feature === "services" ? services.find((item) => item.id === id) : undefined;
  const workflow = feature === "workflows" ? workflows.find((item) => item.id === id) : undefined;
  const application =
    feature === "applications" ? applications.find((item) => item.id === id) : undefined;
  const integration =
    feature === "integrations" ? integrations.find((item) => item.id === id) : undefined;
  const linkedService = application
    ? services.find((item) => item.id === application.serviceId)
    : undefined;
  const currentWorkflow = linkedService?.workflowId
    ? workflows.find((item) => item.id === linkedService.workflowId)
    : undefined;
  const title =
    service?.name ?? workflow?.name ?? application?.id ?? integration?.name ?? "Workspace item";
  const Icon =
    feature === "services"
      ? Landmark
      : feature === "workflows"
        ? GitBranch
        : feature === "integrations"
          ? Boxes
          : FileStack;

  return (
    <>
      <PageHeader
        eyebrow="Government workspace"
        title={title}
        subtitle={service?.summary ?? integration?.protocol ?? "Details from the connected service"}
        actions={
          <Button variant="outline" asChild>
            <Link to="/$feature" params={{ feature }}>
              <ArrowLeft className="mr-2 size-4" /> Back to {feature}
            </Link>
          </Button>
        }
      />
      {!ready && !loadError ? (
        <Surface>
          <p className="text-sm text-muted-foreground">Loading details…</p>
        </Surface>
      ) : loadError ? (
        <Surface>
          <p role="alert" className="text-sm text-danger">
            {loadError}
          </p>
        </Surface>
      ) : !service && !workflow && !application && !integration ? (
        <Surface>
          <p className="text-sm text-muted-foreground">The requested record was not found.</p>
        </Surface>
      ) : (
        <>
          <Surface>
            <div className="flex items-start gap-4">
              <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                <Icon className="size-6" />
              </span>
              <div className="min-w-0">
                <h2 className="text-lg font-bold">
                  {application ? "Application details" : "Operational details"}
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {application
                    ? `${application.citizen} · ${application.id}`
                    : (service?.summary ?? integration?.owner ?? "")}
                </p>
              </div>
            </div>
            {service ? (
              <DetailGrid
                items={[
                  ["Department", service.department],
                  ["Category", service.category ?? "—"],
                  ["SLA", service.sla ?? "—"],
                  ["Fee", service.fee ?? "—"],
                ]}
              />
            ) : null}
            {workflow ? (
              <DetailGrid
                items={[
                  ["Version", workflow.version],
                  ["Status", workflow.status],
                  ["Stages", String(workflow.stages.length)],
                ]}
              />
            ) : null}
            {application ? (
              <DetailGrid
                items={[
                  ["Citizen", application.citizen],
                  ["Service", linkedService?.name ?? "—"],
                  ["Submitted", application.submitted || "—"],
                  ["Status", application.status],
                  [
                    "Current stage",
                    currentWorkflow?.stages.find((stage) => stage.id === application.stageId)
                      ?.name ?? "—",
                  ],
                ]}
              />
            ) : null}
            {integration ? (
              <DetailGrid
                items={[
                  ["Protocol", integration.protocol],
                  ["Owner", integration.owner || "—"],
                  ["Health", integration.health],
                  [
                    "Response time",
                    integration.latencyMs !== undefined ? `${integration.latencyMs} ms` : "—",
                  ],
                ]}
              />
            ) : null}
          </Surface>
          {workflow || currentWorkflow ? (
            <Surface>
              <h2 className="text-base font-bold">Workflow steps</h2>
              <ol className="mt-4 space-y-3">
                {(workflow ?? currentWorkflow)?.stages.map((stage, index) => (
                  <li key={stage.id} className="flex gap-3 rounded-lg border border-border p-3">
                    <span className="grid size-7 shrink-0 place-items-center rounded-full bg-muted text-xs font-semibold">
                      {index + 1}
                    </span>
                    <div>
                      <p className="text-sm font-semibold">{stage.name}</p>
                      {stage.department ? (
                        <p className="text-xs text-muted-foreground">{stage.department}</p>
                      ) : null}
                    </div>
                    {application && stage.id === application.stageId ? (
                      <span className="ml-auto">
                        <StatusPill status="Current" />
                      </span>
                    ) : null}
                  </li>
                )) ?? (
                  <li className="text-sm text-muted-foreground">
                    No workflow steps are configured.
                  </li>
                )}
              </ol>
            </Surface>
          ) : null}
        </>
      )}
    </>
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
