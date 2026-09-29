import { api, type MeshApplication } from "@/lib/api";
import type { ApplicationItem, GovernmentService } from "./api";

function mapApplication(application: MeshApplication): ApplicationItem {
  const workflow = application.workflow ?? [];
  const completed = workflow.filter((step) =>
    ["completed", "recovered", "skipped"].includes(step.status.toLowerCase()),
  ).length;
  return {
    id: application.reference_id,
    backendId: application.id,
    applicationId: application.reference_id,
    service: application.service_name ?? "",
    department: application.department_name ?? "",
    submittedDate: application.created_at,
    status:
      application.status === "under_review"
        ? "Under Review"
        : application.status.charAt(0).toUpperCase() + application.status.slice(1),
    ...(workflow.length ? { progress: Math.round((completed / workflow.length) * 100) } : {}),
    lastUpdated: application.updated_at,
    timeline: workflow.map((step) => ({
      label: step.label,
      date: step.completed_at ?? step.started_at ?? null,
      completed: ["completed", "recovered", "skipped"].includes(step.status.toLowerCase()),
      inProgress: step.status.toLowerCase() === "in_progress",
    })),
    expectedNextStep: application.current_workflow_step?.name ?? "",
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
