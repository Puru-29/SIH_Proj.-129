import type { DepartmentName, GovernmentService } from "@/services/api";

export type ApplicationFieldConfig = {
  id: string;
  label: string;
  required: boolean;
  type?: "text" | "email" | "tel" | "date" | "number" | "select" | "checkbox";
  options?: string[];
  recordKey?: string;
};

export type VerifiedRecordRequirement = {
  key: string;
  name: string;
  aliases?: string[];
  sourceDepartment: DepartmentName;
  sourceSystem?: string;
  fieldsCovered: string[];
  dataRequested: string;
};

export type ConsentRequirement = {
  key: string;
  sourceDepartment: DepartmentName;
  dataRequested: string;
  purpose: string;
  whenField?: string;
  whenValue?: string;
};

export type ApplicationServiceConfig = {
  serviceId: string;
  serviceName: string;
  aliases: string[];
  backendServiceNames: string[];
  department: DepartmentName;
  description: string;
  requiredInformation: ApplicationFieldConfig[];
  requiredDocuments: string[];
  requiredVerifiedRecords: VerifiedRecordRequirement[];
  consentRequirements: ConsentRequirement[];
  connectedDepartments: DepartmentName[];
  interoperabilityWorkflow: string[];
  processingStages: string[];
};

export function getApplicationServiceConfig(service: GovernmentService): ApplicationServiceConfig {
  const documents = service.requiredDocuments ?? [];
  const departments = service.interoperabilityRequirements ?? [];
  return {
    serviceId: service.id,
    serviceName: service.name,
    aliases: [service.name, service.code],
    backendServiceNames: [service.name, service.code],
    department: service.department,
    description: service.description,
    requiredInformation: (service.requiredData ?? []).map((label, index) => ({
      id: `backend_field_${index + 1}`,
      label,
      required: true,
    })),
    requiredDocuments: documents,
    requiredVerifiedRecords: [],
    consentRequirements: [],
    connectedDepartments: departments,
    interoperabilityWorkflow: service.workflow ?? [],
    processingStages: service.workflow ?? [],
  };
}
