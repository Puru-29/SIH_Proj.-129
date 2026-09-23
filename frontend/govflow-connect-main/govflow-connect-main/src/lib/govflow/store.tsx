import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  APPLICATIONS,
  CONSENTS,
  EXCEPTIONS,
  INTEGRATIONS,
  LOCATIONS,
  MAPPING_PRESETS,
  NOTIFICATIONS,
  WORKFLOWS,
  SERVICES,
  getLocation,
  type Consent,
  type ExceptionItem,
  type Application,
  type Integration,
  type Workflow,
  type FieldMap,
  type Notification,
  type Role,
} from "./data";
import {
  api,
  type DashboardStats,
  type MeshApplication,
  type MeshConsent,
  type MeshNodePlatform,
} from "@/lib/api";

export type SessionUser = {
  name: string;
  email: string;
  mobile: string;
  role: Role;
  department: string;
  avatarInitial: string;
};

export type ConsentHistoryEntry = {
  status: Consent["status"];
  timestamp: string;
  actor: string;
};

type Store = {
  user: SessionUser | null;
  signIn: (u: SessionUser) => void;
  signOut: () => void;
  locationId: string;
  setLocationId: (id: string) => void;
  location: ReturnType<typeof getLocation>;
  notifications: Notification[];
  markRead: (id: string) => void;
  markAllRead: () => void;
  pushNotification: (n: Omit<Notification, "id" | "time" | "read">) => void;
  exceptions: ExceptionItem[];
  updateException: (id: string, patch: Partial<ExceptionItem>) => void;
  consents: Consent[];
  updateConsent: (id: string, status: Consent["status"]) => void;
  consentHistory: Record<string, ConsentHistoryEntry[]>;
  applications: Application[];
  updateApplication: (id: string, patch: Partial<Application>) => void;
  workflows: Workflow[];
  createWorkflow: (workflow: Workflow) => void;
  updateWorkflow: (id: string, patch: Partial<Workflow>) => void;
  integrations: Integration[];
  updateIntegration: (id: string, patch: Partial<Integration>) => void;
  mappings: Record<string, FieldMap[]>;
  saveMapping: (integrationId: string, mapping: FieldMap[]) => void;
  lastUpdated: Date;
  ready: boolean;
  isLive: boolean;
  liveStats: DashboardStats | null;
  refreshLiveData: () => Promise<void>;
};

const Ctx = createContext<Store | null>(null);

const KEY = "govflow.state.v2"; // v2 to bypass stale mock data

const nowIso = () =>
  new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });

function mapBackendApplication(app: MeshApplication, index: number): Application {
  const serviceCode = (app.service_code || "").toUpperCase();
  let serviceId = "scholarship";
  if (serviceCode.includes("AGRI") || serviceCode.includes("FRM")) serviceId = "farmer-assistance";
  else if (serviceCode.includes("RTO") || serviceCode.includes("DL")) serviceId = "driving-license";
  else if (serviceCode.includes("RC") || serviceCode.includes("PDS") || serviceCode.includes("SUB")) serviceId = "subsidy";
  else if (serviceCode.includes("INC") || serviceCode.includes("REV")) serviceId = "income-certificate";

  const loc = LOCATIONS[index % LOCATIONS.length]!;

  let status: Application["status"] = "In Progress";
  let stageId = "verification";
  if (app.status === "approved") {
    status = "Completed";
    stageId = "completed";
  } else if (app.status === "rejected") {
    status = "Failed";
    stageId = "exception";
  } else if (app.status === "submitted") {
    status = "Pending";
    stageId = "eligibility";
  } else {
    status = "In Progress";
    stageId = "education";
  }

  const createdAt = app.created_at || (app as MeshApplication & { createdAt?: string }).createdAt;
  const dateStr = createdAt
    ? new Date(createdAt).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : `${(index % 27) + 1} Sep 2026`;

  return {
    id: app.reference_id || `APP-${app.id}`,
    citizen: app.citizen_name || `Citizen #${app.citizen_id}`,
    citizenId: `CIT-${900100 + app.citizen_id}`,
    serviceId,
    locationId: loc.id,
    status,
    stageId,
    submitted: dateStr,
    consentIds: [`CA-2026-${70000 + app.id}`],
    exceptionIds: status === "Failed" ? [`EXC-${4400 + app.id}`] : [],
  };
}

