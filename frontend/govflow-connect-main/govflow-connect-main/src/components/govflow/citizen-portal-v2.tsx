import { Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ArrowRight,
  Bell,
  Briefcase,
  Building2,
  Check,
  CircleAlert,
  FileText,
  FileUser,
  GraduationCap,
  HandCoins,
  Landmark,
  Menu,
  Search,
  ShieldCheck,
  Sparkles,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApplicationWizard } from "@/components/govflow/application-wizard";
import { api, type MeshApplication } from "@/lib/api";
import {
  approveConsent,
  applicationsMock,
  consentRequests,
  documentList,
  getApplications,
  getCitizenProfile,
  getConsentRequests,
  getDocuments,
  getGrievances,
  getNotifications,
  getServices,
  getVerifiedRecords,
  grievanceList,
  notificationsMock,
  rejectConsent,
  revokeConsent,
  type ApplicationItem,
  type CitizenProfile,
  type ConsentRequest,
  type DocumentItem,
  type GovernmentService,
  type GrievanceItem,
  type NotificationItem,
  type RecordItem,
} from "@/services/api";

export type CitizenPage =
  | "dashboard"
  | "apply"
  | "services"
  | "applications"
  | "track"
  | "records"
  | "consent"
  | "notifications"
  | "grievances"
  | "profile";

const NAV_ITEMS = [
  { group: "Overview", items: [{ key: "dashboard", label: "Overview", icon: Landmark }] },
  { group: "Services", items: [{ key: "services", label: "Services", icon: FileText }] },
  { group: "Applications", items: [{ key: "applications", label: "My Applications", icon: FileUser }, { key: "track", label: "Track Applications", icon: Search }] },
  { group: "Records", items: [{ key: "records", label: "Verified Records", icon: ShieldCheck }, { key: "consent", label: "Consent & Data Sharing", icon: Check }] },
  { group: "Communication", items: [{ key: "notifications", label: "Notifications", icon: Bell }, { key: "grievances", label: "Grievances", icon: Users }] },
  { group: "Account", items: [{ key: "profile", label: "Profile", icon: UserRound }] },
] as const;

const filterOptions = ["All", "Revenue", "Education", "Social Welfare", "Transport", "Municipal", "Employment"] as const;
function getStatusClass(status: string) {
  switch (status) {
    case "Approved":
    case "Documents Verified":
      return "success";
    case "Under Verification":
    case "Action Required":
    case "Appointment Required":
      return "warning";
    case "Rejected":
      return "danger";
    default:
      return "info";
  }
}

function formatPageTitle(page: CitizenPage) {
  const map: Record<CitizenPage, string> = {
    dashboard: "Dashboard",
    apply: "Apply for a Service",
    services: "Government Services",
    applications: "My Applications",
    track: "Track Application",
    records: "Verified Records",
    consent: "Consent & Data Sharing",
    notifications: "Notifications",
    grievances: "Grievances & Support",
    profile: "Profile",
  };
  return map[page];
}

function navigateToCitizenPage(navigate: ReturnType<typeof useNavigate>, page: CitizenPage) {
  navigate({ to: "/citizen/$page", params: { page } });
}

