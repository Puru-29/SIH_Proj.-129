import axios from "axios";
import { getAccessToken, setAccessToken } from "@/lib/auth-token";
import {
  apiErrorMessage,
  authenticatedApiClient,
  markSessionActive,
  refreshAccessToken,
} from "@/lib/http";

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

export interface UserProfile {
  id: number;
  full_name: string;
  email: string;
  phone?: string | null;
  department?: string | null;
  aadhaar_last4?: string | null;
  role:
    | "citizen"
    | "officer"
    | "admin"
    | "developer"
    | "operator"
    | "auditor"
    | "department_officer"
    | "system_admin"
    | "interoperability_admin";
  is_active: boolean;
  staff_request_pending?: boolean;
  created_at: string;
}

export interface MeshUser {
  id: number;
  full_name: string;
  email: string;
  role: UserProfile["role"];
  department?: string | null;
  is_active: boolean;
  staff_request_pending?: boolean;
  created_at: string;
}

export type ManagedStaffRole = "department_officer" | "interoperability_admin" | "system_admin";

export type StaffRequestRole = "department_officer" | "interoperability_admin";

export interface ManagedUserCreate {
  full_name: string;
  email: string;
  password: string;
  role: ManagedStaffRole;
  phone?: string;
  department_id?: number;
}

