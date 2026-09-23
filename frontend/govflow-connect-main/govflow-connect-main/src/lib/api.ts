/**
 * GovFlow Inter-Governmental Mesh API Client
 * Connects frontend directly to the FastAPI AI/ML Backend (port 8000).
 */

export const API_BASE_URL =
  (typeof window !== "undefined" && (window as any).__VITE_API_URL__) ||
  import.meta.env["VITE_API_URL"] ||
  "http://127.0.0.1:8000/api/v1";


export const BACKEND_ROOT_URL = API_BASE_URL.replace(/\/api\/v1\/?$/, "");

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
  created_at: string;
  updated_at: string;
  document_count: number;
  form_data?: Record<string, string>;
  workflow?: Array<{ key: string; label: string; status: string; detail: string; attempts: number }>;
}

export interface MeshConsent {
  id: number;
  application_id?: number;
  applicationId?: string;
  purpose: string;
  status: "granted" | "revoked" | "expired";
  source_platform_id: number;
  source_platform_name?: string | null;
  target_platform_id: number;
  target_platform_name?: string | null;
  citizen_id: number;
  citizen_name?: string | null;
  citizen_aadhaar_last4?: string | null;
  created_at: string;
  expires_at?: string | null;
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


// Token helper
const TOKEN_KEY = "govflow_jwt_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function clearStoredToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ data: T | null; error: string | null; status: number }> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith("http")
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    const isJson = res.headers.get("content-type")?.includes("application/json");
    const body = isJson ? await res.json() : null;

    if (!res.ok) {
      const errorMsg =
        body?.detail ||
        (Array.isArray(body?.detail) ? body.detail[0]?.msg : null) ||
        `HTTP Error ${res.status}`;
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

  // Auth
  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (res.error) throw new Error(res.error);
    if (res.data?.access_token) {
      setStoredToken(res.data.access_token);
    }
    return res.data!;
  },

  async signup(data: {
    full_name: string;
    email: string;
    password: string;
    phone?: string;
    aadhaar_last4?: string;
    department?: string;
    role?: "citizen" | "officer" | "admin" | "developer" | "operator" | "auditor";
  }): Promise<AuthResponse> {
    const res = await request<AuthResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (res.error) throw new Error(res.error);
    if (res.data?.access_token) {
      setStoredToken(res.data.access_token);
    }
    return res.data!;
  },

  async getMe(): Promise<UserProfile | null> {
    const res = await request<UserProfile>("/auth/me");
    return res.data;
  },

  logout(): void {
    clearStoredToken();
  },

  // Applications
  async getApplications(params?: {
    status?: string;
    search?: string;
    citizen_id?: number;
    limit?: number;
  }): Promise<MeshApplication[]> {
    const query = new URLSearchParams();
    if (params?.status) query.append("status", params.status);
    if (params?.search) query.append("search", params.search);
    if (params?.citizen_id) query.append("citizen_id", String(params.citizen_id));
    if (params?.limit) query.append("limit", String(params.limit));

    const res = await request<MeshApplication[]>(`/applications?${query.toString()}`);
    return res.data || [];
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
    form_data?: Record<string, string>;
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

  async updateWorkflowStage(
    id: number,
    stageKey: string,
    status: string,
    detail?: string,
    error?: string
  ): Promise<MeshApplication["workflow"]> {
    const res = await request<MeshApplication["workflow"]>(`/applications/${id}/workflow`, {
      method: "PATCH",
      body: JSON.stringify({
        stage_key: stageKey,
        status,
        detail,
        completed_at: status === "completed" ? new Date().toISOString() : undefined,
        error,
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
    expires_at?: string;
  }): Promise<MeshConsent> {
    const res = await request<MeshConsent>("/consents", {
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
