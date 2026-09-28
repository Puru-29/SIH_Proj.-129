/**
 * GovFlow Inter-Governmental Mesh API Client
 * Connects frontend directly to the FastAPI AI/ML Backend (port 8000).
 */

export const API_BASE_URL =
  (typeof window !== "undefined" && (window as any).__VITE_API_BASE_URL__) ||
  import.meta.env["VITE_API_BASE_URL"] ||
  import.meta.env["VITE_API_URL"] ||
  "http://127.0.0.1:8000/api/v1";


export const BACKEND_ROOT_URL = API_BASE_URL.replace(/\/api\/v1\/?$/, "");

if (typeof window !== "undefined") {
  try {
    window.localStorage.removeItem("govflow_jwt_token");
  } catch {
    // Storage may be unavailable; tokens are never read from or written to it.
  }
}

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
  role: "citizen" | "officer" | "admin" | "developer" | "operator" | "auditor";
  is_active: boolean;
  created_at: string;
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
      created_at: string | null;
    }>;
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
  action: string;
  entity_type: string;
  entity_id: string;
  details?: string | null;
  actor_id?: number | null;
  actor_name?: string | null;
  created_at: string;
}

export interface EngineStatusItem {
  name: string;
  type: string;
  ready: boolean;
  device: string;
  version: string;
  mode: string;
}

export interface MLSystemStatus {
  status: string;
  system_healthy?: boolean;
  total_engines: number;
  ready_count: number;
  ready_engines?: number;
  timestamp?: number;
  engines: Record<string, EngineStatusItem>;
}


let accessToken: string | null = null;
let refreshPromise: Promise<AuthResponse | null> | null = null;

export function getStoredToken(): string | null {
  return accessToken;
}

export function setStoredToken(token: string): void {
  accessToken = token;
}

export function clearStoredToken(): void {
  accessToken = null;
}

async function refreshAccessToken(): Promise<AuthResponse | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        clearStoredToken();
        return null;
      }

      const result = (await response.json()) as AuthResponse;
      if (!result.access_token) {
        clearStoredToken();
        return null;
      }
      setStoredToken(result.access_token);
      return result;
    } catch {
      clearStoredToken();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ data: T | null; error: string | null; status: number }> {
  const url = endpoint.startsWith("http")
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  try {
    const send = () => {
      const headers = new Headers(options.headers);
      if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
      const token = getStoredToken();
      if (token) headers.set("Authorization", `Bearer ${token}`);
      else headers.delete("Authorization");
      return fetch(url, { ...options, headers, credentials: "include" });
    };

    let res = await send();
    const isCredentialEndpoint = /^\/auth\/(login|signup|refresh|logout)(?:\?|$)/.test(endpoint);
    if (res.status === 401 && !isCredentialEndpoint) {
      const refreshed = await refreshAccessToken();
      if (refreshed) res = await send();
    }

    const isJson = res.headers.get("content-type")?.includes("application/json");
    const body = isJson ? await res.json() : null;

    if (!res.ok) {
      const errorMsg = Array.isArray(body?.detail)
        ? body.detail[0]?.msg || `HTTP Error ${res.status}`
        : body?.detail || `HTTP Error ${res.status}`;
      return { data: null, error: errorMsg, status: res.status };
    }

    return { data: body as T, error: null, status: res.status };
  } catch (err: any) {
    return {
      data: null,
      error: err.message || "Network request failed. Is the backend running on port 8000?",
      status: 0,
    };
  }
}

