export type DepartmentName = string;

export type ApplicationStatus = "submitted" | "under_review" | "approved" | "rejected" | "draft";

export type ConsentStatus = "pending" | "granted" | "revoked" | "expired";
export type NotificationType = string;

export type CitizenProfile = {
  id: string;
  citizenId: string;
  fullName: string;
  email: string;
  phone: string;
  address?: string;
  preferredLanguage?: string;
  verifiedMobile?: boolean;
  verifiedEmail?: boolean;
  aadhaarLast4?: string | null;
};

export type GovernmentService = {
  id: string;
  backendId: number;
  name: string;
  code: string;
  department: string;
  departmentId: number;
  platformId: number;
  description: string;
  active: boolean;
  processingTime?: string;
  estimatedProcessingTime?: string;
  fee?: string;
  requiredDocuments?: string[];
  requiredData?: string[];
  interoperabilityRequirements?: string[];
  workflow?: string[];
  category?: string;
  onlineAvailability?: boolean;
};

export type RecordItem = {
  id: string;
  name: string;
  sourceDepartment: string;
  verificationStatus: string;
  lastVerified: string | null;
  usedByApplications: string[];
};

export type ApplicationItem = {
  id: string;
  service: string;
  department: string;
  submittedDate: string;
  status: string;
  progress?: number;
  lastUpdated: string;
  applicationId: string;
  backendId: number;
  timeline: Array<{ label: string; date: string | null; completed: boolean; inProgress?: boolean }>;
  expectedNextStep: string;
  contact?: string;
};

export type ConsentRequest = {
  id: string;
  backendId: number;
  department: string;
  data: string;
  purpose: string;
  status: string;
  grantedOn?: string;
  expires?: string;
  sourceDepartment?: string;
  applicationId?: string;
};

export type NotificationItem = {
  id: string;
  title: string;
  description: string;
  time: string;
  type: NotificationType;
  read: boolean;
  relatedApplication?: string | undefined;
  relatedTransaction?: string | undefined;
};

export type DocumentItem = {
  id: string;
  name: string;
  category: string;
  uploadedAt: string;
  verificationStatus: string;
};

export type GrievanceItem = {
  id: string;
  category: string;
  relatedApplication: string;
  department: string;
  description: string;
  priority: string;
  status: string;
};

export type AuditEvent = {
  id: number;
  timestamp: string;
  actor_id: number | null;
  actor_name: string | null;
  actor_role: string | null;
  department_id: number | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  transaction_id: string | null;
  result: string | null;
  metadata: Record<string, unknown>;
};
