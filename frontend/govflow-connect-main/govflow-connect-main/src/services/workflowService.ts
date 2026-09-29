import { api } from "@/lib/api";

export async function getWorkflowDefinitions(serviceId?: number) {
  return api.getWorkflowDefinitions(serviceId);
}

export async function getApplicationWorkflow(applicationId: number | string) {
  return api.getApplicationWorkflow(applicationId);
}

export async function updateWorkflowStage(
  applicationId: number,
  stageKey: string,
  status: string,
  detail?: string,
) {
  return api.updateWorkflowStage(applicationId, stageKey, status, detail);
}

export const workflowService = {
  getWorkflowDefinitions,
  getApplicationWorkflow,
  updateWorkflowStage,
};