export const api = {
  // System Health
  async getHealth(): Promise<{ status: string; app: string } | null> {
    try {
      const res = await fetch(`${BACKEND_ROOT_URL}/health`, {
        signal: AbortSignal.timeout(3500),
        credentials: "include",
      });
      if (res.ok) return await res.json();
    } catch {
      // ignore
    }
    return null;
  },

  async getMLStatus(): Promise<MLSystemStatus | null> {
    const res = await request<MLSystemStatus>("/ml/status");
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
    if (!res.data?.access_token) throw new Error("Sign in did not return an access token.");
    setStoredToken(res.data.access_token);
    const profile = await api.getMe();
    if (!profile) {
      clearStoredToken();
      throw new Error("Unable to load your account profile.");
    }
    return { ...res.data!, user: profile };
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
    if (!res.data?.access_token) throw new Error("Registration did not return an access token.");
    setStoredToken(res.data.access_token);
    const profile = await api.getMe();
    if (!profile) {
      clearStoredToken();
      throw new Error("Unable to load your account profile.");
    }
    return { ...res.data!, user: profile };
  },

  async getMe(): Promise<UserProfile | null> {
    const res = await request<UserProfile>("/auth/me");
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
    const endpoint = typeof id === "string" && !/^\d+$/.test(id)
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
        reference_id: data.reference_id || `APP-2026-${Math.floor(10000 + Math.random() * 90000)}`,
        citizen_id: data.citizen_id,
        service_id: data.service_id,
        remarks: data.remarks,
        form_data: data.form_data,
        verified_records: data.verified_records,
        consent: data.consent,
        location: data.location,
      }),
    });
    if (res.error) throw new Error(res.error);
    return res.data!;
  },

  async getApplicationWorkflow(id: number | string): Promise<MeshApplication["workflow"]> {
    const res = await request<MeshApplication["workflow"]>(`/applications/${id}/workflow`);
    if (res.error) throw new Error(res.error);
    return res.data || [];
  },

  async getWorkflowDefinitions(serviceId?: number): Promise<WorkflowDefinition[]> {
    const query = serviceId === undefined ? "" : `?service_id=${serviceId}`;
    const res = await request<WorkflowDefinition[]>(`/workflows${query}`);
    if (res.error) throw new Error(res.error);
    return res.data || [];
  },

  async getDocuments(ownerId: number): Promise<MeshDocument[]> {
    const res = await request<MeshDocument[]>(`/documents?owner_id=${ownerId}`);
    if (res.error) throw new Error(res.error);
    return res.data || [];
  },

  async updateWorkflowStage(
    id: number,
    stageKey: string,
    status: string,
    detail?: string,
    error?: string,
    nextStep?: string
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
    if (res.error) throw new Error(res.error);
    return res.data || [];
  },

  async updateApplicationStatus(
    id: number,
    status: string,
    remarks?: string
  ): Promise<MeshApplication> {
    const res = await request<MeshApplication>(`/applications/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, remarks }),
    });
    if (res.error) throw new Error(res.error);
    return res.data!;
  },

  // Mesh Platforms
  async getPlatforms(): Promise<MeshNodePlatform[]> {
    const res = await request<MeshNodePlatform[]>("/platforms");
    if (res.error) throw new Error(res.error);
    return res.data || [];
  },

  async getDepartments(): Promise<MeshDepartment[]> {
    const res = await request<MeshDepartment[]>("/departments");
    if (res.error) throw new Error(res.error);
    return res.data || [];
  },

  async pingPlatform(
    id: number
  ): Promise<{ latency_ms: number; status: string; message: string }> {
    const res = await request<any>(`/platforms/${id}/ping`, { method: "POST" });
    if (res.error) throw new Error(res.error);
    return res.data;
  },

  // Services
  async getServices(): Promise<MeshService[]> {
    const res = await request<MeshService[]>("/services");
    if (res.error) throw new Error(res.error);
    return res.data || [];
  },

  async getServiceFormSchema(id: number | string): Promise<ServiceFormSchema> {
    const res = await request<ServiceFormSchema>(`/services/${id}/form-schema`);
    if (res.error) throw new Error(res.error);
    return res.data!;
  },

  async getWorkflows(): Promise<any[]> {
    const res = await request<any[]>("/workflows");
    return res.data || [];
  },

  async getIntegrations(): Promise<any[]> {
    const res = await request<any[]>("/integrations");
    return res.data || [];
  },

  async getExceptions(): Promise<any[]> {
    const res = await request<any[]>("/exceptions");
    return res.data || [];
  },

  async getDataMappings(): Promise<any[]> {
    const res = await request<any[]>("/data-mapping");
    return res.data || [];
  },

  // Consents
  async getConsents(citizen_id?: number): Promise<MeshConsent[]> {
    const q = citizen_id ? `?citizen_id=${citizen_id}` : "";
    const res = await request<MeshConsent[]>(`/consents${q}`);
    return res.data || [];
  },

  async createConsent(data: {
    purpose: string;
    source_platform_id: number;
    target_platform_id: number;
    citizen_id: number;
    requested_data: string;
    requested_fields: string[];
  }): Promise<MeshConsent> {
    const res = await request<MeshConsent>("/consents", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (res.error) throw new Error(res.error);
    return res.data!;
  },

  async approveConsent(id: number): Promise<MeshConsent> {
    const res = await request<MeshConsent>(`/consents/${id}/approve`, {
      method: "POST",
    });
    if (res.error) throw new Error(res.error);
    return res.data!;
  },

  async rejectConsent(id: number): Promise<MeshConsent> {
    const res = await request<MeshConsent>(`/consents/${id}/reject`, {
      method: "POST",
    });
    if (res.error) throw new Error(res.error);
    return res.data!;
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
    if (res.error) throw new Error(res.error);
    return res.data!;
  },

  async revokeConsent(id: number): Promise<MeshConsent> {
    const res = await request<MeshConsent>(`/consents/${id}/revoke`, {
      method: "POST",
    });
    if (res.error) throw new Error(res.error);
    return res.data!;
  },

  // Audit Logs
  async getAuditLogs(limit = 50, entityId?: string): Promise<MeshAuditLog[]> {
    const query = new URLSearchParams({ limit: String(limit) });
    if (entityId) query.set("entity_id", entityId);
    const res = await request<MeshAuditLog[]>(`/audit-logs?${query.toString()}`);
    return res.data || [];
  },

  // AI & Machine Learning Pipeline
  async verifyDocument(payload: {
    title: string;
    doc_type: string;
    owner_id: number;
    application_id?: number;
    image_base64?: string;
    document_text?: string;
    citizen_full_name?: string;
    citizen_aadhaar_last4?: string;
    claimed_income?: number;
    mesh_income?: number;
    claimed_land_acres?: number;
    mesh_land_acres?: number;
    applicant_remarks?: string;
  }): Promise<any> {
    const res = await request<any>("/documents/upload-and-verify", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (res.error) throw new Error(res.error);
    return res.data;
  },

  async runOCR(rawTextHint?: string, imageBase64?: string): Promise<any> {
    const res = await request<any>("/ml/ocr", {
      method: "POST",
      body: JSON.stringify({
        raw_text_hint: rawTextHint,
        image_base64: imageBase64,
      }),
    });
    if (res.error) throw new Error(res.error);
    return res.data;
  },

  async detectAnomaly(payload: {
    annual_income_claimed: number;
    annual_income_tax_mesh: number;
    land_holding_acres_claimed: number;
    land_holding_acres_registry: number;
    ocr_confidence?: number;
    name_match_score?: number;
    past_rejections_count?: number;
  }): Promise<any> {
    const res = await request<any>("/ml/detect-anomaly", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (res.error) throw new Error(res.error);
    return res.data;
  },
};
