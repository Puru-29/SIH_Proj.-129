import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  Bell,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  ClipboardList,
  FileCheck2,
  FilePlus2,
  GraduationCap,
  HandCoins,
  Home,
  Landmark,
  Leaf,
  Loader2,
  LogOut,
  Menu,
  Search,
  ShieldCheck,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ServiceForm } from "@/components/govflow/service-form";
import {
  api,
  getStoredToken,
  type MeshApplication,
  type MeshService,
  type ServiceFormField,
  type ServiceFormSchema,
  type UserProfile,
} from "@/lib/api";

type View = "apply" | "dashboard" | "profile";
type IconType = typeof GraduationCap;

const SERVICE_UI: Record<string, { description: string; icon: IconType; tone: string }> = {
  "Pre-Matric Scholarship": {
    description: "Support for school students and their education.",
    icon: GraduationCap,
    tone: "mint",
  },
  "Post-Matric Scholarship": {
    description: "Financial support for higher education.",
    icon: GraduationCap,
    tone: "orange",
  },
  "Farmer Assistance": {
    description: "Benefits and support for farming families.",
    icon: Leaf,
    tone: "green",
  },
  "Direct Benefit Subsidy": {
    description: "Receive eligible government benefits directly.",
    icon: HandCoins,
    tone: "blue",
  },
  "Senior Citizen Pension": {
    description: "Apply for support in your retirement years.",
    icon: Users,
    tone: "purple",
  },
  "Residence Certificate": {
    description: "Get proof of your residential address.",
    icon: Home,
    tone: "sky",
  },
  "Income Certificate": {
    description: "Request an official income certificate.",
    icon: FileCheck2,
    tone: "rose",
  },
};
const FALLBACK_SERVICE_UI = {
  description: "Apply online for this government service.",
  icon: ClipboardList,
  tone: "mint",
};

