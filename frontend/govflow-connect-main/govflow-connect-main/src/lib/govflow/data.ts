export type Health = "Healthy" | "Degraded" | "Down" | "Unknown";
export type Role =
  "Admin" | "Department Officer" | "Developer" | "Operator" | "Auditor" | "Citizen";
export type Service = {
  id: string;
  name: string;
  code: string;
  category?: string;
  department: string;
  sla?: string;
  fee?: string;
  workflowId?: string;
  summary: string;
  documents?: string[];
  eligibility?: string[];
  active: boolean;
};
export type Department = {
  id: string;
  name: string;
  head?: string;
  services: string[];
  systems?: string[];
  health?: Health;
  responseMs?: number;
  uptime?: number;
};
export type Integration = {
  id: string;
  name: string;
  protocol: string;
  owner: string;
  health: Health;
  successRate?: number;
  latencyMs?: number;
  uptime?: number;
  failures24h?: number;
  auth?: string;
  endpoints?: Array<{ method: string; path: string; desc: string }>;
  schema?: string[];
};
export type StageDef = {
  id: string;
  name: string;
  department?: string;
  system?: string;
  dataExchanged?: string;
  api?: string;
  ms?: number;
};
export type Workflow = {
  id: string;
  name: string;
  serviceId: string;
  version: string;
  status: string;
  runs?: number;
  successRate?: number;
  avgMinutes?: number;
  stages: StageDef[];
};
export type Application = {
  id: string;
  backendId?: number;
  citizen: string;
  citizenId: string;
  serviceId: string;
  status: "In Progress" | "Completed" | "Pending" | "Failed";
  stageId: string;
  submitted: string;
  consentIds: string[];
  exceptionIds: string[];
};
export type Consent = {
  id: string;
  applicationId: string;
  requestedBy: string;
  dataRequested: string;
  purpose: string;
  recipient: string;
  status: "Active" | "Pending" | "Expired" | "Revoked";
  grantedOn?: string;
  expiry?: string;
};
export type ExceptionItem = {
  id: string;
  applicationId: string;
  stage: string;
  system: string;
  code: string;
  message: string;
  severity: "Critical" | "High" | "Medium";
  detectedAt: string;
  attempts: number;
  status: "Open" | "Retrying" | "Recovered" | "Escalated" | "Ignored";
  recovery: string;
};
export type PlatformUser = {
  id: string;
  name: string;
  email: string;
  role: Role;
  department: string;
  status: "Active" | "Suspended";
  pendingApproval?: boolean;
  lastActive: string;
};
export type FieldMap = {
  id: string;
  source: string;
  target: string;
  transform: string;
  required: boolean;
  status: string;
};
export type Notification = {
  id: string;
  title: string;
  body: string;
  kind: string;
  time: string;
  read: boolean;
  eventType?: string;
  applicationId?: number | null;
  applicationReference?: string | null;
  transactionId?: string | null;
};