export function CitizenPortalApp({ page = "dashboard" }: { page?: CitizenPage }) {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState("");
  const [serviceCategory, setServiceCategory] = useState<(typeof filterOptions)[number]>("All");
  const [applications, setApplications] = useState<ApplicationItem[]>(applicationsMock);
  const [services, setServices] = useState<GovernmentService[]>([]);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [consents, setConsents] = useState<ConsentRequest[]>(consentRequests);
  const [documents, setDocuments] = useState<DocumentItem[]>(documentList);
  const [notifications, setNotifications] = useState<NotificationItem[]>(notificationsMock);
  const [grievances, setGrievances] = useState<GrievanceItem[]>(grievanceList);
  const [profile, setProfile] = useState<CitizenProfile>({
    id: "",
    citizenId: "",
    fullName: "",
    email: "",
    phone: "",
    address: "",
    preferredLanguage: "English",
    verifiedMobile: false,
    verifiedEmail: false,
  });
  const [selectedAppId, setSelectedAppId] = useState(applicationsMock[0]?.applicationId ?? "");
  const [selectedServiceId, setSelectedServiceId] = useState<string | null>(null);
  const [trackValue, setTrackValue] = useState("");
  const [trackedBackendApplication, setTrackedBackendApplication] = useState<MeshApplication | null>(null);
  const [grievanceForm, setGrievanceForm] = useState({
    category: "Service delay",
    relatedApplication: "APP-2026-10294",
    department: "Revenue",
    description: "",
    priority: "Medium",
  });

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    Promise.all([
      getCitizenProfile(),
      getServices(),
      getApplications(),
      getVerifiedRecords(),
      getConsentRequests(),
      getDocuments(),
      getNotifications(),
      getGrievances(),
    ]).then(([profileData, servicesData, applicationsData, recordsData, consentData, documentData, notificationsData, grievancesData]) => {
      if (!isMounted) return;
      if (profileData) setProfile(profileData);
      setServices(servicesData);
      setApplications(applicationsData);
      setSelectedAppId(applicationsData[0]?.applicationId ?? selectedAppId);
      setRecords(recordsData);
      setConsents(consentData);
      setDocuments(documentData);
      setNotifications(notificationsData);
      setGrievances(grievancesData);

      if (typeof window !== "undefined") {
        const savedServiceId = window.localStorage.getItem("govflow-selected-service");
        if (savedServiceId && servicesData.some((service) => service.id === savedServiceId)) {
          setSelectedServiceId(savedServiceId);
        } else {
          setSelectedServiceId(null);
        }
      }

      setLoading(false);
    }).catch(() => {
      if (isMounted) {
        setLoading(false);
        toast.error("Unable to connect to the department right now.");
      }
    });

    return () => {
      isMounted = false;
    };
  }, [selectedAppId]);

  const selectedApplication = applications.find((application) => application.applicationId === selectedAppId) ?? applications[0];
  const mockTrackedApplication = applications.find((application) =>
    application.applicationId.toLowerCase() === trackValue.trim().toLowerCase() ||
    application.id.toLowerCase() === trackValue.trim().toLowerCase(),
  );
  const selectedService = services.find((service) => service.id === selectedServiceId);

  const filteredServices = useMemo(() => {
    const value = searchText.trim().toLowerCase();
    return services.filter((service) => {
      const matchesCategory = serviceCategory === "All" || service.department === serviceCategory;
      const matchesQuery = !value || `${service.name} ${service.department} ${service.description}`.toLowerCase().includes(value);
      return matchesCategory && matchesQuery;
    });
  }, [services, searchText, serviceCategory]);

  const filteredNotifications = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    return notifications.filter((entry) => !query || `${entry.title} ${entry.description}`.toLowerCase().includes(query));
  }, [notifications, searchText]);

  const filteredDocuments = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    return documents.filter((entry) => !query || `${entry.name} ${entry.issuingDepartment}`.toLowerCase().includes(query));
  }, [documents, searchText]);

  const searchResults = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    if (!query) return [];
    const serviceHits = services.filter((service) => `${service.name} ${service.department}`.toLowerCase().includes(query)).slice(0, 4);
    const appHits = applications.filter((app) => `${app.service} ${app.applicationId}`.toLowerCase().includes(query)).slice(0, 3);
    const docHits = documents.filter((doc) => `${doc.name} ${doc.issuingDepartment}`.toLowerCase().includes(query)).slice(0, 2);
    return [...serviceHits, ...appHits, ...docHits].slice(0, 6);
  }, [applications, documents, searchText, services]);

  const unreadNotifications = notifications.filter((entry) => !entry.read).length;

  const handleServiceApply = (service: GovernmentService) => {
    setSelectedServiceId(service.id);
    if (typeof window !== "undefined") window.localStorage.setItem("govflow-selected-service", service.id);
  };

  const startServiceApplication = (service: GovernmentService) => {
    handleServiceApply(service);
    navigateToCitizenPage(navigate, "apply");
  };

  const markAsRead = async (id: string) => {
    const next = notifications.map((item) => (item.id === id ? { ...item, read: true } : item));
    setNotifications(next);
    await getNotifications();
    toast.success("Notification marked as read.");
  };

  const handleConsentAction = async (id: string, action: "approve" | "reject" | "revoke") => {
    if (action === "approve") {
      await approveConsent(id);
      setConsents((current) => current.map((consent) => (consent.id === id ? { ...consent, status: "Granted" } : consent)));
      toast.success("Consent approved.");
    }
    if (action === "reject") {
      await rejectConsent(id);
      setConsents((current) => current.map((consent) => (consent.id === id ? { ...consent, status: "Revoked" } : consent)));
      toast.success("Consent rejected.");
    }
    if (action === "revoke") {
      await revokeConsent(id);
      setConsents((current) => current.map((consent) => (consent.id === id ? { ...consent, status: "Revoked" } : consent)));
      toast.success("Permission revoked.");
    }
  };

  const loadApplicationTracking = async (referenceId: string) => {
    try {
      const application = await api.trackApplication(referenceId);
      if (!application) {
        setTrackedBackendApplication(null);
        if (mockTrackedApplication) {
          setSelectedAppId(mockTrackedApplication.applicationId);
          return;
        }
        toast.error("Application not found. Please check the ID and try again.");
        return;
      }
      setTrackedBackendApplication(application);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load application tracking.";
      toast.error(message);
    }
  };

  const handleTrackApplication = async (event: FormEvent) => {
    event.preventDefault();
    const value = trackValue.trim();
    if (!value) {
      toast.error("Enter an application ID to track.");
      return;
    }
    await loadApplicationTracking(value);
  };

  const handleGrievanceSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!grievanceForm.description.trim()) {
      toast.error("Please add a brief description of your grievance.");
      return;
    }
    const item: GrievanceItem = {
      id: `GRV-2026-${Math.floor(10000 + Math.random() * 90000)}`,
      category: grievanceForm.category,
      relatedApplication: grievanceForm.relatedApplication,
      department: grievanceForm.department as any,
      description: grievanceForm.description,
      priority: grievanceForm.priority as "Low" | "Medium" | "High",
      status: "Submitted",
    };
    setGrievances((current) => [item, ...current]);
    setGrievanceForm({
      category: "Service delay",
      relatedApplication: "APP-2026-10294",
      department: "Revenue",
      description: "",
      priority: "Medium",
    });
    toast.success(`Grievance raised successfully. ID: ${item.id}`);
  };

  return (
    <div className="citizen-portal">
      <aside className={`citizen-sidebar ${sidebarOpen ? "is-open" : ""}`}>
        <div className="citizen-brand">
          <div className="citizen-brand-mark">
            <Landmark className="size-5" />
          </div>
          <div>
            <strong>
              Gov<span>Flow</span>
            </strong>
            <small>Citizen Portal</small>
            <em>Your Services, Simplified</em>
          </div>
          <button className="citizen-mobile-close" aria-label="Close menu" onClick={() => setSidebarOpen(false)}>
            <X className="size-4" />
          </button>
        </div>

        <nav className="citizen-nav" aria-label="Citizen portal navigation">
          {NAV_ITEMS.map(({ group, items }) => (
            <div key={group} style={{ display: "grid", gap: "0.35rem" }}>
              <span style={{ padding: "0.55rem 0.7rem 0.25rem", fontSize: "0.8rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#465766", fontWeight: 700 }}>
                {group}
              </span>
              {items.map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  type="button"
                  className={page === key ? "is-active" : ""}
                  onClick={() => {
                    setSidebarOpen(false);
                    navigate({ to: `/citizen/${key === "dashboard" ? "" : key}` as any });
                  }}
                  aria-current={page === key ? "page" : undefined}
                >
                  <Icon className="size-4" />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="citizen-sidebar-footer">
          <p>One citizen. One portal. Multiple government services.</p>
          <button type="button" onClick={() => navigate({ to: "/citizen/login" })}>
            <X className="size-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {sidebarOpen ? <button type="button" className="citizen-nav-overlay" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} /> : null}

      <main className="citizen-main">
        <header className="citizen-topbar">
          <button type="button" className="citizen-mobile-menu" aria-label="Open menu" onClick={() => setSidebarOpen(true)}>
            <Menu className="size-4" />
          </button>

          <div className="citizen-top-search" role="search">
            <Search className="size-4" />
            <input
              aria-label="Global search"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="Search services, applications, documents..."
            />
            <kbd>⌘K</kbd>
          </div>

          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <button type="button" className="citizen-notification" aria-label="Notifications">
              <Bell className="size-4" />
              {unreadNotifications > 0 ? <span>{unreadNotifications}</span> : null}
            </button>
            <button type="button" className="citizen-profile-trigger" aria-label="Citizen profile">
              <span>{profile.fullName.charAt(0) || "?"}</span>
              <div>
                <b>{profile.fullName}</b>
                <small>Citizen ID: {profile.citizenId}</small>
              </div>
            </button>
          </div>
        </header>

        {searchText.trim() ? (
          <div className="citizen-content" style={{ paddingTop: "0.6rem" }}>
            <div className="surface" style={{ padding: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>Search results for “{searchText}”</strong>
                <button type="button" className="text-sm text-primary" onClick={() => setSearchText("")}>Clear</button>
              </div>
              <div style={{ display: "grid", gap: "0.6rem", marginTop: "0.8rem" }}>
                {searchResults.length > 0 ? searchResults.map((result) => (
                  <button
                    key={result.id}
                    type="button"
                    className="citizen-available-service"
                    style={{ padding: "0.7rem 0.8rem", border: "1px solid #e0ebea", background: "#f9fdfb" }}
                    onClick={() => {
                      if ("service" in result && "department" in result) {
                        navigateToCitizenPage(navigate, "applications");
                      }
                      setSearchText("");
                    }}
                  >
                    <Search className="size-4" />
                    <span>
                      <strong>{"service" in result ? result.service : result.name}</strong>
                      <small>{"department" in result ? result.department : result.issuingDepartment || "Government service"}</small>
                    </span>
                  </button>
                )) : <p className="text-sm text-muted-foreground">No matching records found.</p>}
              </div>
            </div>
          </div>
        ) : null}

        <div className="citizen-content">
          {loading && page !== "apply" ? (
            <div className="surface" style={{ padding: "2rem", textAlign: "center" }}>
              <p className="text-sm text-muted-foreground">Loading your citizen dashboard...</p>
            </div>
          ) : (
            <div className="citizen-page">
              {page === "dashboard" && (
                <>
                  <div className="citizen-welcome">
                    <div>
                      <span className="citizen-eyebrow">Secure government access</span>
                      <h1>
                        Good morning, {profile.fullName.trim().split(" ")[0] || "there"}
                        <span className="citizen-sun"> </span>
                      </h1>
                      <p>Manage government services, applications and verified records from one place.</p>
                    </div>
                    <div className="citizen-action-row">
                      <Button onClick={() => navigateToCitizenPage(navigate, "services")}>Apply for a Service</Button>
                      <Button variant="outline" onClick={() => navigateToCitizenPage(navigate, "track")}>Track Application</Button>
                    </div>
                  </div>

                  <div className="citizen-stat-grid" style={{ marginTop: "1rem" }}>
                    {[{ label: "Total Applications", value: applications.length, tone: "mint", icon: FileText, detail: "All records" }, { label: "In Progress", value: applications.filter((item) => item.status !== "Approved" && item.status !== "Rejected").length, tone: "orange", icon: FileUser, detail: "Active" }, { label: "Completed", value: applications.filter((item) => item.status === "Approved").length, tone: "blue", icon: Check, detail: "Closed" }, { label: "Action Required", value: applications.filter((item) => item.status === "Action Required" || item.status === "Appointment Required").length, tone: "rose", icon: CircleAlert, detail: "Needs review" }].map(({ label, value, tone, icon: Icon, detail }) => (
                      <button
                        key={label}
                        type="button"
                        className={`citizen-stat-card ${tone}`}
                        onClick={() => {
                          if (label === "Total Applications") navigateToCitizenPage(navigate, "applications");
                          if (label === "In Progress") navigateToCitizenPage(navigate, "applications");
                          if (label === "Action Required") navigateToCitizenPage(navigate, "applications");
                          if (label === "Completed") navigateToCitizenPage(navigate, "applications");
                        }}
                      >
                        <div className="citizen-stat-icon"><Icon className="size-4" /></div>
                        <div>
                          <span>{label}</span>
                          <strong>{value}</strong>
                          <small>{detail}</small>
                        </div>
                      </button>
                    ))}
                  </div>

                  <div className="citizen-dashboard-grid">
                    <Card style={{ borderRadius: "0.9rem" }}>
                      <CardHeader className="card-header">
                        <div>
                          <CardTitle>Active Applications</CardTitle>
                          <p>Application status and movement across departments</p>
                        </div>
                        <button type="button" onClick={() => navigateToCitizenPage(navigate, "applications")}>View all</button>
                      </CardHeader>
                      <CardContent>
                        <div style={{ display: "grid", gap: "0.7rem" }}>
                          {applications.slice(0, 3).map((application) => (
                            <div
                              key={application.applicationId}
                              className={`citizen-application-row ${selectedAppId === application.applicationId ? "is-selected" : ""}`}
                              role="button"
                              tabIndex={0}
                              onClick={() => {
                                setSelectedAppId(application.applicationId);
                                navigateToCitizenPage(navigate, "applications");
                              }}
                              onKeyDown={(event) => {
                                if (event.key === "Enter" || event.key === " ") {
                                  event.preventDefault();
                                  setSelectedAppId(application.applicationId);
                                  navigateToCitizenPage(navigate, "applications");
                                }
                              }}
                            >
                              <div className="citizen-application-top">
                                <span>
                                  <strong>{application.service}</strong>
                                  <small>{application.department} Department</small>
                                </span>
                                <span className={`citizen-status ${getStatusClass(application.status)}`}>{application.status}</span>
                              </div>
                              <div className="citizen-application-meta">
                                <b>Application ID: {application.applicationId}</b>
                                <b>{application.progress}%</b>
                              </div>
                              <div className="citizen-progress"><span style={{ width: `${application.progress}%` }} /></div>
                              <div className="citizen-submitted">Last updated: {application.lastUpdated}</div>
                              <div style={{ display: "flex", gap: "0.6rem", marginTop: "0.8rem" }}>
                                <Button variant="outline" size="sm" onClick={(event) => { event.stopPropagation(); setSelectedAppId(application.applicationId); navigateToCitizenPage(navigate, "applications"); }}>View Details</Button>
                                <Button size="sm" onClick={(event) => { event.stopPropagation(); setSelectedAppId(application.applicationId); navigateToCitizenPage(navigate, "track"); }}>Track Status</Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>

                    <Card style={{ borderRadius: "0.9rem" }}>
                      <CardHeader className="card-header">
                        <div>
                          <CardTitle>Verified Records Available</CardTitle>
                          <p>Securely retrieved from connected departments</p>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <p style={{ fontSize: "0.8rem", lineHeight: "1.6", color: "#465766" }}>
                          GovFlow can securely retrieve verified records from connected government departments, reducing repeated document submission.
                        </p>
                        <div className="citizen-available-list" style={{ marginTop: "1rem" }}>
                          {records.map((record) => (
                            <div key={record.id} className="citizen-available-service">
                              <ShieldCheck className="size-4 text-green-700" />
                              <span>
                                <strong>{record.name}</strong>
                                <small>{record.status} · {record.sourceDepartment}</small>
                              </span>
                            </div>
                          ))}
                        </div>
                        <Button className="mt-4 w-full" onClick={() => navigateToCitizenPage(navigate, "records")}>View Verified Records</Button>
                      </CardContent>
                    </Card>
                  </div>

                  <div className="citizen-lower-grid">
                    <Card style={{ borderRadius: "0.9rem" }}>
                      <CardHeader className="card-header">
                        <div>
                          <CardTitle>Services For You</CardTitle>
                          <p>Popular citizen services and applications</p>
                        </div>
                        <button type="button" onClick={() => navigateToCitizenPage(navigate, "services")}>Explore</button>
                      </CardHeader>
                      <CardContent>
                        <div style={{ display: "grid", gap: "0.8rem", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))" }}>
                          {services.slice(0, 6).map((service) => (
                            <div key={service.id} className="surface" style={{ padding: "0.9rem" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: "0.7rem" }}>
                                <div className={`citizen-service-icon ${service.department === "Revenue" ? "mint" : service.department === "Social Welfare" ? "orange" : service.department === "Transport" ? "blue" : service.department === "Municipal" ? "green" : "purple"}`}>
                                  {service.department === "Revenue" ? <Landmark className="size-4" /> : service.department === "Social Welfare" ? <HandCoins className="size-4" /> : service.department === "Transport" ? <Building2 className="size-4" /> : service.department === "Municipal" ? <Users className="size-4" /> : <Briefcase className="size-4" />}
                                </div>
                                <div style={{ minWidth: 0 }}>
                                  <strong style={{ display: "block", fontSize: "0.8rem" }}>{service.name}</strong>
                                  <small style={{ color: "#465766", fontSize: "0.8rem" }}>{service.department} Department</small>
                                </div>
                              </div>
                              <p style={{ marginTop: "0.7rem", color: "#465766", fontSize: "0.8rem", lineHeight: "1.6" }}>{service.description}</p>
                              <div style={{ display: "flex", justifyContent: "space-between", marginTop: "0.8rem", fontSize: "0.8rem", color: "#465766" }}>
                                <span>{service.processingTime}</span>
                                <span>{service.fee}</span>
                              </div>
                              <Button className="mt-3 w-full" size="sm" onClick={() => startServiceApplication(service)}>Apply</Button>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>

                    <Card style={{ borderRadius: "0.9rem" }}>
                      <CardHeader className="card-header">
                        <div>
                          <CardTitle>Your Data Permissions</CardTitle>
                          <p>Consent-based sharing across departments</p>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div style={{ display: "grid", gap: "0.7rem" }}>
                          {consents.slice(0, 2).map((consent) => (
                            <div key={consent.id} className="surface" style={{ padding: "0.8rem" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.4rem" }}>
                                <strong style={{ fontSize: "0.8rem" }}>{consent.department}</strong>
                                <span className={`citizen-status ${consent.status === "Awaiting Approval" ? "warning" : "success"}`}>{consent.status}</span>
                              </div>
                              <p style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "#465766" }}>{consent.purpose}</p>
                              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.7rem" }}>
                                {consent.status === "Awaiting Approval" ? (
                                  <>
                                    <Button size="sm" variant="outline" onClick={() => handleConsentAction(consent.id, "approve")}>Review Request</Button>
                                    <Button size="sm" variant="ghost" onClick={() => handleConsentAction(consent.id, "reject")}>Manage Permissions</Button>
                                  </>
                                ) : (
                                  <Button size="sm" variant="outline" onClick={() => handleConsentAction(consent.id, "revoke")}>Revoke Access</Button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  <div className="citizen-lower-grid" style={{ marginTop: "0.9rem" }}>
                    <Card style={{ borderRadius: "0.9rem" }}>
                      <CardHeader className="card-header">
                        <div>
                          <CardTitle>Recent Notifications</CardTitle>
                          <p>System and application updates</p>
                        </div>
                        <button type="button" onClick={() => navigateToCitizenPage(navigate, "notifications")}>View All Notifications</button>
                      </CardHeader>
                      <CardContent>
                        <div style={{ display: "grid", gap: "0.7rem" }}>
                          {notifications.slice(0, 4).map((notification) => (
                            <div key={notification.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", padding: "0.7rem 0.8rem", border: "1px solid #e5eee9", borderRadius: "0.7rem" }}>
                              <div>
                                <strong style={{ display: "block", fontSize: "0.8rem" }}>{notification.title}</strong>
                                <small style={{ color: "#465766", fontSize: "0.8rem" }}>{notification.description}</small>
                              </div>
                              <span style={{ color: "#465766", fontSize: "0.8rem" }}>{notification.time}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>

                    <Card style={{ borderRadius: "0.9rem" }}>
                      <CardHeader className="card-header">
                        <div>
                          <CardTitle>How GovFlow Connects Your Services</CardTitle>
                          <p>Shared verified information across departments</p>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div style={{ display: "grid", placeItems: "center", gap: "0.6rem", padding: "1rem 0" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                            <div className="citizen-service-icon mint"><Landmark className="size-4" /></div>
                            <span style={{ fontWeight: 700, fontSize: "0.8rem" }}>GOVFLOW</span>
                          </div>
                          <div style={{ display: "flex", gap: "1.2rem" }}>
                            <div className="citizen-service-icon mint"><Briefcase className="size-4" /></div>
                            <div className="citizen-service-icon mint"><GraduationCap className="size-4" /></div>
                            <div className="citizen-service-icon mint"><HandCoins className="size-4" /></div>
                          </div>
                          <div style={{ display: "flex", gap: "1rem", fontSize: "0.8rem", color: "#465766" }}>
                            <span>Revenue</span>
                            <span>Education</span>
                            <span>Welfare</span>
                          </div>
                        </div>
                        <p style={{ color: "#465766", fontSize: "0.8rem", lineHeight: "1.6" }}>
                          GovFlow securely connects participating government departments so verified information can be reused when you give permission.
                        </p>
                      </CardContent>
                    </Card>
                  </div>

                  <Card style={{ marginTop: "0.9rem", borderRadius: "0.9rem" }}>
                    <CardHeader className="card-header">
                      <div>
                        <CardTitle>Your Data, Your Control</CardTitle>
                        <p>Trust and privacy in the citizen journey</p>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div style={{ display: "grid", gap: "0.7rem", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
                        {[
                          "Consent-based sharing",
                          "Secure authentication",
                          "Department-level access control",
                          "Activity audit trail",
                          "Verified government records",
                        ].map((item) => (
                          <div key={item} style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.65rem 0.75rem", borderRadius: "0.7rem", background: "#f4faf5" }}>
                            <ShieldCheck className="size-4 text-green-700" />
                            <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>{item}</span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </>
              )}

              {page === "services" && (
                <>
                  <div className="citizen-welcome" style={{ alignItems: "center" }}>
                    <div>
                      <span className="citizen-eyebrow">Government services</span>
                      <h1>Government Services</h1>
                    </div>
                  </div>
                  <div className="citizen-search-row">
                    <div className="citizen-search-input" style={{ maxWidth: "30rem" }}>
                      <Search className="size-4" />
                      <input value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder="Search services..." aria-label="Search government services" />
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
                    {filterOptions.map((option) => (
                      <button
                        key={option}
                        type="button"
                        className={serviceCategory === option ? "citizen-status success" : "citizen-status info"}
                        style={{ border: "1px solid #dfeae3", cursor: "pointer" }}
                        onClick={() => setServiceCategory(option)}
                      >
                        {option}
                      </button>
                    ))}
                  </div>

                  {selectedService ? (
                    <Card style={{ borderRadius: "0.9rem", marginBottom: "1rem" }}>
                      <CardHeader>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "0.8rem", alignItems: "center", flexWrap: "wrap" }}>
                          <div>
                            <span className="citizen-eyebrow">Service Details</span>
                            <CardTitle style={{ fontSize: "1.3rem", marginTop: "0.35rem" }}>{selectedService.name}</CardTitle>
                          </div>
                          <Button onClick={() => startServiceApplication(selectedService)}>Start Application</Button>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
                          <div className="surface" style={{ padding: "1rem", borderRadius: "0.8rem" }}>
                            <strong style={{ display: "block", marginBottom: "0.5rem" }}>Service overview</strong>
                            <p style={{ color: "#465766", fontSize: "0.8rem", lineHeight: "1.7" }}>{selectedService.description}</p>
                            <ul style={{ marginTop: "0.8rem", paddingLeft: "1rem", color: "#465766", fontSize: "0.8rem", lineHeight: "1.8" }}>
                              <li>Service ID: {selectedService.id}</li>
                              <li>Department: {selectedService.department}</li>
                              <li>Estimated processing: {selectedService.estimatedProcessingTime ?? selectedService.processingTime}</li>
                              <li>Fee: {selectedService.fee}</li>
                            </ul>
                          </div>
                          <div className="surface" style={{ padding: "1rem", borderRadius: "0.8rem" }}>
                            <strong style={{ display: "block", marginBottom: "0.5rem" }}>Required information</strong>
                            <div style={{ display: "grid", gap: "0.4rem", fontSize: "0.8rem", color: "#465766" }}>
                              <span><strong>Required data:</strong> {selectedService.requiredData.join(", ")}</span>
                              <span><strong>Required documents:</strong> {selectedService.requiredDocuments.join(", ")}</span>
                              <span><strong>Interoperability:</strong> {selectedService.interoperabilityRequirements.join(", ")}</span>
                            </div>
                          </div>
                          <div className="surface" style={{ padding: "1rem", borderRadius: "0.8rem" }}>
                            <strong style={{ display: "block", marginBottom: "0.5rem" }}>Workflow</strong>
                            <ol style={{ margin: 0, paddingLeft: "1rem", color: "#465766", fontSize: "0.8rem", lineHeight: "1.9" }}>
                              {selectedService.workflow.map((step) => <li key={step}>{step}</li>)}
                            </ol>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ) : null}

                  <div className="citizen-service-grid" style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))" }}>
                    {filteredServices.map((service) => (
                      <Card key={service.id} className="citizen-service-card" style={{ borderRadius: "0.85rem" }}>
                        <CardHeader className="citizen-service-card-header">
                          <div style={{ display: "flex", justifyContent: "space-between", gap: "0.6rem" }}>
                            <div>
                              <CardTitle style={{ fontSize: "1rem" }}>{service.name}</CardTitle>
                              <p style={{ fontSize: "0.85rem", color: "#465766" }}>{service.department}</p>
                            </div>
                            <button type="button" className="citizen-service-icon mint" onClick={() => setSelectedServiceId(service.id)} aria-label={`View details for ${service.name}`}>
                              <Landmark className="size-4" />
                            </button>
                          </div>
                        </CardHeader>
                        <CardContent className="citizen-service-card-content">
                          <p style={{ color: "#465766", fontSize: "0.875rem", lineHeight: "1.65" }}>{service.description}</p>
                          <div className="citizen-service-card-details" style={{ display: "grid", gap: "0.55rem", marginTop: "0.8rem", fontSize: "0.85rem", color: "#465766" }}>
                            <span>Processing time: {service.processingTime}</span>
                            <span>Fee: {service.fee}</span>
                            <span>Required documents: {service.requiredDocuments.join(", ")}</span>
                            <span>Online availability: {service.onlineAvailability ? "Available" : "Not available"}</span>
                          </div>
                          <div className="citizen-service-card-actions" style={{ display: "flex", gap: "0.6rem", marginTop: "1rem" }}>
                            <Button className="flex-1" onClick={() => setSelectedServiceId(service.id)}>View Details</Button>
                            <Button className="flex-1" variant="outline" onClick={() => startServiceApplication(service)}>Apply Now</Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </>
              )}

              {page === "apply" && (
                selectedService ? (
                  <ApplicationWizard
                    key={selectedService.id}
                    service={selectedService}
                    records={records}
                    citizenAddress={profile.address}
                    onBack={() => navigateToCitizenPage(navigate, "services")}
                    onTrack={(referenceId) => {
                      setTrackValue(referenceId);
                      void loadApplicationTracking(referenceId);
                      navigateToCitizenPage(navigate, "track");
                    }}
                  />
                ) : (
                  <div className="surface" style={{ padding: "1.5rem" }}>
                    <h1>Select a service to apply</h1>
                    <p>Choose a service before starting its application.</p>
                    <Button onClick={() => navigateToCitizenPage(navigate, "services")}>Browse services</Button>
                  </div>
                )
              )}
              {page === "applications" && (
                <>
                  <div className="citizen-welcome">
                    <div>
                      <span className="citizen-eyebrow">Application management</span>
                      <h1>My Applications</h1>
                    </div>
                    <Button onClick={() => navigateToCitizenPage(navigate, "services")}>Apply for a Service</Button>
                  </div>

                  <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "1rem" }}>
                    {['All', 'In Progress', 'Action Required', 'Completed', 'Rejected'].map((tab) => (
                      <button key={tab} type="button" className="citizen-status info" style={{ border: "1px solid #dfeae3", cursor: "pointer" }}>{tab}</button>
                    ))}
                  </div>

                  <div style={{ display: "grid", gap: "1rem", marginTop: "1rem" }}>
                    {applications.map((application) => (
                      <div key={application.id} className="surface" style={{ padding: "1rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "0.8rem", flexWrap: "wrap" }}>
                          <div>
                            <strong>{application.applicationId}</strong>
                            <div style={{ fontSize: "0.8rem", color: "#465766" }}>{application.service} · {application.department}</div>
                          </div>
                          <div className={`citizen-status ${getStatusClass(application.status)}`}>{application.status}</div>
                        </div>
                        <div style={{ display: "grid", gap: "0.45rem", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", marginTop: "0.9rem", fontSize: "0.8rem", color: "#465766" }}>
                          <span>Submitted: {application.submittedDate}</span>
                          <span>Progress: {application.progress}%</span>
                          <span>Last Updated: {application.lastUpdated}</span>
                          <span>Action: <button type="button" style={{ color: "#156b48", fontWeight: 700 }} onClick={() => setSelectedAppId(application.applicationId)}>View</button></span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {selectedApplication && (
                    <div className="surface" style={{ marginTop: "1.2rem", padding: "1rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center" }}>
                        <div>
                          <h3 style={{ margin: 0 }}>{selectedApplication.service}</h3>
                          <small style={{ color: "#465766" }}>{selectedApplication.applicationId}</small>
                        </div>
                        <div>
                          <div style={{ fontSize: "0.8rem", color: "#465766" }}>Status: {selectedApplication.status}</div>
                          <div style={{ fontSize: "0.8rem", color: "#465766" }}>Progress: {selectedApplication.progress}%</div>
                        </div>
                      </div>

                      <div style={{ marginTop: "1rem", display: "flex", flexWrap: "wrap", gap: "0.8rem" }}>
                        {selectedApplication.timeline.map((step, index) => (
                          <div key={`${step.label}-${index}`} className={`citizen-timeline-stage ${step.completed ? "completed" : step.inProgress ? "in_progress" : "pending"}`}>
                            <span>{step.completed ? "Complete" : step.inProgress ? "In progress" : "Pending"}</span>
                            <strong style={{ fontSize: "0.8rem" }}>{step.label}</strong>
                            <small style={{ fontSize: "0.8rem", color: "#465766" }}>{step.date}</small>
                          </div>
                        ))}
                      </div>

                      <div style={{ marginTop: "1rem" }}>
                        <strong>Interdepartmental Activity</strong>
                        <ul style={{ marginTop: "0.7rem", display: "grid", gap: "0.45rem", color: "#465766", fontSize: "0.8rem" }}>
                          {selectedApplication.interdepartmentalEvents.map((event) => <li key={event}>• {event}</li>)}
                        </ul>
                      </div>
                    </div>
                  )}
                </>
              )}

              {page === "track" && (
                <>
                  <div className="citizen-welcome">
                    <div>
                      <span className="citizen-eyebrow">Track application</span>
                      <h1>Track Application</h1>
                    </div>
                  </div>
                  <div className="surface" style={{ padding: "1rem", marginTop: "1rem" }}>
                    <form onSubmit={handleTrackApplication} style={{ display: "flex", gap: "0.7rem", alignItems: "center", flexWrap: "wrap" }}>
                      <Input value={trackValue} onChange={(event) => { setTrackValue(event.target.value); setTrackedBackendApplication(null); }} placeholder="APP-2026-XXXX" aria-label="Application ID" style={{ maxWidth: "16rem" }} />
                      <Button type="submit">Track</Button>
                    </form>
                  </div>

                  {trackedBackendApplication && (
                    <div className="surface" style={{ marginTop: "1rem", padding: "1rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
                        <div>
                          <strong>{trackedBackendApplication.service_name ?? "Government service"}</strong>
                          <div style={{ color: "#465766", fontSize: "0.8rem" }}>{trackedBackendApplication.reference_id}</div>
                        </div>
                        <div className={`citizen-status ${getStatusClass(trackedBackendApplication.status)}`}>{trackedBackendApplication.status.replaceAll("_", " ")}</div>
                      </div>
                      <div className="application-timeline">
                        {(trackedBackendApplication.workflow ?? []).map((stage) => (
                          <div key={stage.key} className={`application-timeline-stage ${stage.status}`}>
                            <strong>{stage.label}</strong>
                            <span>{stage.status.replaceAll("_", " ")}</span>
                            <p>{stage.detail}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {!trackedBackendApplication && mockTrackedApplication && (
                    <div className="surface" style={{ marginTop: "1rem", padding: "1rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
                        <div>
                          <strong>{mockTrackedApplication.service}</strong>
                          <div style={{ color: "#465766", fontSize: "0.8rem" }}>{mockTrackedApplication.applicationId}</div>
                        </div>
                        <div className={`citizen-status ${getStatusClass(mockTrackedApplication.status)}`}>{mockTrackedApplication.status}</div>
                      </div>
                      <div style={{ display: "grid", gap: "0.6rem", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", marginTop: "1rem", fontSize: "0.8rem", color: "#465766" }}>
                        <span>Current department: {mockTrackedApplication.department}</span>
                        <span>Progress: {mockTrackedApplication.progress}%</span>
                        <span>Expected next step: {mockTrackedApplication.expectedNextStep}</span>
                        <span>Last updated: {mockTrackedApplication.lastUpdated}</span>
                        <span>Contact: {mockTrackedApplication.contact}</span>
                      </div>
                    </div>
                  )}
                </>
              )}

              {page === "records" && (
                <>
                  <div className="citizen-welcome">
                    <div>
                      <span className="citizen-eyebrow">Verified information</span>
                      <h1>Verified Records</h1>
                    </div>
                  </div>
                  <p style={{ marginTop: "0.8rem", color: "#465766" }}>Verified Records are information retrieved from connected government systems.</p>
                  <div style={{ display: "grid", gap: "1rem", marginTop: "1rem" }}>
                    {records.map((record) => (
                      <div key={record.id} className="surface" style={{ padding: "1rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
                          <div>
                            <strong>{record.name}</strong>
                            <p style={{ fontSize: "0.8rem", color: "#465766" }}>Source: {record.sourceDepartment}</p>
                          </div>
                          <span className="citizen-status success">Verified</span>
                        </div>
                        <div style={{ marginTop: "0.8rem", display: "grid", gap: "0.4rem", fontSize: "0.8rem", color: "#465766" }}>
                          <span>Last verified: {record.lastVerified}</span>
                          <span>Used for: {record.usedByApplications.join(", ")}</span>
                        </div>
                        <Button className="mt-3" variant="outline" size="sm">View Record</Button>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {page === "consent" && (
                <>
                  <div className="citizen-welcome">
                    <div>
                      <span className="citizen-eyebrow">Consent management</span>
                      <h1>Consent & Data Sharing</h1>
                    </div>
                  </div>
                  <p style={{ marginTop: "0.7rem", color: "#465766", fontSize: "0.8rem" }}>You control which connected government departments can access your verified records.</p>
                  <div style={{ display: "grid", gap: "1rem", marginTop: "1rem" }}>
                    {['Pending Requests', 'Active Permissions', 'Expired Permissions', 'Revoked Permissions'].map((label) => (
                      <div key={label} className="surface" style={{ padding: "1rem" }}>
                        <h3 style={{ margin: 0 }}>{label}</h3>
                        <div style={{ marginTop: "0.8rem", display: "grid", gap: "0.8rem" }}>
                          {consents.filter((consent) => {
                            if (label === "Pending Requests") return consent.status === "Awaiting Approval";
                            if (label === "Active Permissions") return consent.status === "Granted";
                            if (label === "Expired Permissions") return consent.status === "Expired";
                            return consent.status === "Revoked";
                          }).map((consent) => (
                            <div key={consent.id} style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap", padding: "0.8rem", border: "1px solid #e5eee8", borderRadius: "0.7rem" }}>
                              <div>
                                <strong>{consent.department}</strong>
                                <p style={{ fontSize: "0.8rem", color: "#465766" }}>Data: {consent.data}</p>
                                <p style={{ fontSize: "0.8rem", color: "#465766" }}>Purpose: {consent.purpose}</p>
                              </div>
                              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                                <span className={`citizen-status ${consent.status === "Awaiting Approval" ? "warning" : consent.status === "Granted" ? "success" : "danger"}`}>{consent.status}</span>
                                {consent.status === "Awaiting Approval" ? (
                                  <>
                                    <Button size="sm" variant="outline" onClick={() => handleConsentAction(consent.id, "approve")}>Approve</Button>
                                    <Button size="sm" variant="ghost" onClick={() => handleConsentAction(consent.id, "reject")}>Reject</Button>
                                  </>
                                ) : (
                                  <Button size="sm" variant="outline" onClick={() => handleConsentAction(consent.id, "revoke")}>Revoke</Button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {page === "notifications" && (
                <>
                  <div className="citizen-welcome">
                    <div>
                      <span className="citizen-eyebrow">Notification center</span>
                      <h1>Notifications</h1>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem", flexWrap: "wrap" }}>
                    {['All', 'Applications', 'Consent', 'Documents', 'System'].map((filter) => (
                      <button key={filter} type="button" className="citizen-status info" style={{ border: "1px solid #dfeae3", cursor: "pointer" }}>{filter}</button>
                    ))}
                  </div>
                  <div style={{ display: "grid", gap: "0.8rem", marginTop: "1rem" }}>
                    {filteredNotifications.map((notification) => (
                      <div key={notification.id} className="surface" style={{ padding: "1rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center" }}>
                          <div>
                            <strong>{notification.title}</strong>
                            <p style={{ fontSize: "0.8rem", color: "#465766" }}>{notification.description}</p>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <div style={{ fontSize: "0.8rem", color: "#465766" }}>{notification.time}</div>
                            <div className={`citizen-status ${notification.read ? "success" : "warning"}`}>{notification.read ? "Read" : "Unread"}</div>
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: "0.6rem", marginTop: "0.8rem", flexWrap: "wrap" }}>
                          {!notification.read && <Button size="sm" onClick={() => markAsRead(notification.id)}>Review</Button>}
                          {notification.relatedApplication && <span style={{ fontSize: "0.8rem", color: "#465766" }}>Related: {notification.relatedApplication}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {page === "grievances" && (
                <>
                  <div className="citizen-welcome">
                    <div>
                      <span className="citizen-eyebrow">Support request</span>
                      <h1>Grievances & Support</h1>
                    </div>
                  </div>
                  <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "1.2fr 0.8fr", marginTop: "1rem" }}>
                    <form className="surface" style={{ padding: "1rem" }} onSubmit={handleGrievanceSubmit}>
                      <h3>Raise a Grievance</h3>
                      <div style={{ display: "grid", gap: "0.8rem", marginTop: "0.9rem" }}>
                        <div><label>Category</label><Input value={grievanceForm.category} onChange={(event) => setGrievanceForm((current) => ({ ...current, category: event.target.value }))} /></div>
                        <div><label>Related Application</label><Input value={grievanceForm.relatedApplication} onChange={(event) => setGrievanceForm((current) => ({ ...current, relatedApplication: event.target.value }))} /></div>
                        <div><label>Department</label><Input value={grievanceForm.department} onChange={(event) => setGrievanceForm((current) => ({ ...current, department: event.target.value }))} /></div>
                        <div><label>Priority</label><Input value={grievanceForm.priority} onChange={(event) => setGrievanceForm((current) => ({ ...current, priority: event.target.value }))} /></div>
                        <div><label>Description</label><textarea value={grievanceForm.description} onChange={(event) => setGrievanceForm((current) => ({ ...current, description: event.target.value }))} style={{ width: "100%", minHeight: "120px", border: "1px solid #dfeae3", borderRadius: "0.7rem", padding: "0.8rem" }} /></div>
                        <div><label>Attachments</label><Input type="file" /></div>
                        <Button type="submit">Submit Grievance</Button>
                      </div>
                    </form>

                    <div className="surface" style={{ padding: "1rem" }}>
                      <h3>Support</h3>
                      <div style={{ display: "grid", gap: "0.7rem", marginTop: "0.9rem" }}>
                        <button type="button" className="citizen-status info" style={{ width: "100%", border: "1px solid #dfeae3" }}>Track Grievance</button>
                        <button type="button" className="citizen-status info" style={{ width: "100%", border: "1px solid #dfeae3" }}>FAQs</button>
                        <button type="button" className="citizen-status info" style={{ width: "100%", border: "1px solid #dfeae3" }}>Contact Department</button>
                        <button type="button" className="citizen-status info" style={{ width: "100%", border: "1px solid #dfeae3" }}>Help Center</button>
                      </div>
                    </div>
                  </div>

                  <div style={{ marginTop: "1rem", display: "grid", gap: "0.8rem" }}>
                    {grievances.map((entry) => (
                      <div key={entry.id} className="surface" style={{ padding: "1rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
                          <div>
                            <strong>{entry.id}</strong>
                            <div style={{ fontSize: "0.8rem", color: "#465766" }}>{entry.category} · {entry.department}</div>
                          </div>
                          <span className={`citizen-status ${entry.status === "Submitted" ? "info" : entry.status === "Resolved" || entry.status === "Closed" ? "success" : "warning"}`}>{entry.status}</span>
                        </div>
                        <p style={{ marginTop: "0.7rem", color: "#465766" }}>{entry.description}</p>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {page === "profile" && (
                <>
                  <div className="citizen-welcome">
                    <div>
                      <span className="citizen-eyebrow">Profile</span>
                      <h1>Citizen Profile</h1>
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem", marginTop: "1rem" }}>
                    <div className="surface" style={{ padding: "1rem" }}>
                      <h3>Personal Information</h3>
                      <div style={{ marginTop: "0.8rem", display: "grid", gap: "0.5rem", fontSize: "0.8rem", color: "#465766" }}>
                        <span>Citizen ID: {profile.citizenId}</span>
                        <span>Name: {profile.fullName}</span>
                        <span>Preferred language: {profile.preferredLanguage}</span>
                      </div>
                    </div>
                    <div className="surface" style={{ padding: "1rem" }}>
                      <h3>Contact Information</h3>
                      <div style={{ marginTop: "0.8rem", display: "grid", gap: "0.5rem", fontSize: "0.8rem", color: "#465766" }}>
                        <span>Verified mobile: {profile.verifiedMobile ? "Yes" : "No"}</span>
                        <span>Verified email: {profile.verifiedEmail ? "Yes" : "No"}</span>
                        <span>{profile.phone}</span>
                        <span>{profile.email}</span>
                      </div>
                    </div>
                    <div className="surface" style={{ padding: "1rem" }}>
                      <h3>Address</h3>
                      <p style={{ marginTop: "0.8rem", color: "#465766", fontSize: "0.8rem" }}>{profile.address}</p>
                    </div>
                    <div className="surface" style={{ padding: "1rem" }}>
                      <h3>Security</h3>
                      <div style={{ marginTop: "0.8rem", display: "grid", gap: "0.5rem", fontSize: "0.8rem", color: "#465766" }}>
                        <span>Change password</span>
                        <span>Two-factor authentication</span>
                        <span>Active sessions</span>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export function CitizenPortalPage({ page }: { page: CitizenPage }) { return <CitizenPortalApp page={page} />; }
