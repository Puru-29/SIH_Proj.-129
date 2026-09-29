import { api, type MeshApplication } from "@/lib/api";
import type { ApplicationItem, GovernmentService } from "./api";

function formatDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(date);
}

function getSubmittedAddress(application: MeshApplication): string | undefined {
  const formData = application.form_data;
  if (!formData) return undefined;
  const parts = [
    formData["address"],
    formData["village_city"],
    formData["taluka"],
    formData["district"],
    formData["state"],
    formData["pin_code"],
  ]
    .filter((value): value is string => typeof value === "string" && value.trim() !== "")
    .map((value) => value.trim());
  const uniqueParts = [...new Set(parts)];
  return uniqueParts.length ? uniqueParts.join(", ") : undefined;
}

function mapApplication(application: MeshApplication): ApplicationItem {
  const workflow = application.workflow ?? [];
  const submittedAddress = getSubmittedAddress(application);
  const progressed = workflow.filter((step) =>
    ["completed", "recovered", "skipped", "in_progress"].includes(step.status.toLowerCase()),
  ).length;
  return {
    id: application.reference_id,
    backendId: application.id,
    applicationId: application.reference_id,
    service: application.service_name ?? "",
    department: application.department_name ?? "",
    submittedDate: formatDate(application.created_at) ?? application.created_at,
    status:
      application.status === "under_review"
        ? "Under Review"
        : application.status.charAt(0).toUpperCase() + application.status.slice(1),
    ...(workflow.length ? { progress: Math.round((progressed / workflow.length) * 100) } : {}),
    lastUpdated: formatDate(application.updated_at) ?? application.updated_at,
    timeline: workflow.map((step) => ({
      label: step.label,
      date: formatDate(step.completed_at ?? step.started_at),
      completed: ["completed", "recovered", "skipped"].includes(step.status.toLowerCase()),
      inProgress: step.status.toLowerCase() === "in_progress",
    })),
    expectedNextStep: application.current_workflow_step?.name ?? "",
    ...(submittedAddress ? { submittedAddress } : {}),
  };
}

export async function getApplications(): Promise<ApplicationItem[]> {
  return (await api.getApplications()).map(mapApplication);
}

export async function getApplicationById(
  applicationId: string,
): Promise<ApplicationItem | undefined> {
  const application = await api.getApplication(applicationId);
  return application ? mapApplication(application) : undefined;
}

export async function submitApplication(
  service: GovernmentService,
  formData: Record<string, unknown>,
  consent: boolean,
): Promise<ApplicationItem> {
  const created = await api.createApplication({
    service_id: service.backendId,
    form_data: formData,
    consent,
  });
  return mapApplication(created);
}