function mapBackendPlatform(p: MeshNodePlatform, index: number): Integration {
  return {
    id: p.slug || `int-${p.id}`,
    name: p.name,
    protocol: "REST / JSON",
    owner: p.name.split(" ")[0] || "Government of India",
    health: p.status === "active" ? "Healthy" : p.status === "degraded" ? "Degraded" : "Down",
    successRate: p.status === "active" ? 99.4 : 88.5,
    latencyMs: 24 + ((index * 17) % 160),
    uptime: 99.9,
    failures24h: p.status === "active" ? 0 : 3,
    auth: "OAuth 2.0 + HMAC",
    baseUrl: p.base_url || "https://api.govflow.in/v1",
    endpoints: [
      { method: "GET", path: "/status", desc: "Live node health and availability" },
      { method: "POST", path: "/verify", desc: "Inter-departmental verification exchange" },
    ],
    sampleRequest: `{\n  "mesh_node": "${p.slug}",\n  "api_version": "${p.api_version}"\n}`,
    sampleResponse: `{\n  "status": "${p.status.toUpperCase()}",\n  "node": "${p.name}",\n  "timestamp": "${new Date().toISOString()}"\n}`,
    schema: ["citizen_id", "timestamp", "signature", "payload"],
  };
}

function mapBackendConsent(c: MeshConsent): Consent {
  return {
    id: `CA-2026-${c.id}`,
    applicationId: "SCH-10291",
    requestedBy: c.source_platform_name || "UIDAI / SAMARTH",
    dataRequested: c.purpose,
    purpose: c.purpose,
    recipient: c.target_platform_name || "GovFlow Inter-Governmental Mesh",
    status: c.status === "granted" ? "Active" : c.status === "revoked" ? "Revoked" : "Expired",
    grantedOn: new Date(c.created_at).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }),
    expiry: c.expires_at
      ? new Date(c.expires_at).toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric",
        })
      : "31 Dec 2026",
  };
}

