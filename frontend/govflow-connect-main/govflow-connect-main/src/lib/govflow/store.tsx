import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, type DashboardStats, type MeshApplication, type MeshConsent } from "@/lib/api";
import { apiErrorMessage } from "@/lib/http";
import { connectorService } from "@/services/connectorService";
import { governmentDataService } from "@/services/governmentDataService";
import { workflowService } from "@/services/workflowService";
import {
  type Application,
  type Consent,
  type Department,
  type ExceptionItem,
  type FieldMap,
  type Integration,
  type Notification,
  type PlatformUser,
  type Role,
  type Service,
  type Workflow,
} from "./data";

export type SessionUser = {
  id?: number;
  name: string;
  email: string;
  mobile: string;
  role: Role;
  backendRole?: string;
  department: string;
  avatarInitial: string;
};

type Store = {
  user: SessionUser | null;
  signIn: (user: SessionUser) => void;
  signOut: () => Promise<void>;
  notifications: Notification[];
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  exceptions: ExceptionItem[];
  updateException: (id: string, patch: Partial<ExceptionItem>) => Promise<void>;
  consents: Consent[];
  updateConsent: (id: string, status: Consent["status"]) => Promise<void>;
  applications: Application[];
  updateApplication: (id: string, patch: Partial<Application>) => Promise<void>;
  workflows: Workflow[];
  createWorkflow: (workflow: Workflow) => void;
  updateWorkflow: (id: string, patch: Partial<Workflow>) => Promise<void>;
  integrations: Integration[];
  updateIntegration: (id: string, patch: Partial<Integration>) => Promise<void>;
  mappings: Record<string, FieldMap[]>;
  saveMapping: (integrationId: string, mapping: FieldMap[]) => Promise<void>;
  services: Service[];
  departments: Department[];
  users: PlatformUser[];
  lastUpdated: Date | null;
  ready: boolean;
  isLive: boolean;
  liveStats: DashboardStats | null;
  loadError: string;
  refreshLiveData: () => Promise<void>;
};

const Ctx = createContext<Store | null>(null);

export function displayBackendRole(role: string): Role {
  if (role === "citizen") return "Citizen";
  if (role === "admin" || role === "system_admin") return "Admin";
  if (role === "officer" || role === "department_officer") return "Department Officer";
  if (role === "developer" || role === "interoperability_admin") return "Developer";
  if (role === "auditor") return "Auditor";
  return "Operator";
}

const displayStatus = (status: string) => status.replaceAll("_", " ").toLowerCase();

function mapApplication(
  app: MeshApplication,
  consents: MeshConsent[],
  exceptions: Awaited<ReturnType<typeof api.getExceptions>>,
): Application {
  const step = app.current_workflow_step;
  const status: Application["status"] =
    app.status === "approved"
      ? "Completed"
      : app.status === "rejected"
        ? "Failed"
        : app.status === "submitted"
          ? "Pending"
          : "In Progress";
  return {
    id: app.reference_id,
    backendId: app.id,
    citizen: app.citizen_name ?? "",
    citizenId: String(app.citizen_id),
    serviceId: String(app.service_id),
    status,
    stageId: step?.step_id ?? "",
    submitted: app.created_at,
    consentIds: consents
      .filter((consent) => consent.application_id === app.id)
      .map((consent) => String(consent.id)),
    exceptionIds: exceptions
      .filter((exception) => exception.applicationId === String(app.id))
      .map((exception) => String(exception.id)),
  };
}

function mapIntegration(
  item: Awaited<ReturnType<typeof api.getConnectedSystems>>[number],
): Integration {
  const latency = item.responseTimeMs;
  return {
    id: String(item.id),
    name: item.name,
    protocol: item.integrationType,
    owner: item.department ?? "",
    health:
      item.status === "healthy"
        ? "Healthy"
        : item.status === "degraded"
          ? "Degraded"
          : item.status === "offline"
            ? "Down"
            : "Unknown",
    ...(latency !== null && latency !== undefined ? { latencyMs: latency } : {}),
    failures24h: item.failureCount,
  };
}

function mapConsent(consent: MeshConsent): Consent {
  const status: Consent["status"] =
    consent.status === "granted" || consent.status === "active"
      ? "Active"
      : consent.status === "revoked"
        ? "Revoked"
        : consent.status === "expired"
          ? "Expired"
          : "Pending";
  return {
    id: String(consent.id),
    applicationId: consent.application_id ? String(consent.application_id) : "",
    requestedBy: consent.source_platform_name ?? "",
    dataRequested: consent.requested_data,
    purpose: consent.purpose,
    recipient: consent.target_platform_name ?? "",
    status,
    ...(consent.granted_at ? { grantedOn: consent.granted_at } : {}),
    ...(consent.expires_at ? { expiry: consent.expires_at } : {}),
  };
}

