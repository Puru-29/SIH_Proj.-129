import { createFileRoute, Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { CitizenPortal as RedesignedCitizenPortal } from "@/components/govflow/citizen-portal";
import { useEffect, useState } from "react";
import { CheckCircle2, FilePlus2, Home, Landmark, Loader2, LogOut, Search, ShieldCheck, UserRound } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ServiceForm } from "@/components/govflow/service-form";
import { api, getStoredToken, type MeshApplication, type MeshService, type ServiceFormField, type ServiceFormSchema, type UserProfile } from "@/lib/api";

export const Route = createFileRoute("/citizen")({ component: CitizenPortalLayout });
type View = "apply" | "dashboard" | "profile";

function CitizenPortalLayout() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  return pathname === "/citizen" ? <RedesignedCitizenPortal /> : <Outlet />;
}

function CitizenPortal() {
  const navigate = useNavigate();
  const [view, setView] = useState<View>("apply");
  const [services, setServices] = useState<MeshService[]>([]);
  const [schema, setSchema] = useState<ServiceFormSchema | null>(null);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [applications, setApplications] = useState<MeshApplication[]>([]);
  const [selected, setSelected] = useState<MeshApplication | null>(null);
  const [trackingId, setTrackingId] = useState("");
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([api.getMe(), api.getServices()]).then(async ([user, loadedServices]) => {
      if (!active) return;
      if (!user) { navigate({ to: "/citizen/login", replace: true }); return; }
      if (user.role !== "citizen") { navigate({ to: "/dashboard", replace: true }); return; }
      setProfile(user);
      setServices(loadedServices);
      setValues({ full_name: user.full_name });
      const existingApplications = await api.getApplications({ citizen_id: user.id });
      setApplications(existingApplications);
      const portalVisitKey = `govflow-citizen-portal-visited-${user.id}`;
      if (existingApplications.length > 0 || window.localStorage.getItem(portalVisitKey)) {
        setView("dashboard");
      } else {
        window.localStorage.setItem(portalVisitKey, "true");
      }
      setReady(true);
    }).catch(() => { if (active) navigate({ to: "/citizen/login", replace: true }); });
    return () => { active = false; };
  }, [navigate]);

  const loadService = async (id: string) => {
    setError("");
    setSchema(null);
    if (!id) return;
    try {
      const loaded = await api.getServiceFormSchema(Number(id));
      setSchema(loaded);
      setValues((current) => {
        const allowed = new Set(loaded.fields.map((field) => field.id));
        return Object.fromEntries(Object.entries(current).filter(([key]) => allowed.has(key)));
      });
    } catch (requestError: any) { setError(requestError.message || "Unable to load this service form."); }
  };

  const updateField = (field: ServiceFormField, value: string | boolean) => setValues((current) => ({ ...current, [field.id]: value }));
  const progress = (item: MeshApplication) => item.workflow?.length ? Math.round((item.workflow.filter((stage) => ["completed", "recovered"].includes(stage.status)).length / item.workflow.length) * 100) : 0;
  const currentStage = (item: MeshApplication) => item.workflow?.find((stage) => !["completed", "recovered"].includes(stage.status))?.label || "Completed";
  const signOut = () => { api.logout(); navigate({ to: "/citizen/login" }); };
  const startApplication = () => { setSchema(null); setValues({ full_name: profile?.full_name || "" }); setError(""); setView("apply"); };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (!getStoredToken()) { navigate({ to: "/citizen/login" }); return; }
    if (!profile || !schema) { setError("Select a government service and complete its form."); return; }
    setLoading(true);
    try {
      const formData = Object.fromEntries(schema.fields.filter((field) => !field.visible_if || values[field.visible_if.field] === field.visible_if.equals).map((field) => [field.id, values[field.id]]).filter(([, value]) => value !== undefined && value !== ""));
      const created = await api.createApplication({ citizen_id: profile.id, service_id: schema.service_id, location: String(values["district"] || values["village_city"] || ""), form_data: formData as Record<string, string>, consent: true });
      setApplications((current) => [created, ...current]);
      setSelected(created);
      setView("dashboard");
      toast.success(`Application ${created.reference_id} submitted`);
    } catch (submitError: any) { setError(submitError.message || "Unable to submit application."); }
    finally { setLoading(false); }
  };

  const track = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!trackingId.trim()) return;
    try { setSelected(await api.trackApplication(trackingId.trim())); } catch (trackError: any) { setError(trackError.message || "Application not found."); }
  };

  const sidebar = <aside className="h-fit rounded-xl bg-sidebar p-3 text-sidebar-foreground"><p className="px-3 pb-3 text-xs font-semibold uppercase tracking-wide text-sidebar-foreground/60">Citizen account</p><div className="space-y-1"><button className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-semibold ${view === "dashboard" ? "bg-sidebar-accent text-sidebar-accent-foreground" : "text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"}`} onClick={() => setView("dashboard")}><Home className="size-4" />Dashboard</button><button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" onClick={startApplication}><FilePlus2 className="size-4" />Apply for a service</button><button className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-semibold ${view === "profile" ? "bg-sidebar-accent text-sidebar-accent-foreground" : "text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"}`} onClick={() => setView("profile")}><UserRound className="size-4" />Profile</button></div><div className="mt-4 border-t border-sidebar-border pt-3"><button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" onClick={signOut}><LogOut className="size-4" />Sign out</button></div></aside>;

  const applyPage = <div className="space-y-5"><div className="rounded-2xl border border-primary/15 bg-gradient-to-br from-primary/10 via-card to-card p-6 shadow-sm"><div className="flex items-start gap-4"><span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-sm"><FilePlus2 className="size-5" /></span><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Citizen services</p><h1 className="mt-1 text-2xl font-bold tracking-tight">Apply for a service</h1><p className="mt-1 max-w-xl text-sm leading-6 text-muted-foreground">Choose the service you need. We will show only the information required for that application.</p></div></div><div className="mt-5 grid gap-3 border-t border-border/70 pt-4 sm:grid-cols-3"><div className="flex gap-2 text-sm"><span className="font-bold text-primary">01</span><span><b className="font-semibold">Choose</b><br /><span className="text-xs text-muted-foreground">Select a service</span></span></div><div className="flex gap-2 text-sm"><span className="font-bold text-primary">02</span><span><b className="font-semibold">Complete</b><br /><span className="text-xs text-muted-foreground">Fill the guided form</span></span></div><div className="flex gap-2 text-sm"><span className="font-bold text-primary">03</span><span><b className="font-semibold">Track</b><br /><span className="text-xs text-muted-foreground">Follow every stage</span></span></div></div></div><Card className="overflow-hidden shadow-sm"><CardHeader className="border-b border-border/70 bg-muted/20"><div className="flex items-center justify-between gap-3"><div><CardTitle>{schema?.service_name || "Start your application"}</CardTitle><p className="mt-1 text-sm text-muted-foreground">Your information is used only to process this request.</p></div><ShieldCheck className="size-5 text-primary" /></div></CardHeader><CardContent className="pt-6"><form onSubmit={submit} className="space-y-5"><div className="rounded-xl border border-primary/20 bg-primary/5 p-4"><label className="text-sm font-semibold">What service do you need?</label><select className="mt-2 flex h-11 w-full rounded-lg border border-input bg-background px-3 text-sm shadow-sm" value={schema?.service_id ? String(schema.service_id) : ""} onChange={(event) => void loadService(event.target.value)}><option value="">Select a service</option>{services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}</select></div>{schema ? <ServiceForm schema={schema} values={values} onChange={updateField} /> : <div className="rounded-xl border border-dashed border-border px-4 py-8 text-center"><p className="text-sm font-medium">Choose a service to begin</p><p className="mt-1 text-xs text-muted-foreground">The right form will appear here automatically.</p></div>}{error ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p> : null}<Button type="submit" disabled={loading || !schema} className="h-11 px-5">{loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}Submit application</Button></form></CardContent></Card></div>;

  const dashboardPage = <div className="space-y-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-xl font-bold">Citizen dashboard</h1><p className="text-sm text-muted-foreground">Track your applications and verification progress.</p></div><Button onClick={startApplication}><FilePlus2 className="mr-2 size-4" />Apply for a new service</Button></div><div className="grid gap-4 sm:grid-cols-3"><Card><CardContent className="pt-5"><p className="text-xs text-muted-foreground">Total applications</p><p className="mt-1 text-2xl font-bold">{applications.length}</p></CardContent></Card><Card><CardContent className="pt-5"><p className="text-xs text-muted-foreground">In progress</p><p className="mt-1 text-2xl font-bold">{applications.filter((item) => !["approved", "rejected"].includes(item.status)).length}</p></CardContent></Card><Card><CardContent className="pt-5"><p className="text-xs text-muted-foreground">Account</p><p className="mt-1 text-2xl font-bold">Citizen</p></CardContent></Card></div><Card><CardHeader><CardTitle>My applications</CardTitle></CardHeader><CardContent><form onSubmit={track} className="mb-5 flex max-w-xl gap-2"><Input value={trackingId} onChange={(event) => setTrackingId(event.target.value)} placeholder="Track by application ID" /><Button size="icon" type="submit" aria-label="Track application"><Search className="size-4" /></Button></form>{error ? <p className="mb-4 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p> : null}{applications.length ? <div className="grid gap-4 md:grid-cols-2">{applications.map((item) => <button key={item.id} type="button" className={`rounded-lg border p-4 text-left hover:bg-muted ${selected?.id === item.id ? "border-primary bg-primary/5" : "border-border"}`} onClick={() => setSelected(item)}><div className="flex justify-between"><span className="font-semibold">{item.reference_id}</span><span className="text-xs capitalize text-muted-foreground">{item.status.replace("_", " ")}</span></div><p className="mt-1 text-sm text-muted-foreground">{item.service_name}</p><div className="mt-4 flex justify-between text-xs"><span>Current stage: {currentStage(item)}</span><span className="font-semibold text-primary">{progress(item)}%</span></div><div className="mt-2 h-2 rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${progress(item)}%` }} /></div></button>)}</div> : <p className="py-6 text-sm text-muted-foreground">No applications yet. Apply for a service to begin.</p>}{selected ? <div className="mt-6 border-t border-border pt-5"><div className="flex items-center gap-2 font-semibold"><CheckCircle2 className="size-5 text-emerald-600" />{selected.reference_id}</div><p className="text-sm text-muted-foreground">{selected.service_name}</p><div className="mt-3 space-y-2">{(selected.workflow || []).map((stage) => <div key={stage.key} className="flex justify-between rounded-md border border-border px-3 py-3 text-sm"><span>{stage.label}</span><span className="capitalize text-muted-foreground">{stage.status}</span></div>)}</div></div> : null}</CardContent></Card></div>;

  const profilePage = <Card><CardHeader><CardTitle>My profile</CardTitle><p className="text-sm text-muted-foreground">Your registered citizen details.</p></CardHeader><CardContent><dl className="grid gap-4 sm:grid-cols-2">{[["Full name", profile?.full_name], ["Email", profile?.email], ["Mobile number", profile?.phone || "Not added"], ["Aadhaar", profile?.aadhaar_last4 ? `Last 4 digits: ${profile.aadhaar_last4}` : "Not added"], ["Account type", "Citizen"]].map(([label, value]) => <div key={label} className="rounded-lg border border-border p-3"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 font-medium">{value}</dd></div>)}</dl></CardContent></Card>;

  return <main className="min-h-screen bg-[linear-gradient(135deg,hsl(var(--background)),hsl(var(--muted)/.45))] px-4 py-8 lg:px-10">{!ready ? <div className="grid min-h-96 place-items-center text-sm text-muted-foreground">Verifying citizen session...</div> : <div className="mx-auto max-w-6xl space-y-6"><header className="flex items-center justify-between rounded-2xl border border-border/80 bg-card/90 px-4 py-3 shadow-sm backdrop-blur"><div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-xl bg-sidebar-accent"><Landmark className="size-5 text-sidebar-primary" /></span><div><p className="text-lg leading-none font-bold">Gov<span className="text-primary">Flow</span></p><p className="mt-1 text-[10px] text-muted-foreground">Connected Government · Citizen Services</p></div></div><span className="rounded-full bg-muted px-3 py-1.5 text-sm text-muted-foreground">{profile?.full_name}</span></header>{view === "apply" ? <div className="mx-auto max-w-3xl">{applyPage}</div> : <div className="grid gap-6 lg:grid-cols-[220px_1fr]">{sidebar}<section className="min-w-0">{view === "dashboard" ? dashboardPage : profilePage}</section></div>}<p className="text-sm text-muted-foreground">Government Staff? <Link to="/login" className="font-semibold text-primary">Open GovFlow dashboard</Link></p></div>}</main>;
}