export function GovFlowProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const [liveStats, setLiveStats] = useState<DashboardStats | null>(null);
  const [rawBackendApps, setRawBackendApps] = useState<MeshApplication[]>([]);
  const [rawBackendConsents, setRawBackendConsents] = useState<MeshConsent[]>([]);

  const [user, setUser] = useState<SessionUser | null>(null);
  const [locationId, setLocationId] = useState<string>(LOCATIONS[0]!.id);
  const [notifications, setNotifications] = useState<Notification[]>(NOTIFICATIONS);
  const [exceptions, setExceptions] = useState<ExceptionItem[]>(EXCEPTIONS);
  const [consents, setConsents] = useState<Consent[]>(CONSENTS);
  const [consentHistory, setConsentHistory] = useState<Record<string, ConsentHistoryEntry[]>>({});
  const [applications, setApplications] = useState<Application[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>(WORKFLOWS);
  const [integrations, setIntegrations] = useState<Integration[]>(INTEGRATIONS);
  const [mappings, setMappings] = useState(MAPPING_PRESETS);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // Function to fetch and synchronize live data from FastAPI backend
  const refreshLiveData = useCallback(async () => {
    try {
      const [statsRes, appsRes, platformsRes, consentsRes] = await Promise.allSettled([
        api.getStats(),
        api.getApplications(),
        api.getPlatforms(),
        api.getConsents(),
      ]);

      let loadedSomething = false;

      if (statsRes.status === "fulfilled" && statsRes.value) {
        setLiveStats(statsRes.value);
        loadedSomething = true;
      }

      if (appsRes.status === "fulfilled" && appsRes.value && appsRes.value.length > 0) {
        setRawBackendApps(appsRes.value);
        const mappedApps = appsRes.value.map(mapBackendApplication);
        setApplications(mappedApps);
        loadedSomething = true;
      }

      if (platformsRes.status === "fulfilled" && platformsRes.value && platformsRes.value.length > 0) {
        const mappedPlatforms = platformsRes.value.map(mapBackendPlatform);
        setIntegrations(mappedPlatforms);
        loadedSomething = true;
      }

      if (consentsRes.status === "fulfilled" && consentsRes.value && consentsRes.value.length > 0) {
        setRawBackendConsents(consentsRes.value);
        const mappedConsents = consentsRes.value.map(mapBackendConsent);
        setConsents(mappedConsents);
        setConsentHistory(
          Object.fromEntries(
            mappedConsents.map((consent) => [
              consent.id,
              [{ status: consent.status, timestamp: consent.grantedOn, actor: consent.requestedBy }],
            ]),
          ),
        );
        loadedSomething = true;
      }

      if (loadedSomething) {
        setIsLive(true);
        setLastUpdated(new Date());
      }
    } catch (err) {
      console.warn("Could not synchronize live data with backend:", err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    // Clear legacy mock localStorage cache
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("govflow.state.v1");
    }

    api.getMe().then((profile) => {
      if (profile) {
        setUser({
          name: profile.full_name,
          email: profile.email,
          mobile: profile.phone || "",
          role: profile.role === "citizen" ? "Citizen" : profile.role === "admin" ? "Admin" : profile.role === "officer" ? "Department Officer" : profile.role === "developer" ? "Developer" : profile.role === "auditor" ? "Auditor" : "Operator",
          department: "Inter-Governmental Mesh",
          avatarInitial: profile.full_name[0]?.toUpperCase() || "G",
        });
      }
    }).finally(() => refreshLiveData().finally(() => setReady(true)));

    // Poll live data every 15 seconds
    const interval = setInterval(refreshLiveData, 15000);
    return () => clearInterval(interval);
  }, [refreshLiveData]);

  const pushNotification = useCallback((n: Omit<Notification, "id" | "time" | "read">) => {
    setNotifications((prev) =>
      [{ ...n, id: `n-${Date.now()}`, time: "just now", read: false }, ...prev].slice(0, 40),
    );
  }, []);

  const updateApplication = useCallback(
    async (id: string, patch: Partial<Application>) => {
      // Optimistic local state update
      setApplications((p) => p.map((a) => (a.id === id ? { ...a, ...patch } : a)));

      // Sync with FastAPI SQLite database
      const targetBackendApp = rawBackendApps.find(
        (b) => b.reference_id === id || String(b.id) === id,
      );
      if (targetBackendApp && patch.status) {
        let backendStatus = "under_review";
        if (patch.status === "Completed") backendStatus = "approved";
        else if (patch.status === "Failed") backendStatus = "rejected";
        else if (patch.status === "Pending") backendStatus = "submitted";

        try {
          await api.updateApplicationStatus(
            targetBackendApp.id,
            backendStatus,
            "Updated from GovFlow Operator Console",
          );
        } catch (e) {
          console.warn("Backend status update failed:", e);
        }
      }
    },
    [rawBackendApps],
  );

  const updateConsent = useCallback(
    async (id: string, status: Consent["status"]) => {
      setConsents((p) => p.map((c) => (c.id === id ? { ...c, status } : c)));
      setConsentHistory((p) => ({
        ...p,
        [id]: [
          ...(p[id] ?? []),
          { status, timestamp: nowIso(), actor: user?.name ?? "GovFlow Officer" },
        ],
      }));

      // Sync with FastAPI SQLite database
      const consentIdNum = parseInt(id.replace(/\D/g, ""), 10);
      if (!isNaN(consentIdNum) && status === "Revoked") {
        try {
          await api.revokeConsent(consentIdNum);
        } catch (e) {
          console.warn("Backend consent revocation failed:", e);
        }
      }
    },
    [user],
  );

  const value = useMemo<Store>(
    () => ({
      user,
      signIn: setUser,
      signOut: () => {
        api.logout();
        setUser(null);
      },
      locationId,
      setLocationId: (id) =>
        setLocationId(LOCATIONS.some((location) => location.id === id) ? id : LOCATIONS[0]!.id),
      location: getLocation(locationId),
      notifications,
      markRead: (id) =>
        setNotifications((p) => p.map((n) => (n.id === id ? { ...n, read: true } : n))),
      markAllRead: () => setNotifications((p) => p.map((n) => ({ ...n, read: true }))),
      pushNotification,
      exceptions,
      updateException: (id, patch) =>
        setExceptions((p) => p.map((e) => (e.id === id ? { ...e, ...patch } : e))),
      consents,
      updateConsent,
      consentHistory,
      applications,
      updateApplication,
      workflows,
      createWorkflow: (workflow) => setWorkflows((p) => [workflow, ...p]),
      updateWorkflow: (id, patch) =>
        setWorkflows((p) => p.map((w) => (w.id === id ? { ...w, ...patch } : w))),
      integrations,
      updateIntegration: (id, patch) =>
        setIntegrations((p) => p.map((i) => (i.id === id ? { ...i, ...patch } : i))),
      mappings,
      saveMapping: (integrationId, mapping) =>
        setMappings((p) => ({ ...p, [integrationId]: mapping })),
      lastUpdated,
      ready,
      isLive,
      liveStats,
      refreshLiveData,
    }),
    [
      user,
      locationId,
      notifications,
      exceptions,
      consents,
      consentHistory,
      applications,
      workflows,
      integrations,
      mappings,
      lastUpdated,
      pushNotification,
      ready,
      isLive,
      liveStats,
      refreshLiveData,
      updateApplication,
      updateConsent,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useGovFlow() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useGovFlow must be used inside GovFlowProvider");
  return ctx;
}

/** Location-aware application list. Shows live applications for current location or all if city matches. */
export function useScopedApplications() {
  const { locationId, applications } = useGovFlow();
  return useMemo(() => {
    const matched = applications.filter((a) => a.locationId === locationId);
    return matched.length > 0 ? matched : applications;
  }, [applications, locationId]);
}
