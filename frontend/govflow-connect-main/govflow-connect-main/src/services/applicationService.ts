import { applicationsMock, type ApplicationItem, getApplicationById as getById, submitApplication as submit } from "./api";

export async function getApplications(): Promise<ApplicationItem[]> {
  return Promise.resolve(applicationsMock);
}

export async function getApplicationById(applicationId: string): Promise<ApplicationItem | undefined> {
  return getById(applicationId);
}

export async function submitApplication(service: { name: string; department: string; processingTime?: string; fee?: string }): Promise<ApplicationItem> {
  return submit({
    id: service.name.toLowerCase().replace(/\s+/g, "-"),
    name: service.name,
    department: service.department as any,
    description: "Mock service request",
    processingTime: service.processingTime || "7 days",
    fee: service.fee || "Free",
    requiredDocuments: ["Applicant ID"],
    onlineAvailability: true,
    category: "Revenue",
  } as any);
}