export interface StaffAccountRequest {
  full_name: string;
  email: string;
  password: string;
  role: StaffRequestRole;
  phone?: string;
  department_id?: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface DashboardStats {
  total_applications: number;
  applications_by_status: Record<string, number>;
  total_mesh_nodes: number;
  active_mesh_nodes: number;
  total_departments: number;
  total_services: number;
  total_consents_granted: number;
  total_audit_events: number;
  total_documents_verified: number;
  api_success_rate: number;
  avg_latency_ms: number;
  fraud_anomalies_detected: number;
  system_status: string;
  timestamp: number;
}

export interface MeshNodePlatform {
  id: number;
  name: string;
  slug: string;
  status: "active" | "degraded" | "offline";
  base_url?: string | null;
  api_version: string;
  department?: string | null;
  description?: string | null;
  department_id: number;
}

export interface MeshDepartment {
  id: number;
  name: string;
  code?: string;
}

export interface ServiceApplicationSource {
  department: string;
  department_id: number;
  platform_id: number;
}

export interface MeshService {
  id: number;
  name: string;
  code: string;
  description?: string | null;
  is_active: boolean;
  department_id: number;
  platform_id: number;
}

export interface ServiceFormField {
  id: string;
  type: "text" | "email" | "tel" | "date" | "number" | "select" | "checkbox";
  label: string;
  required: boolean;
  help_text?: string;
  options?: string[];
  pattern?: string;
  max_length?: number;
  default?: string;
  visible_if?: { field: string; equals: string };
}

export interface ServiceFormSection {
  id: string;
  label: string;
  fields: ServiceFormField[];
  description?: string;
}

export interface ServiceFormSchema {
  service_id: number;
  service_name: string;
  department_id: number;
  sections: ServiceFormSection[];
  fields: ServiceFormField[];
  workflow: string[];
}

export interface MeshApplication {
  id: number;
  reference_id: string;
  status: "draft" | "submitted" | "under_review" | "approved" | "rejected";
  remarks?: string | null;
  citizen_id: number;
  citizen_name?: string | null;
  citizen_email?: string | null;
  citizen_phone?: string | null;
  citizen_aadhaar_last4?: string | null;
  location?: string | null;
  service_id: number;
  service_name?: string | null;
  service_code?: string | null;
  department_name?: string | null;
  assigned_officer_id?: number | null;
  assigned_officer_name?: string | null;
  current_workflow_step?: {
    step_id: string;
    name: string;
    department?: string | null;
    type: string;
    status: string;
  } | null;
  sla_due_at?: string | null;
  created_at: string;
  updated_at: string;
  document_count: number;
  form_data?: Record<string, string>;
  workflow?: Array<{
    key: string;
    label: string;
    status: string;
    detail: string;
    attempts: number;
    step_id?: string;
    department?: string | null;
    type?: string;
    order?: number;
    required?: boolean;
    action?: Record<string, unknown>;
    next_steps?: string[];
    started_at?: string | null;
    completed_at?: string | null;
    error?: string | null;
  }>;
}

export interface GovernmentDashboard {
  department_name: string | null;
  counts: {
    pending_applications: number;
    assigned_to_me: number;
    sla_at_risk: number;
    interdepartmental_requests: number;
    data_verification_requests: number;
    open_exceptions: number;
    completed_today: number;
  };
  application_queue: Array<{
    id: number;
    reference_id: string;
    citizen_name: string;
    service_name: string;
    status: string;
    current_step: { name: string; type: string } | null;
    sla_due_at: string | null;
    assigned_officer_id: number | null;
    assigned_officer_name: string | null;
  }>;
  recent_requests: Array<{
    transaction_id: string;
    application_id: number;
    reference_id: string;
    service_name: string;
    source_department: string;
    requesting_department: string;
    data_requested: string;
    status: string;
    requested_at: string;
  }>;
  generated_at: string;
}

export interface ApplicationWorkspace {
  application: MeshApplication;
  citizen: {
    id: number;
    full_name: string;
    email: string;
    phone: string | null;
    aadhaar_last4: string | null;
  };
  application_information: {
    id: number;
    reference_id: string;
    status: string;
    service_id: number;
    service_name: string | null;
    department_name: string | null;
    submitted_at: string | null;
    form_data: Record<string, unknown>;
    sla_due_at: string | null;
    assigned_officer_id: number | null;
    assigned_officer_name: string | null;
  };
  verified_records: Array<{
    id: string;
    record_type: string;
    status: string;
    department: string | null;
    source_record_id: string;
    verified_at: string | null;
    values: Record<string, string>;
  }>;
  documents: Array<{
    id: number;
    title: string;
    doc_type: string;
    is_verified: boolean;
    verification_score: number | null;
    fraud_risk_level: string | null;
    created_at: string | null;
  }>;
  consents: Array<{
    id: number;
    purpose: string;
    requested_data: string;
    status: string;
    source_department: string | null;
    granted_at: string | null;
    expires_at: string | null;
    revoked_at: string | null;
  }>;
  transactions: Array<{
    transaction_id: string;
    status: string;
    source_department: string;
    requesting_department: string;
    data_requested: string;
    requested_at: string | null;
    completed_at: string | null;
    error_message: string | null;
  }>;
  transaction_events: Array<{
    id: string;
    transaction_id: number;
    event_type: string;
    status: string;
    detail: string | null;
    error_code: string | null;
    error_message: string | null;
    occurred_at: string | null;
  }>;
  workflow: NonNullable<MeshApplication["workflow"]>;
  exceptions: Array<{
    id: number;
    system: string;
    category: string;
    message: string;
    severity: string;
    status: string;
    details: Record<string, unknown> | null;
    created_at: string | null;
  }>;
  audit_events: Array<{
    id: string | number;
    action: string;
    entity_type: string;
    details: string | null;
    actor_id: number | null;
    actor_role?: string | null;
    department_id?: number | null;
    resource_type?: string;
    resource_id?: string;
    transaction_id?: string | null;
    result?: string;
    metadata?: Record<string, unknown>;
    created_at: string | null;
  }>;
}

export interface WorkflowDefinition {
  workflow_id: number;
  service_id: number;
  application_id: number | null;
  name: string;
  version: number;
  status: string;
  steps: Array<{
    step_id: string;
    name: string;
    department: string | null;
    type:
      | "DATA_REQUEST"
      | "CONSENT"
      | "DOCUMENT_UPLOAD"
      | "DOCUMENT_VERIFICATION"
      | "DATA_VALIDATION"
      | "OFFICER_REVIEW"
      | "APPROVAL"
      | "REJECTION"
      | "NOTIFICATION"
      | "COMPLETION";
    order: number;
    required: boolean;
    action: Record<string, unknown>;
    next_steps: string[];
    status: string;
    attempts: number;
    detail: string | null;
  }>;
  required_records: string[];
  required_consents: string[];
  departments: string[];
  transitions: Record<string, string[]>;
  sla_hours: number | null;
  sla_due_at: string | null;
}

export interface MeshDocument {
  id: number;
  title: string;
  doc_type: string;
  owner_id: number;
  application_id: number | null;
  is_verified: boolean;
  created_at: string;
}

export interface MeshConsent {
  id: number;
  application_id?: number;
  applicationId?: string;
  purpose: string;
  status: "pending" | "granted" | "denied" | "active" | "revoked" | "expired";
  source_platform_id: number;
  source_platform_name?: string | null;
  target_platform_id: number;
  target_platform_name?: string | null;
  citizen_id: number;
  citizen_name?: string | null;
  citizen_aadhaar_last4?: string | null;
  requested_data: string;
  data_items: Array<{
    id: number;
    data_key: string;
    description: string;
    classification?: string | null;
  }>;
  created_at: string;
  granted_at?: string | null;
  expires_at?: string | null;
  revoked_at?: string | null;
}

export interface MeshException {
  id: number;
  exceptionId?: number;
  applicationId: string | null;
  system: string;
  sourceSystem?: string;
  category: string;
  type?: string;
  message: string;
  severity: string;
  status: "OPEN" | "RETRYING" | "RESOLVED" | "ESCALATED" | "IGNORED";
  transactionId?: string | null;
  retryCount: number;
  details: Record<string, unknown> | null;
  createdAt: string;
  updatedAt?: string | null;
  resolvedAt?: string | null;
}

export interface MeshNotification {
  id: number;
  recipient_id: number;
  event_type: string;
  title: string;
  message: string;
  notification_type: string;
  created_at: string;
  read_at: string | null;
  read: boolean;
  application_id: number | null;
  application_reference: string | null;
  transaction_id: string | null;
}

export interface MeshDocument {
  id: number;
  title: string;
  doc_type: string;
  file_path: string;
  mime_type: string;
  owner_id: number;
  application_id: number | null;
  is_verified: boolean;
  verification_score: number | null;
  fraud_risk_level: string | null;
  extracted_text: string | null;
  extracted_entities: string | null;
  created_at: string;
}

export interface MeshDocumentVerification {
  id: number;
  document_id: number;
  file_sha256: string;
  extracted_fields: Record<string, string | number>;
  extraction_text: string;
  pipeline_steps: Array<{
    step: string;
    status: string;
    [key: string]: unknown;
  }>;
  verification_status: "PENDING_REVIEW" | "VERIFIED" | "REJECTED";
  confidence: number;
  source_match_status: "MATCHED" | "MISMATCHED" | "NOT_FOUND" | "NOT_CHECKED" | "UNAVAILABLE";
  source_match: Record<string, unknown>;
  duplicate_status: "UNIQUE" | "DUPLICATE";
  tampering_indicators: string[];
  reviewed_by: number | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_at: string;
}

export interface MeshDocumentVerificationResponse {
  document: MeshDocument;
  verification_result: MeshDocumentVerification;
}

export interface ConnectedSystemMetrics {
  id: number;
  system_name: string;
  connectorMode: string | null;
  slug: string;
  name: string;
  department: string | null;
  connectionStatus: "connected" | "disconnected";
  healthStatus: "active" | "degraded" | "offline";
  responseTimeMs: number | null;
  transactionResponseTimeMs: number | null;
  lastSuccessfulRequestAt: string | null;
  lastFailureAt: string | null;
  lastFailureMessage: string | null;
  failureCount: number;
  transactionCount: number;
  failedTransactionCount: number;
  platformStatus: string;
  isActive: boolean;
  integrationType: string;
  apiVersion: string;
  status: "healthy" | "degraded" | "offline";
  response_time: number;
  last_successful_request: string | null;
  last_failure: string | null;
  failure_count: number;
}

export interface SystemHealth {
  system_name: string;
  status: "healthy" | "degraded";
  response_time: number;
  last_successful_request: string | null;
  last_failure: string | null;
  failure_count: number;
  checked_at: string;
  integrations: SystemHealthCheck[];
}

export interface SystemHealthCheck {
  id: number;
  slug: string;
  name: string;
  department: string | null;
  system_name: string;
  connector_mode: string | null;
  connectorMode: string | null;
  status: "healthy" | "degraded" | "offline";
  response_time: number;
  last_successful_request: string | null;
  last_failure: string | null;
  last_failure_message: string | null;
  failure_count: number;
}

export interface InteroperabilityTransaction {
  transactionId: string;
  source: string;
  destination: string;
  sourceDepartment: string;
  requestingDepartment: string;
  dataRequested: string;
  dataType: string;
  transactionType: string;
  status: string;
  transactionStatus: string;
  applicationId: number;
  applicationReference: string | null;
  consentId: number;
  startedAt: string | null;
  completedAt: string | null;
  errorCode: string | null;
  errorMessage: string | null;
  timeline: Array<{
    key: string;
    label: string;
    status: "completed" | "pending";
    occurredAt: string | null;
    detail: string | null;
  }>;
  events: Array<{
    state: string;
    type: string;
    detail: string | null;
    occurredAt: string | null;
  }>;
}

export interface DataMappingConfiguration {
  id: number;
  name: string;
  source: string;
  target: string;
  sourceSystemId: number;
  sourceSystem: string | null;
  targetSystemId: number;
  targetSystem: string | null;
  sourceSchemaVersion: string;
  targetSchemaVersion: string;
  version: number;
  status: string;
  rules: Array<{
    sourceField: string;
    targetField: string;
    transformation: string | null;
    required: boolean;
  }>;
}

export interface InteroperabilityResult {
  status: string;
  transactionStatus: string;
  message: string;
  transactionId: string;
  data?: Record<string, unknown>;
  record?: { source: string; status: string };
  applicationId: number;
  validation?: Record<string, unknown>;
}

export interface MeshAuditLog {
  id: number;
  timestamp: string;
  actor_id: number | null;
  actor_role: string | null;
  actor_name: string | null;
  department_id: number | null;
  action: string;
  resource_type: string;
  resource_id: string;
  transaction_id: string | null;
  result: string;
  metadata: Record<string, unknown>;
  details: string | null;
}

export interface AuditLogFilters {
  date?: string;
  actor?: string;
  department?: string;
  action?: string;
  transaction?: string;
  resource?: string;
  result?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

export function getStoredToken(): string | null {
  return getAccessToken();
}

export function setStoredToken(token: string): void {
  setAccessToken(token);
  markSessionActive();
}

export function clearStoredToken(): void {
  setAccessToken(null);
}

async function request<T>(
  endpoint: string,
  options: RequestInit & { timeoutMs?: number } = {},
): Promise<{ data: T | null; error: string | null; status: number }> {
  try {
    const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
    const response = await authenticatedApiClient.request<T>({
      url: endpoint,
      method: options.method ?? "GET",
      data: options.body,
      headers: {
        ...Object.fromEntries(new Headers(options.headers).entries()),
        ...(options.body && !isFormData ? { "Content-Type": "application/json" } : {}),
      },
      ...(options.timeoutMs ? { timeout: options.timeoutMs } : {}),
      ...(options.signal ? { signal: options.signal } : {}),
    });
    return { data: response.data, error: null, status: response.status };
  } catch (err: unknown) {
    const responseStatus = axios.isAxiosError(err) ? (err.response?.status ?? 0) : 0;
    return {
      data: null,
      error: apiErrorMessage(err),
      status: responseStatus,
    };
  }
}

export const api = {
  // System Health
  async getSystemHealth(): Promise<SystemHealth> {
    const res = await request<SystemHealth>("/system/health");
    if (res.error || !res.data) {
      throw new Error(res.error || "System health could not be loaded.");
    }
    return res.data;
  },

  async getStats(): Promise<DashboardStats | null> {
    const res = await request<DashboardStats>("/stats/dashboard");
    return res.data;
  },

  async getGovernmentDashboard(): Promise<GovernmentDashboard> {
    const res = await request<GovernmentDashboard>("/stats/government-dashboard");
    if (res.error || !res.data) {
      throw new Error(res.error || "Government dashboard data is unavailable.");
    }
    return res.data;
  },

  // Auth
  async login(email: string, password: string): Promise<AuthResponse> {
    clearStoredToken();
    const res = await request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (res.error) throw new Error(res.error);
    if (!res.data?.access_token || !res.data.user)
      throw new Error("Sign in did not return a valid authentication response.");
    setStoredToken(res.data.access_token);
    return res.data;
  },

  async signup(data: {
    full_name: string;
    email: string;
    password: string;
    phone?: string;
    aadhaar_last4?: string;
  }): Promise<AuthResponse> {
    clearStoredToken();
    const { full_name, email, password, phone, aadhaar_last4 } = data;
    const res = await request<AuthResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ full_name, email, password, phone, aadhaar_last4 }),
    });
    if (res.error) throw new Error(res.error);
    if (!res.data?.access_token || !res.data.user)
      throw new Error("Registration did not return a valid authentication response.");
    setStoredToken(res.data.access_token);
    return res.data;
  },

  async getMe(): Promise<UserProfile | null> {
    const res = await request<UserProfile>("/auth/me");
    return res.data;
  },

  async getUsers(): Promise<MeshUser[]> {
    const res = await request<MeshUser[]>("/auth/users");
    if (res.error || !res.data) throw new Error(res.error || "User records could not be loaded.");
    return res.data;
  },

  async createManagedUser(data: ManagedUserCreate): Promise<UserProfile> {
    const res = await request<UserProfile>("/auth/users", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Staff account could not be created.");
    }
    return res.data;
  },

  async requestStaffAccount(data: StaffAccountRequest): Promise<{ message: string }> {
    const res = await request<{ message: string }>("/auth/staff-requests", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Staff account request could not be submitted.");
    }
    return res.data;
  },

  async updateManagedUser(id: number, data: { is_active: boolean }): Promise<UserProfile> {
    const res = await request<UserProfile>(`/auth/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Staff account could not be updated.");
    }
    return res.data;
  },

  async restoreSession(): Promise<UserProfile | null> {
    const refreshed = await refreshAccessToken();
    if (!refreshed) return null;

    const profile = await api.getMe();
    if (!profile) clearStoredToken();
    return profile;
  },

  async logout(): Promise<void> {
    clearStoredToken();
    await request<void>("/auth/logout", { method: "POST" });
  },

  // Applications
  async getApplications(params?: {
    status?: string;
    search?: string;
    citizen_id?: number;
    limit?: number;
    assigned_to_me?: boolean;
  }): Promise<MeshApplication[]> {
    const query = new URLSearchParams();
    if (params?.status) query.append("status", params.status);
    if (params?.search) query.append("search", params.search);
    if (params?.citizen_id) query.append("citizen_id", String(params.citizen_id));
    if (params?.limit) query.append("limit", String(params.limit));
    if (params?.assigned_to_me) query.append("assigned_to_me", "true");

    const res = await request<MeshApplication[]>(`/applications?${query.toString()}`);
    if (res.error || !res.data) {
      throw new Error(res.error || "Applications could not be loaded.");
    }
    return res.data;
  },

  async getApplicationWorkspace(id: number | string): Promise<ApplicationWorkspace> {
    if (!/^\d+$/.test(String(id))) {
      throw new Error("An application database ID is required to load its workspace.");
    }
    const res = await request<ApplicationWorkspace>(`/applications/${id}/workspace`);
    if (res.error || !res.data) {
      throw new Error(res.error || "Application workspace could not be loaded.");
    }
    return res.data;
  },

  async assignApplicationToMe(id: number): Promise<MeshApplication> {
    const res = await request<MeshApplication>(`/applications/${id}/assign-to-me`, {
      method: "POST",
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Application could not be assigned.");
    }
    return res.data;
  },

  async getApplication(id: number | string): Promise<MeshApplication | null> {
    const endpoint =
      typeof id === "string" && !/^\d+$/.test(id)
        ? `/applications/track/${encodeURIComponent(id)}`
        : `/applications/${id}`;
    const res = await request<MeshApplication>(endpoint);
    return res.data;
  },

  async trackApplication(refId: string): Promise<MeshApplication | null> {
    const res = await request<MeshApplication>(`/applications/track/${encodeURIComponent(refId)}`);
    return res.data;
  },

  async createApplication(data: {
    reference_id?: string;
    citizen_id?: number;
    service_id: number;
    remarks?: string;
    form_data?: Record<string, unknown>;
    verified_records?: Record<string, string>;
    consent: boolean;
    location?: string;
  }): Promise<MeshApplication> {
    const res = await request<MeshApplication>("/applications", {
      method: "POST",
      body: JSON.stringify({
        ...(data.reference_id ? { reference_id: data.reference_id } : {}),
        citizen_id: data.citizen_id,
        service_id: data.service_id,
        remarks: data.remarks,
        form_data: data.form_data,
        verified_records: data.verified_records,
        consent: data.consent,
        location: data.location,
      }),
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Application could not be created.");
    }
    return res.data;
  },

  async getApplicationWorkflow(id: number | string): Promise<MeshApplication["workflow"]> {
    const res = await request<MeshApplication["workflow"]>(`/applications/${id}/workflow`);
    if (res.error || !res.data) {
      throw new Error(res.error || "Application workflow could not be loaded.");
    }
    return res.data;
  },

  async getWorkflowDefinitions(serviceId?: number): Promise<WorkflowDefinition[]> {
    const query = serviceId === undefined ? "" : `?service_id=${serviceId}`;
    const res = await request<WorkflowDefinition[]>(`/workflows${query}`);
    if (res.error || !res.data) {
      throw new Error(res.error || "Workflow definitions could not be loaded.");
    }
    return res.data;
  },

  async getDocuments(ownerId: number): Promise<MeshDocument[]> {
    const res = await request<MeshDocument[]>(`/documents?owner_id=${ownerId}`);
    if (res.error || !res.data) {
      throw new Error(res.error || "Documents could not be loaded.");
    }
    return res.data;
  },

  async getDocument(documentId: number): Promise<MeshDocument | null> {
    const res = await request<MeshDocument>(`/documents/${documentId}`);
    return res.data;
  },

  async updateWorkflowStage(
    id: number,
    stageKey: string,
    status: string,
    detail?: string,
    error?: string,
    nextStep?: string,
  ): Promise<MeshApplication["workflow"]> {
    const res = await request<MeshApplication["workflow"]>(`/applications/${id}/workflow`, {
      method: "PATCH",
      body: JSON.stringify({
        stage_key: stageKey,
        status,
        detail,
        completed_at: status === "completed" ? new Date().toISOString() : undefined,
        error,
        next_step: nextStep,
      }),
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Workflow stage could not be updated.");
    }
    return res.data;
  },

  async updateApplicationStatus(
    id: number,
    status: string,
    remarks?: string,
  ): Promise<MeshApplication> {
    const res = await request<MeshApplication>(`/applications/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, remarks }),
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Application status could not be updated.");
    }
    return res.data;
  },

  // Mesh Platforms
  async getPlatforms(): Promise<MeshNodePlatform[]> {
    const res = await request<MeshNodePlatform[]>("/platforms");
    if (res.error || !res.data) {
      throw new Error(res.error || "Connected systems could not be loaded.");
    }
    return res.data;
  },

  async getDepartments(): Promise<MeshDepartment[]> {
    const res = await request<MeshDepartment[]>("/departments");
    if (res.error || !res.data) {
      throw new Error(res.error || "Departments could not be loaded.");
    }
    return res.data;
  },

  async pingPlatform(id: number): Promise<{ latency_ms: number; status: string; message: string }> {
    const res = await request<{ latency_ms: number; status: string; message: string }>(
      `/platforms/${id}/ping`,
      { method: "POST" },
    );
    if (res.error || !res.data) {
      throw new Error(res.error || "System health could not be checked.");
    }
    return res.data;
  },

  // Services
  async getServices(): Promise<MeshService[]> {
    const res = await request<MeshService[]>("/services");
    if (res.error || !res.data) {
      throw new Error(res.error || "Services could not be loaded.");
    }
    return res.data;
  },

  async getServiceFormSchema(id: number | string): Promise<ServiceFormSchema> {
    const res = await request<ServiceFormSchema>(`/services/${id}/form-schema`);
    if (res.error || !res.data) {
      throw new Error(res.error || "Service application details could not be loaded.");
    }
    return res.data;
  },

  async getServiceApplicationSources(id: number | string): Promise<ServiceApplicationSource[]> {
    const res = await request<ServiceApplicationSource[]>(`/services/${id}/application-sources`);
    if (res.error || !res.data) {
      throw new Error(res.error || "Application data sources could not be loaded.");
    }
    return res.data;
  },

  async getConnectedSystems(): Promise<ConnectedSystemMetrics[]> {
    const res = await request<ConnectedSystemMetrics[]>("/integrations");
    if (res.error || !res.data) {
      throw new Error(res.error || "Connected systems could not be loaded.");
    }
    return res.data;
  },

  async getIntegrationHealth(id: number | string): Promise<ConnectedSystemMetrics> {
    const res = await request<ConnectedSystemMetrics>(
      `/integrations/${encodeURIComponent(String(id))}/health`,
    );
    if (res.error || !res.data) {
      throw new Error(res.error || "Connected system health could not be loaded.");
    }
    return res.data;
  },

  async getInteroperabilityTransactions(): Promise<InteroperabilityTransaction[]> {
    const res = await request<InteroperabilityTransaction[]>("/interoperability/transactions");
    if (res.error || !res.data) {
      throw new Error(res.error || "Interoperability transactions could not be loaded.");
    }
    return res.data;
  },

  async getInteroperabilityTransaction(id: string): Promise<InteroperabilityTransaction> {
    const res = await request<InteroperabilityTransaction>(
      `/interoperability/transactions/${encodeURIComponent(id)}`,
    );
    if (res.error || !res.data) {
      throw new Error(res.error || "Transaction details could not be loaded.");
    }
    return res.data;
  },

  async getExceptions(): Promise<MeshException[]> {
    const res = await request<MeshException[]>("/exceptions?limit=100");
    if (res.error || !res.data) {
      throw new Error(res.error || "Exceptions could not be loaded.");
    }
    return res.data;
  },

  async getNotifications(): Promise<MeshNotification[]> {
    const res = await request<MeshNotification[]>("/notifications");
    if (res.error || !res.data) {
      throw new Error(res.error || "Notifications could not be loaded.");
    }
    return res.data;
  },

  async markNotificationRead(id: number): Promise<MeshNotification> {
    const res = await request<MeshNotification>(`/notifications/${id}/read`, {
      method: "PATCH",
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Notification could not be marked as read.");
    }
    return res.data;
  },

  async updateException(
    id: number,
    payload: { status: MeshException["status"] },
  ): Promise<MeshException> {
    const res = await request<MeshException>(`/exceptions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Exception could not be updated.");
    }
    return res.data;
  },

  async retryException(id: number): Promise<{
    status: "success" | "failure";
    transactionStatus: string;
    transactionId: string;
    message: string;
    exception: MeshException;
  }> {
    const res = await request<{
      status: "success" | "failure";
      transactionStatus: string;
      transactionId: string;
      message: string;
      exception: MeshException;
    }>(`/exceptions/${id}/retry`, { method: "POST" });
    if (res.error || !res.data) {
      throw new Error(res.error || "Exception retry could not be completed.");
    }
    return res.data;
  },

  async getDataMappings(): Promise<DataMappingConfiguration[]> {
    const res = await request<DataMappingConfiguration[]>("/data-mappings");
    if (res.error || !res.data) {
      throw new Error(res.error || "Data mappings could not be loaded.");
    }
    return res.data;
  },

  // Consents
  async getConsents(citizen_id?: number): Promise<MeshConsent[]> {
    const q = citizen_id ? `?citizen_id=${citizen_id}` : "";
    const res = await request<MeshConsent[]>(`/consents${q}`);
    if (res.error || !res.data) {
      throw new Error(res.error || "Consent requests could not be loaded.");
    }
    return res.data;
  },

  async createConsent(data: {
    purpose: string;
    source_platform_id: number;
    target_platform_id: number;
    citizen_id: number;
    application_id?: number;
    requested_data: string;
    requested_fields: string[];
  }): Promise<MeshConsent> {
    const res = await request<MeshConsent>("/consents", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Consent request could not be created.");
    }
    return res.data;
  },

  async approveConsent(id: number): Promise<MeshConsent> {
    const res = await request<MeshConsent>(`/consents/${id}/approve`, {
      method: "POST",
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Consent approval could not be saved.");
    }
    return res.data;
  },

  async rejectConsent(id: number): Promise<MeshConsent> {
    const res = await request<MeshConsent>(`/consents/${id}/reject`, {
      method: "POST",
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Consent rejection could not be saved.");
    }
    return res.data;
  },

  async requestInteroperability(data: {
    citizen_id: number;
    service_id: number;
    application_id: number;
    requesting_department: string;
    source_department: string;
    data_requested: string;
    purpose: string;
    consent_id: number;
  }): Promise<InteroperabilityResult> {
    const res = await request<InteroperabilityResult>("/interoperability/request", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Interoperability request could not be completed.");
    }
    return res.data;
  },

  async revokeConsent(id: number): Promise<MeshConsent> {
    const res = await request<MeshConsent>(`/consents/${id}/revoke`, {
      method: "POST",
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Consent revocation could not be saved.");
    }
    return res.data;
  },

  // Audit Logs
  async getAuditLogs(filters: AuditLogFilters = {}): Promise<MeshAuditLog[]> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== "") query.set(key, String(value));
    }
    const res = await request<MeshAuditLog[]>(`/audit-logs?${query.toString()}`);
    if (res.error || !res.data) {
      throw new Error(res.error || "Audit logs could not be loaded.");
    }
    return res.data;
  },

  // AI & Machine Learning Pipeline
  async uploadAndVerifyDocument(
    file: File,
    applicationId: number,
    documentType?: string,
  ): Promise<MeshDocumentVerificationResponse> {
    const form = new FormData();
    form.set("file", file);
    form.set("application_id", String(applicationId));
    if (documentType) form.set("doc_type", documentType);
    const res = await request<MeshDocumentVerificationResponse>("/documents/upload-and-verify", {
      method: "POST",
      body: form,
      timeoutMs: 180_000,
    });
    if (res.error || !res.data) {
      throw new Error(res.error || "Document verification could not be started.");
    }
    return res.data;
  },

  async getDocumentVerifications(params?: {
    applicationId?: number;
    verificationStatus?: string;
    limit?: number;
  }): Promise<MeshDocumentVerificationResponse[]> {
    const query = new URLSearchParams();
    if (params?.applicationId) query.set("application_id", String(params.applicationId));
    if (params?.verificationStatus) query.set("verification_status", params.verificationStatus);
    if (params?.limit) query.set("limit", String(params.limit));
    const res = await request<MeshDocumentVerificationResponse[]>(
      `/documents/verifications?${query.toString()}`,
    );
    if (res.error || !res.data) {
      throw new Error(res.error || "Document verification results could not be loaded.");
    }
    return res.data;
  },

  async reviewDocumentVerification(
    verificationId: number,
    payload: { decision: "VERIFIED" | "REJECTED"; note: string },
  ): Promise<MeshDocumentVerificationResponse> {
    const res = await request<MeshDocumentVerificationResponse>(
      `/documents/verifications/${verificationId}/review`,
      { method: "POST", body: JSON.stringify(payload) },
    );
    if (res.error || !res.data) {
      throw new Error(res.error || "Document review could not be saved.");
    }
    return res.data;
  },

  async downloadDocument(documentId: number): Promise<Blob> {
    try {
      const response = await authenticatedApiClient.get<Blob>(`/documents/${documentId}/file`, {
        responseType: "blob",
      });
      return response.data;
    } catch (error) {
      throw new Error(apiErrorMessage(error));
    }
  },
};