export function GovFlowProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const [liveStats, setLiveStats] = useState<DashboardStats | null>(null);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [exceptions, setExceptions] = useState<ExceptionItem[]>([]);
  const [consents, setConsents] = useState<Consent[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [mappings, setMappings] = useState<Record<string, FieldMap[]>>({});
  const [services, setServices] = useState<Service[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [loadError, setLoadError] = useState("");

  const refreshLiveData = useCallback(async () => {
    const results = await Promise.allSettled([
      api.getStats(),
      api.getApplications(),
      api.getConsents(),
      api.getNotifications(),
      governmentDataService.getExceptions(),
      workflowService.getWorkflowDefinitions(),
      connectorService.getConnectors(),
      governmentDataService.getMappings(),
      api.getServices(),
      governmentDataService.getDepartments(),
      api.getUsers(),
    ]);
    const rejected = results.filter((result) => result.status === "rejected");
    setLoadError(
      rejected.length ? apiErrorMessage((rejected[0] as PromiseRejectedResult).reason) : "",
    );

    const [
      stats,
      rawApplications,
      rawConsents,
      rawNotifications,
      rawExceptions,
      rawWorkflows,
      rawIntegrations,
      rawMappings,
      rawServices,
      rawDepartments,
      rawUsers,
    ] = results;
    const resolved = <T,>(result: PromiseSettledResult<T>): T | undefined =>
      result.status === "fulfilled" ? result.value : undefined;
    const consentData = resolved(rawConsents) ?? [];
    const applicationData = resolved(rawApplications) ?? [];

    if (stats.status === "fulfilled") setLiveStats(stats.value);
    if (rawConsents.status === "fulfilled") {
      const mapped = consentData.map(mapConsent);
      setConsents(mapped);
    }
    if (rawApplications.status === "fulfilled") {
      setApplications(
        applicationData.map((app) =>
          mapApplication(app, consentData, resolved(rawExceptions) ?? []),
        ),
      );
    }
    if (rawNotifications.status === "fulfilled") {
      setNotifications(
        rawNotifications.value.map((item) => ({
          id: String(item.id),
          title: item.title,
          body: item.message,
          kind: item.event_type,
          time: item.created_at,
          read: item.read,
          eventType: item.event_type,
          applicationId: item.application_id,
          applicationReference: item.application_reference,
          transactionId: item.transaction_id,
        })),
      );
    }
    if (rawExceptions.status === "fulfilled") {
      setExceptions(
        rawExceptions.value.map((item) => ({
          id: String(item.id),
          applicationId: item.applicationId ?? "",
          stage: item.type ?? item.category,
          system: item.sourceSystem ?? item.system,
          code: item.type ?? item.category,
          message: item.message,
          severity:
            item.severity === "critical"
              ? "Critical"
              : item.severity === "high"
                ? "High"
                : "Medium",
          detectedAt: item.createdAt,
          attempts: item.retryCount,
          status:
            item.status === "RESOLVED"
              ? "Recovered"
              : item.status === "ESCALATED"
                ? "Escalated"
                : item.status === "RETRYING"
                  ? "Retrying"
                  : item.status === "IGNORED"
                    ? "Ignored"
                    : "Open",
          recovery: "",
        })),
      );
    }
    if (rawWorkflows.status === "fulfilled") {
      setWorkflows(
        rawWorkflows.value.map((item) => ({
          id: String(item.workflow_id),
          name: item.name,
          serviceId: String(item.service_id),
          version: String(item.version),
          status: displayStatus(item.status),
          stages: item.steps.map((step) => ({
            id: step.step_id,
            name: step.name,
            ...(step.department ? { department: step.department } : {}),
          })),
        })),
      );
    }
    if (rawIntegrations.status === "fulfilled")
      setIntegrations(rawIntegrations.value.map(mapIntegration));
    if (rawMappings.status === "fulfilled") {
      setMappings(
        Object.fromEntries(
          rawMappings.value.map((mapping) => [
            String(mapping.sourceSystemId),
            mapping.rules.map((rule, index) => ({
              id: `${mapping.id}-${index}`,
              source: rule.sourceField,
              target: rule.targetField,
              transform: rule.transformation ?? "",
              required: rule.required,
              status: mapping.status,
            })),
          ]),
        ),
      );
    }
    if (rawServices.status === "fulfilled") {
      const deptNames = new Map(
        (resolved(rawDepartments) ?? []).map((department) => [department.id, department.name]),
      );
      setServices(
        rawServices.value.map((item) => ({
          id: String(item.id),
          name: item.name,
          code: item.code,
          department: deptNames.get(item.department_id) ?? "",
          summary: item.description ?? "",
          active: item.is_active,
        })),
      );
    }
    if (rawDepartments.status === "fulfilled") {
      setDepartments(
        rawDepartments.value.map((item) => ({
          id: String(item.id),
          name: item.name,
          services: (resolved(rawServices) ?? [])
            .filter((service) => service.department_id === item.id)
            .map((service) => String(service.id)),
        })),
      );
    }
    if (rawUsers.status === "fulfilled") {
      setUsers(
        rawUsers.value.map((item) => ({
          id: String(item.id),
          name: item.full_name,
          email: item.email,
          role: displayBackendRole(item.role),
          department: item.department ?? "",
          status: item.is_active ? "Active" : "Suspended",
          lastActive: item.created_at,
        })),
      );
    }
    setIsLive(!rejected.length);
    setLastUpdated(new Date());
  }, []);

  useEffect(() => {
    let active = true;
    void api
      .restoreSession()
      .then((profile) => {
        if (active && profile) {
          setUser({
            id: profile.id,
            name: profile.full_name,
            email: profile.email,
            mobile: profile.phone ?? "",
            role: displayBackendRole(profile.role),
            backendRole: profile.role,
            department: profile.department ?? "",
            avatarInitial: profile.full_name.charAt(0).toUpperCase(),
          });
        }
      })
      .finally(() => {
        if (active) {
          void refreshLiveData().finally(() => setReady(true));
        }
      });
    const interval = window.setInterval(() => void refreshLiveData(), 30_000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [refreshLiveData]);

  const updateApplication = useCallback(
    async (id: string, patch: Partial<Application>) => {
      const target = applications.find((application) => application.id === id);
      if (!target?.backendId || !patch.status)
        throw new Error("Select an application and supported action.");
      const status =
        patch.status === "Completed"
          ? "approved"
          : patch.status === "Failed"
            ? "rejected"
            : "under_review";
      await api.updateApplicationStatus(target.backendId, status, "");
      await refreshLiveData();
    },
    [applications, refreshLiveData],
  );

  const updateConsent = useCallback(
    async (id: string, status: Consent["status"]) => {
      const consent = consents.find((item) => item.id === id);
      if (!consent) throw new Error("Consent request not found.");
      if (status === "Revoked") await api.revokeConsent(Number(id));
      else if (status === "Active") await api.approveConsent(Number(id));
      else if (status === "Expired") await api.rejectConsent(Number(id));
      await refreshLiveData();
    },
    [consents, refreshLiveData],
  );

  const value = useMemo<Store>(
    () => ({
      user,
      signIn: setUser,
      signOut: async () => {
        await api.logout();
        setUser(null);
      },
      notifications,
      markRead: async (id) => {
        const updated = await api.markNotificationRead(Number(id));
        setNotifications((current) =>
          current.map((item) =>
            item.id === id
              ? {
                  ...item,
                  read: updated.read,
                  time: updated.created_at,
                }
              : item,
          ),
        );
      },
      markAllRead: async () => {
        await Promise.all(
          notifications
            .filter((item) => !item.read)
            .map((item) => api.markNotificationRead(Number(item.id))),
        );
        await refreshLiveData();
      },
      exceptions,
      updateException: async (id, patch) => {
        if (!patch.status) return;
        await api.updateException(Number(id), {
          status:
            patch.status === "Recovered"
              ? "RESOLVED"
              : (patch.status.toUpperCase() as
                  "OPEN" | "RETRYING" | "RESOLVED" | "ESCALATED" | "IGNORED"),
        });
        await refreshLiveData();
      },
      consents,
      updateConsent,
      applications,
      updateApplication,
      workflows,
      createWorkflow: () => {
        throw new Error("Workflow creation requires the workflow service API.");
      },
      updateWorkflow: async () => {
        throw new Error("Workflow changes must be submitted through a configured workflow API.");
      },
      integrations,
      updateIntegration: async (id) => {
        await api.pingPlatform(Number(id));
        await refreshLiveData();
      },
      mappings,
      saveMapping: async () => {
        throw new Error(
          "Mapping changes are read-only until a backend save endpoint is available.",
        );
      },
      services,
      departments,
      users,
      lastUpdated,
      ready,
      isLive,
      liveStats,
      loadError,
      refreshLiveData,
    }),
    [
      user,
      notifications,
      exceptions,
      consents,
      updateConsent,
      applications,
      updateApplication,
      workflows,
      integrations,
      mappings,
      services,
      departments,
      users,
      lastUpdated,
      ready,
      isLive,
      liveStats,
      loadError,
      refreshLiveData,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useGovFlow() {
  const context = useContext(Ctx);
  if (!context) throw new Error("useGovFlow must be used inside GovFlowProvider");
  return context;
}

export function useScopedApplications() {
  return useGovFlow().applications;
}
