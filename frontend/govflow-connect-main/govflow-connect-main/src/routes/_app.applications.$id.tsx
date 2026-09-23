import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, Clock3, GitBranch, Landmark, RefreshCw, ShieldCheck, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader, StatusPill, Surface } from "@/components/govflow/bits";
import { api, type MeshApplication, type MeshAuditLog, type MeshConsent, type MeshNodePlatform } from "@/lib/api";

export const Route = createFileRoute("/_app/applications/$id")({ component: ApplicationDetailsPage });

type DetailState = {
  application: MeshApplication | null;
  consents: MeshConsent[];
  integrations: MeshNodePlatform[];
  exceptions: any[];
  auditLogs: MeshAuditLog[];
};

function ApplicationDetailsPage() {
  const { id } = Route.useParams();
  const [data, setData] = useState<DetailState>({ application: null, consents: [], integrations: [], exceptions: [], auditLogs: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      api.getApplication(id),
      api.getConsents(),
      api.getPlatforms(),
      api.getExceptions(),
      api.getAuditLogs(50, id),
    ]).then(([application, consents, integrations, exceptions, auditLogs]) => {
      if (!active) return;
      if (!application) throw new Error("Application not found");
      setData({
        application,
        consents: consents.filter((item) => item.application_id === application.id || item.applicationId === id),
        integrations,
        exceptions: exceptions.filter((item) => item.application_id === application.id || item.applicationId === id),
        auditLogs,
      });
    }).catch((detail) => { if (active) setError(detail.message || "Unable to load application details."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  const application = data.application;
  const workflow = application?.workflow || [];
  const completed = workflow.filter((stage) => ["completed", "recovered"].includes(stage.status)).length;
  const progress = workflow.length ? Math.round((completed / workflow.length) * 100) : 0;
  const currentStage = workflow.find((stage) => !["completed", "recovered"].includes(stage.status)) || workflow.find((stage) => stage.status === "recovered");
  const consentStatus = data.consents.length && data.consents.every((item) => item.status === "granted") ? "Active" : data.consents.length ? "Review" : "Pending";
  const submitted = application ? formatDate(application.created_at || (application as MeshApplication & { createdAt?: string }).createdAt) : "—";
  const exceptions = useMemo(() => data.exceptions, [data.exceptions]);

  if (loading) return <div className="grid min-h-96 place-items-center text-sm text-muted-foreground">Loading application journey…</div>;
  if (error || !application) return <Surface><p className="text-sm text-danger">{error || "Application not found."}</p><Button className="mt-4" variant="outline" asChild><Link to="/$feature" params={{ feature: "applications" }}><ArrowLeft className="mr-2 size-4" /> Back to applications</Link></Button></Surface>;

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Application Details" title={application.reference_id} subtitle="Complete citizen journey across GovFlow departments and connected systems." actions={<Button variant="outline" asChild><Link to="/$feature" params={{ feature: "applications" }}><ArrowLeft className="mr-2 size-4" /> Back to applications</Link></Button>} />
      <Surface>
        <div className="flex flex-wrap items-start justify-between gap-4"><div className="flex items-start gap-4"><span className="grid size-12 place-items-center rounded-xl bg-primary/10 text-primary"><Landmark className="size-6" /></span><div><h2 className="text-lg font-bold">{application.form_data?.["name"] || application.citizen_name || `Citizen #${application.citizen_id}`}</h2><p className="mt-1 text-sm text-muted-foreground">{application.service_name || "Post-Matric Scholarship"} · {application.location || "Nashik, Maharashtra"}</p></div></div><StatusPill status={formatStatus(application.status)} /></div>
        <DetailGrid items={[["Application ID", application.reference_id], ["Citizen name", application.form_data?.["name"] || application.citizen_name || `Citizen #${application.citizen_id}`], ["Service", application.service_name || "Post-Matric Scholarship"], ["Location", application.location || "Nashik, Maharashtra"], ["Submitted", submitted], ["Current workflow stage", currentStage?.label || "Complete"]]} />
      </Surface>
      <div className="grid gap-4 md:grid-cols-3"><Metric icon={<GitBranch className="size-4" />} label="Progress" value={`${progress}%`} /><Metric icon={<ShieldCheck className="size-4" />} label="Consent status" value={consentStatus} /><Metric icon={<Clock3 className="size-4" />} label="Current stage" value={currentStage?.label || "Complete"} /></div>
      <Surface><div className="flex items-center justify-between gap-3"><div><h2 className="text-base font-bold">Workflow timeline</h2><p className="mt-1 text-sm text-muted-foreground">{completed} of {workflow.length} stages completed or recovered.</p></div><span className="text-sm font-semibold text-primary">{progress}%</span></div><div className="mt-4 h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary transition-all" style={{ width: `${progress}%` }} /></div><div className="mt-5 space-y-3">{workflow.map((stage, index) => <div key={`${stage.key}-${index}`} className="flex gap-3 rounded-lg border border-border p-3"><span className="mt-0.5">{stage.status === "recovered" ? <RefreshCw className="size-5 text-teal" /> : ["completed", "recovered"].includes(stage.status) ? <CheckCircle2 className="size-5 text-success" /> : stage.status === "pending" ? <Clock3 className="size-5 text-warning" /> : <TriangleAlert className="size-5 text-primary" />}</span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><span className="font-semibold">{index + 1}. {stage.label}</span><StatusPill status={formatStatus(stage.status)} /></div><p className="mt-1 text-sm text-muted-foreground">{stage.detail || "Stage is queued for processing."}{stage.attempts > 1 ? ` · ${stage.attempts} attempts` : ""}</p></div></div>)}</div></Surface>
      <div className="grid gap-4 lg:grid-cols-2"><Surface><h2 className="text-base font-bold">Connected departments and integrations</h2><div className="mt-4 grid gap-2 sm:grid-cols-2">{data.integrations.map((integration) => <div key={integration.id} className="rounded-lg border border-border p-3"><div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold">{integration.name}</span><StatusPill status={integration.status === "active" ? "Active" : "Review"} /></div><p className="mt-1 text-xs text-muted-foreground">{integration.description || "GovFlow connected verification system"}</p></div>)}</div></Surface><Surface><h2 className="text-base font-bold">Consent status</h2><div className="mt-4 space-y-2">{data.consents.map((consent) => <div key={consent.id} className="rounded-lg border border-border p-3"><div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold">{consent.target_platform_name || consent.purpose}</span><StatusPill status={formatStatus(consent.status)} /></div><p className="mt-1 text-xs text-muted-foreground">{consent.source_platform_name} · {consent.purpose}</p></div>)}</div></Surface></div>
      <div className="grid gap-4 lg:grid-cols-2"><Surface><h2 className="text-base font-bold">Exceptions and retries</h2><div className="mt-4 space-y-2">{exceptions.length ? exceptions.map((item) => <div key={item.id} className="rounded-lg border border-border p-3"><div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold">{item.stage}</span><StatusPill status={formatStatus(item.status)} /></div><p className="mt-1 text-xs text-muted-foreground">{item.code} · {item.message}</p><p className="mt-1 text-xs text-muted-foreground">Recovery: {item.recovery} · Attempts: {item.attempts}</p></div>) : <p className="text-sm text-muted-foreground">No exceptions or retries recorded.</p>}</div></Surface><Surface><h2 className="text-base font-bold">Audit and activity history</h2><div className="mt-4 space-y-2">{data.auditLogs.length ? data.auditLogs.map((log) => <div key={log.id} className="rounded-lg border border-border p-3"><p className="text-sm font-semibold">{log.action}</p><p className="mt-1 text-xs text-muted-foreground">{log.details} · {formatDate(log.created_at || (log as MeshAuditLog & { createdAt?: string }).createdAt)}</p></div>) : <p className="text-sm text-muted-foreground">No audit activity recorded.</p>}</div></Surface></div>
    </div>
  );
}

function formatStatus(status: string) { return status === "under_review" ? "Review" : status.charAt(0).toUpperCase() + status.slice(1); }
function formatDate(value?: string) { return value ? new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—"; }
function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <Surface className="flex items-center gap-3"><span className="grid size-9 place-items-center rounded-lg bg-primary/10 text-primary">{icon}</span><div><p className="text-xs text-muted-foreground">{label}</p><p className="font-bold">{value}</p></div></Surface>; }
function DetailGrid({ items }: { items: [string, string][] }) { return <dl className="mt-6 grid gap-4 border-t border-border pt-5 sm:grid-cols-2 lg:grid-cols-3">{items.map(([label, value]) => <div key={label}><dt className="text-xs font-semibold uppercase text-muted-foreground">{label}</dt><dd className="mt-1 text-sm font-medium wrap-break-word">{value}</dd></div>)}</dl>; }