export function CitizenPortal() {
  const navigate = useNavigate();
  const [view, setView] = useState<View>("apply");
  const [services, setServices] = useState<MeshService[]>([]);
  const [schema, setSchema] = useState<ServiceFormSchema | null>(null);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [applications, setApplications] = useState<MeshApplication[]>([]);
  const [selected, setSelected] = useState<MeshApplication | null>(null);
  const [trackingId, setTrackingId] = useState("");
  const [applicationSearch, setApplicationSearch] = useState("");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([api.getMe(), api.getServices()])
      .then(async ([user, loadedServices]) => {
        if (!active) return;
        if (!user) {
          navigate({ to: "/citizen/login", replace: true });
          return;
        }
        if (user.role !== "citizen") {
          navigate({ to: "/dashboard", replace: true });
          return;
        }
        setProfile(user);
        setServices(loadedServices);
        setValues({ full_name: user.full_name });
        const loadedApplications = await api.getApplications({ citizen_id: user.id });
        setApplications(loadedApplications);
        setSelected(loadedApplications[0] || null);
        const visitKey = `govflow-citizen-portal-visited-${user.id}`;
        if (loadedApplications.length || window.localStorage.getItem(visitKey))
          setView("dashboard");
        else window.localStorage.setItem(visitKey, "true");
        setReady(true);
      })
      .catch(() => {
        if (active) navigate({ to: "/citizen/login", replace: true });
      });
    return () => {
      active = false;
    };
  }, [navigate]);

  const loadService = async (id: string) => {
    setError("");
    setSchema(null);
    setView("apply");
    setMobileNavOpen(false);
    try {
      const loaded = await api.getServiceFormSchema(Number(id));
      setSchema(loaded);
      setValues((current) => {
        const allowed = new Set(loaded.fields.map((field) => field.id));
        return Object.fromEntries(Object.entries(current).filter(([key]) => allowed.has(key)));
      });
    } catch (requestError: any) {
      setError(requestError.message || "Unable to load this service form.");
    }
  };

  const progress = (item: MeshApplication) =>
    item.workflow?.length
      ? Math.round(
          (item.workflow.filter((stage) => ["completed", "recovered"].includes(stage.status))
            .length /
            item.workflow.length) *
            100,
        )
      : 0;
  const stage = (item: MeshApplication) =>
    item.workflow?.find((itemStage) => !["completed", "recovered"].includes(itemStage.status))
      ?.label || "Completed";
  const statusLabel = (status: string) =>
    ({
      submitted: "Submitted",
      under_review: "Under verification",
      approved: "Approved",
      rejected: "Rejected",
      draft: "Draft",
    })[status] || status.replaceAll("_", " ");
  const statusTone = (status: string) =>
    status === "approved"
      ? "success"
      : status === "rejected"
        ? "danger"
        : status === "submitted"
          ? "info"
          : "warning";
  const selectedApplication = selected || applications[0] || null;
  const submittedAadhaar = applications.find((item) => item.form_data?.["aadhaar_last4"])?.form_data
    ?.["aadhaar_last4"];
  const aadhaarLast4 = profile?.aadhaar_last4 || submittedAadhaar;
  const filteredApplications = useMemo(
    () =>
      applications.filter((item) =>
        `${item.reference_id} ${item.service_name || ""}`
          .toLowerCase()
          .includes(applicationSearch.toLowerCase()),
      ),
    [applications, applicationSearch],
  );
  const inProgress = applications.filter(
    (item) => !["approved", "rejected"].includes(item.status),
  ).length;
  const completed = applications.filter((item) => item.status === "approved").length;
  const actionRequired = applications.filter(
    (item) =>
      item.status === "rejected" ||
      item.workflow?.some((itemStage) => ["failed", "action_required"].includes(itemStage.status)),
  ).length;
  const closeNav = () => setMobileNavOpen(false);
  const openApplicationProgress = (candidate?: MeshApplication) => {
    const application = candidate || applications[0];
    if (!application) {
      toast.info("Submit an application to see its progress.");
      return;
    }
    setSelected(application);
    setTimeout(
      () =>
        document
          .getElementById("citizen-progress")
          ?.scrollIntoView({ behavior: "smooth", block: "center" }),
      0,
    );
  };
  const findApplicationAndOpen = (
    predicate: (item: MeshApplication) => boolean,
    message: string,
  ) => {
    const application = applications.find(predicate);
    if (application) openApplicationProgress(application);
    else toast.info(message);
  };
  const startApplication = () => {
    setSchema(null);
    setValues({ full_name: profile?.full_name || "" });
    setError("");
    setView("apply");
    closeNav();
  };
  const signOut = () => {
    api.logout();
    navigate({ to: "/citizen/login" });
  };
  const updateField = (field: ServiceFormField, value: string | boolean) =>
    setValues((current) => ({ ...current, [field.id]: value }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (!getStoredToken()) {
      navigate({ to: "/citizen/login" });
      return;
    }
    if (!profile || !schema) {
      setError("Select a government service and complete its form.");
      return;
    }
    setLoading(true);
    try {
      const formData = Object.fromEntries(
        schema.fields
          .filter(
            (field) =>
              !field.visible_if || values[field.visible_if.field] === field.visible_if.equals,
          )
          .map((field) => [field.id, values[field.id]])
          .filter(([, value]) => value !== undefined && value !== ""),
      );
      const created = await api.createApplication({
        citizen_id: profile.id,
        service_id: schema.service_id,
        location: String(values["district"] || values["village_city"] || ""),
        form_data: formData as Record<string, string>,
        consent: true,
      });
      setApplications((current) => [created, ...current]);
      setSelected(created);
      setView("dashboard");
      toast.success(`Application ${created.reference_id} submitted`);
    } catch (submitError: any) {
      setError(submitError.message || "Unable to submit application.");
    } finally {
      setLoading(false);
    }
  };

  const track = async (event: FormEvent) => {
    event.preventDefault();
    if (!trackingId.trim()) return;
    try {
      setSelected(await api.trackApplication(trackingId.trim()));
      setError("");
    } catch (trackError: any) {
      setError(trackError.message || "Application not found.");
    }
  };

  const navItems = [
    [
      "Dashboard",
      Home,
      () => {
        setView("dashboard");
        closeNav();
      },
      view === "dashboard",
    ],
    ["Apply for a Service", FilePlus2, startApplication, view === "apply"],
    [
      "My Applications",
      ClipboardList,
      () => {
        setView("dashboard");
        closeNav();
      },
      false,
    ],
    [
      "Track Application",
      Search,
      () => {
        setView("dashboard");
        closeNav();
        setTimeout(() => document.getElementById("citizen-track")?.focus(), 0);
      },
      false,
    ],
    ["Services", Landmark, startApplication, false],
    [
      "Profile",
      UserRound,
      () => {
        setView("profile");
        closeNav();
      },
      view === "profile",
    ],
  ] as const;

  const sidebar = (
    <aside className={`citizen-sidebar ${mobileNavOpen ? "is-open" : ""}`}>
      <div className="citizen-brand">
        <span className="citizen-brand-mark">
          <Landmark className="size-5" />
        </span>
        <div>
          <strong>
            Gov<span>Flow</span>
          </strong>
          <small>Citizen Portal</small>
          <em>Your Services, Simplified</em>
        </div>
        <button className="citizen-mobile-close" onClick={closeNav} aria-label="Close menu">
          <X className="size-5" />
        </button>
      </div>
      <nav className="citizen-nav">
        {navItems.map(([label, Icon, action, active]) => (
          <button key={label} className={active ? "is-active" : ""} onClick={action}>
            <Icon className="size-[17px]" />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="citizen-sidebar-footer">
        <div className="citizen-leaf-mark">
          <Leaf className="size-5" />
        </div>
        <p>
          One Citizen.
          <br />
          Many Services.
          <br />A Better Tomorrow.
        </p>
        <button onClick={signOut}>
          <LogOut className="size-4" />
          Sign out
        </button>
      </div>
    </aside>
  );

  const applyPage = (
    <div className="citizen-page citizen-apply-page">
      <div className="citizen-apply-hero">
        <div className="citizen-eyebrow">
          <FilePlus2 className="size-3.5" /> Citizen services
        </div>
        <h1>Apply for a service</h1>
        <p>
          Choose the service you need. We will show only the information required for that
          application.
        </p>
        <div className="citizen-steps">
          <span>
            <b>01</b>
            <strong>Choose</strong>
            <small>Select a service</small>
          </span>
          <span>
            <b>02</b>
            <strong>Complete</strong>
            <small>Fill the guided form</small>
          </span>
          <span>
            <b>03</b>
            <strong>Track</strong>
            <small>Follow every stage</small>
          </span>
        </div>
      </div>
      <Card className="citizen-form-card">
        <CardHeader>
          <div>
            <CardTitle>{schema?.service_name || "Start your application"}</CardTitle>
            <p>Your information is used only to process this request.</p>
          </div>
          <ShieldCheck className="size-5 text-primary" />
        </CardHeader>
        <CardContent>
          <form onSubmit={submit}>
            {!schema ? (
              <div className="citizen-service-picker">
                <div className="citizen-section-heading">
                  <div>
                    <h2>What service do you need?</h2>
                    <p>Select a service to begin your application.</p>
                  </div>
                  <span>{services.length} available</span>
                </div>
                <div className="citizen-service-grid">
                  {services.map((service) => {
                    const ui = SERVICE_UI[service.name] || FALLBACK_SERVICE_UI;
                    const Icon = ui.icon;
                    return (
                      <button
                        type="button"
                        key={service.id}
                        className="citizen-service-option"
                        onClick={() => void loadService(String(service.id))}
                      >
                        <span className={`citizen-service-icon ${ui.tone}`}>
                          <Icon className="size-5" />
                        </span>
                        <span>
                          <strong>{service.name}</strong>
                          <small>{ui.description}</small>
                        </span>
                        <ArrowRight className="ml-auto size-4" />
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <>
                <ServiceForm schema={schema} values={values} onChange={updateField} />
                <div className="citizen-form-actions">
                  <Button type="button" variant="outline" onClick={() => setSchema(null)}>
                    Choose another service
                  </Button>
                  <Button type="submit" disabled={loading}>
                    {loading ? (
                      <Loader2 className="mr-2 size-4 animate-spin" />
                    ) : (
                      <CheckCircle2 className="mr-2 size-4" />
                    )}
                    Submit application
                  </Button>
                </div>
              </>
            )}
            {error ? <p className="citizen-error">{error}</p> : null}
          </form>
        </CardContent>
      </Card>
    </div>
  );

  const workflow = selectedApplication?.workflow || [];
  const dashboardPage = (
    <div className="citizen-page">
      <div className="citizen-welcome">
        <div>
          <div className="citizen-eyebrow">Citizen portal</div>
          <h1>
            Good morning, {profile?.full_name?.split(" ")[0] || "there"}{" "}
            <span className="citizen-sun">☀</span>
          </h1>
          <p>Apply for government services and track your applications all in one place.</p>
        </div>
        <Button onClick={startApplication}>
          <FilePlus2 className="mr-2 size-4" />
          Apply for a new service
        </Button>
      </div>
      <div className="citizen-action-row">
        <button onClick={() => document.getElementById("citizen-track")?.focus()}>
          <Search className="size-4" />
          Track application
        </button>
        <button onClick={startApplication}>
          <Landmark className="size-4" />
          Explore services
        </button>
      </div>
      <div className="citizen-stat-grid">
        <StatCard
          label="Total Applications"
          value={applications.length}
          tone="mint"
          icon={ClipboardList}
          onClick={() => openApplicationProgress()}
        />
        <StatCard
          label="In Progress"
          value={inProgress}
          tone="orange"
          icon={Loader2}
          link="Track now"
          onClick={() => findApplicationAndOpen((item) => !["approved", "rejected"].includes(item.status), "There are no applications in progress.")}
        />
        <StatCard
          label="Completed"
          value={completed}
          tone="blue"
          icon={CheckCircle2}
          link="View certificates"
          onClick={() => findApplicationAndOpen((item) => item.status === "approved", "You do not have a completed application yet.")}
        />
        <StatCard
          label="Action Required"
          value={actionRequired}
          tone="rose"
          icon={CircleAlert}
          link="Check now"
          onClick={() => findApplicationAndOpen((item) => item.status === "rejected" || Boolean(item.workflow?.some((workflowStage) => ["failed", "action_required"].includes(workflowStage.status))), "There is no required action right now.")}
        />
      </div>
      <div className="citizen-dashboard-grid">
        <Card className="citizen-applications-card">
          <CardHeader>
            <div>
              <CardTitle>My Applications</CardTitle>
              <p>Keep an eye on your submitted services.</p>
            </div>
            <button onClick={() => setApplicationSearch("")}>
              View all <ArrowRight className="size-4" />
            </button>
          </CardHeader>
          <CardContent>
            <div className="citizen-search-row">
              <div className="citizen-search-input">
                <Search className="size-4" />
                <Input
                  value={applicationSearch}
                  onChange={(event) => setApplicationSearch(event.target.value)}
                  placeholder="Search by application ID or service name"
                />
              </div>
              <Button
                type="button"
                size="icon"
                onClick={() => document.getElementById("citizen-track")?.focus()}
                aria-label="Track application"
              >
                <Search className="size-4" />
              </Button>
            </div>
            {error ? <p className="citizen-error mb-4">{error}</p> : null}
            {filteredApplications.length ? (
              <div className="citizen-application-list">
                {filteredApplications.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`citizen-application-row ${selectedApplication?.id === item.id ? "is-selected" : ""}`}
                    onClick={() => openApplicationProgress(item)}
                  >
                    <div className="citizen-application-top">
                      <span>
                        <strong>{item.reference_id}</strong>
                        <small>{item.service_name || "Government service"}</small>
                      </span>
                      <StatusBadge status={item.status} label={statusLabel(item.status)} />
                    </div>
                    <div className="citizen-application-meta">
                      <span>
                        Current stage: <b>{stage(item)}</b>
                      </span>
                      <b>{progress(item)}%</b>
                    </div>
                    <div className="citizen-progress">
                      <span style={{ width: `${progress(item)}%` }} />
                    </div>
                    <small className="citizen-submitted">
                      <ClipboardList className="size-3.5" />
                      Submitted on{" "}
                      {new Date(item.created_at).toLocaleDateString("en-IN", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })}
                      <ArrowRight className="ml-auto size-4" />
                    </small>
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState onApply={startApplication} />
            )}
          </CardContent>
        </Card>
        <Card className="citizen-services-card">
          <CardHeader>
            <div>
              <CardTitle>Available Services</CardTitle>
              <p>Explore services made for you.</p>
            </div>
            <button onClick={startApplication}>
              View all <ArrowRight className="size-4" />
            </button>
          </CardHeader>
          <CardContent>
            <div className="citizen-available-list">
              {services.slice(0, 7).map((service) => {
                const ui = SERVICE_UI[service.name] || FALLBACK_SERVICE_UI;
                const Icon = ui.icon;
                return (
                  <button
                    key={service.id}
                    className="citizen-available-service"
                    onClick={() => void loadService(String(service.id))}
                  >
                    <span className={`citizen-service-icon ${ui.tone}`}>
                      <Icon className="size-4" />
                    </span>
                    <span>
                      <strong>{service.name}</strong>
                      <small>{ui.description}</small>
                    </span>
                    <ArrowRight className="ml-auto size-4" />
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
      <div className="citizen-lower-grid">
        <Card id="citizen-progress" className="citizen-progress-card">
          <CardHeader>
            <div>
              <CardTitle>Application Progress</CardTitle>
              <p>
                {selectedApplication
                  ? `${selectedApplication.reference_id} · ${selectedApplication.service_name || "Selected application"}`
                  : "Select an application to see its live status."}
              </p>
            </div>
            <StatusBadge
              status={selectedApplication?.status || "submitted"}
              label={
                selectedApplication ? statusLabel(selectedApplication.status) : "No application"
              }
            />
          </CardHeader>
          <CardContent>
            {selectedApplication && workflow.length ? (
              <div className="citizen-timeline">
                {workflow.map((item) => (
                  <div key={item.key} className={`citizen-timeline-stage ${item.status}`}>
                    <span>
                      {["completed", "recovered"].includes(item.status) ? (
                        <Check className="size-3.5" />
                      ) : item.status === "failed" || item.status === "action_required" ? (
                        <CircleAlert className="size-3.5" />
                      ) : (
                        <span />
                      )}
                    </span>
                    <strong>{item.label}</strong>
                    <small>
                      {item.status === "completed" || item.status === "recovered"
                        ? "Completed"
                        : item.status === "failed" || item.status === "action_required"
                          ? "Action required"
                          : item.status === "in_progress"
                            ? "In progress"
                            : "Pending"}
                    </small>
                  </div>
                ))}
              </div>
            ) : (
              <div className="citizen-empty-progress">
                <ClipboardList className="size-5" />
                <p>Select an application above to view its real verification progress.</p>
              </div>
            )}
          </CardContent>
        </Card>
        <Card className="citizen-track-card">
          <CardHeader>
            <div>
              <CardTitle>Track with Reference ID</CardTitle>
              <p>Enter your application ID to view status.</p>
            </div>
            <Search className="size-5 text-primary" />
          </CardHeader>
          <CardContent>
            <form onSubmit={track} className="citizen-track-form">
              <Input
                id="citizen-track"
                value={trackingId}
                onChange={(event) => setTrackingId(event.target.value)}
                placeholder="APP-2026-XXXXX"
              />
              <Button size="icon" type="submit" aria-label="Track application">
                <ArrowRight className="size-4" />
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
      <div className="citizen-help-grid">
        <ActionCard
          icon={CircleAlert}
          title="Need Help?"
          text="Get assistance with your applications"
          action="Visit Help Center"
          onClick={() => toast.info("Help Center is available for service guidance.")}
          tone="rose"
        />
        <ActionCard
          icon={FilePlus2}
          title="Check Eligibility"
          text="Find the services you are eligible for"
          action="Explore Services"
          onClick={startApplication}
          tone="orange"
        />
        <ActionCard
          icon={Search}
          title="Track with Reference ID"
          text="Enter your application ID to track status"
          action="Track application"
          onClick={() => document.getElementById("citizen-track")?.focus()}
          tone="mint"
        />
      </div>
    </div>
  );

  const profilePage = (
    <div className="citizen-page">
      <div className="citizen-welcome">
        <div>
          <div className="citizen-eyebrow">Your account</div>
          <h1>My profile</h1>
          <p>Keep your registered citizen details close at hand.</p>
        </div>
      </div>
      <Card className="citizen-profile-card">
        <CardHeader>
          <CardTitle>Registered details</CardTitle>
          <p>Your personal information is securely connected to your applications.</p>
        </CardHeader>
        <CardContent>
          <dl className="citizen-profile-grid">
            {[
              ["Full name", profile?.full_name],
              ["Email", profile?.email],
              ["Mobile number", profile?.phone || "Not added"],
              ["Aadhaar", aadhaarLast4 ? `Last 4 digits: ${aadhaarLast4}` : "Not added"],
              ["Account type", "Citizen"],
            ].map(([label, value]) => (
              <div key={label} className="citizen-profile-field">
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <main className="citizen-portal">
      <div className="citizen-portal-frame">
        {!ready ? (
          <div className="citizen-loading">
            <Loader2 className="size-5 animate-spin" />
            Verifying citizen session...
          </div>
        ) : (
          <>
            <button
              className="citizen-mobile-menu"
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="size-5" />
            </button>
            {mobileNavOpen ? (
              <button className="citizen-nav-overlay" onClick={closeNav} aria-label="Close menu" />
            ) : null}
            {sidebar}
            <div className="citizen-main">
              <header className="citizen-topbar">
                <div className="citizen-top-search">
                  <Search className="size-4" />
                  <span>Search services, applications, or help...</span>
                  <kbd>⌘ K</kbd>
                </div>
                <button
                  className="citizen-notification"
                  onClick={() => toast.info("You are all caught up.")}
                  aria-label="Notifications"
                >
                  <Bell className="size-5" />
                  <span>3</span>
                </button>
                <button className="citizen-profile-trigger" onClick={() => setView("profile")}>
                  <span>{profile?.full_name?.charAt(0) || "C"}</span>
                  <b>
                    {profile?.full_name || "Citizen"}
                    <small>Citizen</small>
                  </b>
                  <ChevronDown className="size-4" />
                </button>
              </header>
              <section className="citizen-content">
                {view === "apply" ? applyPage : view === "dashboard" ? dashboardPage : profilePage}
                <footer className="citizen-footer">
                  <span>One Citizen. Many Services. A Better Tomorrow.</span>
                  <div>
                    <button>Privacy</button>
                    <button>Terms</button>
                    <button
                      onClick={() => toast.info("Help Center is available for service guidance.")}
                    >
                      Help
                    </button>
                    <button>
                      English <ChevronDown className="size-3" />
                    </button>
                  </div>
                </footer>
              </section>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

function StatCard({
  label,
  value,
  tone,
  icon: Icon,
  link,
  onClick,
}: {
  label: string;
  value: number;
  tone: string;
  icon: IconType;
  link?: string;
  onClick: () => void;
}) {
  return (
    <button type="button" className={`citizen-stat-card ${tone}`} onClick={onClick}>
      <span className="citizen-stat-icon">
        <Icon className="size-5" />
      </span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        {link ? (
          <small>
            {link} <ArrowRight className="size-3" />
          </small>
        ) : null}
      </div>
    </button>
  );
}
function StatusBadge({ status, label }: { status: string; label: string }) {
  return (
    <span
      className={`citizen-status ${status === "approved" ? "success" : status === "rejected" ? "danger" : status === "submitted" ? "info" : "warning"}`}
    >
      {label}
    </span>
  );
}
function EmptyState({ onApply }: { onApply: () => void }) {
  return (
    <div className="citizen-empty-state">
      <ClipboardList className="size-8" />
      <strong>No applications yet</strong>
      <p>Your submitted applications will appear here.</p>
      <Button onClick={onApply}>Explore services</Button>
    </div>
  );
}
function ActionCard({
  icon: Icon,
  title,
  text,
  action,
  onClick,
  tone,
}: {
  icon: IconType;
  title: string;
  text: string;
  action: string;
  onClick: () => void;
  tone: string;
}) {
  return (
    <div className="citizen-action-card">
      <span className={`citizen-service-icon ${tone}`}>
        <Icon className="size-5" />
      </span>
      <div>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
      <button onClick={onClick}>
        {action}
        <ArrowRight className="size-3.5" />
      </button>
    </div>
  );
}
