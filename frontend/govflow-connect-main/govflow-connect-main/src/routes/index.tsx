import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Activity,
  ArrowRight,
  Boxes,
  GitBranch,
  Landmark,
  RefreshCw,
  Route as RouteIcon,
  ShieldCheck,
  Shuffle,
  Sparkles,
  TerminalSquare,
  MapPin,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { WORKFLOWS } from "@/lib/govflow/data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "GovFlow — Connect Government Systems, Orchestrate Citizen Journeys" },
      {
        name: "description",
        content:
          "GovFlow is a government interoperability and workflow orchestration platform: visual cross-department workflows, universal schema mapping, automatic exception recovery and consent-first data sharing.",
      },
      { property: "og:title", content: "GovFlow — Government Interoperability Platform" },
      {
        property: "og:description",
        content:
          "Existing platforms provide access to services. GovFlow connects the systems behind them and orchestrates the complete journey.",
      },
    ],
  }),
  component: Landing,
});

const PILLARS = [
  {
    icon: GitBranch,
    title: "Visual Workflow Orchestrator",
    text: "Design and run cross-department workflows on a live canvas with stage-by-stage telemetry.",
  },
  {
    icon: Shuffle,
    title: "Universal Data Mapper",
    text: "REST/JSON, SOAP/XML and legacy flat files normalised into one canonical citizen schema.",
  },
  {
    icon: RefreshCw,
    title: "Automatic Exception Recovery",
    text: "Detect, retry, recover and continue — failures never dead-end a citizen application.",
  },
  {
    icon: RouteIcon,
    title: "Unified Citizen Journey",
    text: "One application ID reveals every department, system, consent and exception involved.",
  },
  {
    icon: ShieldCheck,
    title: "Consent-Centric Sharing",
    text: "Purpose, scope, recipient, expiry and revocation recorded as signed consent artefacts.",
  },
  {
    icon: Activity,
    title: "Interoperability Monitoring",
    text: "Health, latency, success rate and uptime across every connected government system.",
  },
  {
    icon: MapPin,
    title: "Location-Aware Governance",
    text: "Country → State → District → City scoping reshapes every dashboard and report.",
  },
  {
    icon: TerminalSquare,
    title: "Developer Workspace",
    text: "Endpoints, schemas, auth, request/response previews and integration logs in one console.",
  },
];

function Landing() {
  const stages = WORKFLOWS[0]!.stages;
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-30 border-b border-border bg-card/85 backdrop-blur">
        <div className="mx-auto grid max-w-6xl grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-navy">
              <Landmark className="size-5 text-teal" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-lg leading-none font-bold">
                Gov<span className="text-teal">Flow</span>
              </p>
              <p className="truncate text-[11px] text-muted-foreground">
                SIH 26129 · Interoperability Platform
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button variant="ghost" asChild className="hidden sm:inline-flex">
              <Link to="/login">Sign in</Link>
            </Button>
            <Button asChild>
              <Link to="/signup">Get started</Link>
            </Button>
          </div>
        </div>
      </header>

      <section className="hero-mesh border-b border-border">
        <div className="mx-auto max-w-6xl px-4 py-16 lg:py-24">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-[11px] font-semibold tracking-[0.14em] uppercase">
            <Sparkles className="size-3.5 text-teal" /> Government Interoperability Platform
          </span>
          <h1 className="font-display mt-5 max-w-3xl text-4xl leading-[1.05] font-bold tracking-tight sm:text-6xl">
            Existing portals give access to services. GovFlow connects the systems behind them.
          </h1>
          <p className="mt-5 max-w-2xl text-base text-muted-foreground sm:text-lg">
            A single orchestration layer across departments, protocols and legacy systems — with
            consent, recovery and full traceability for every citizen journey.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button size="lg" asChild>
              <Link to="/login">
                Launch the live demo <ArrowRight className="ml-2 size-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link to="/signup">Create an officer account</Link>
            </Button>
          </div>

          <div className="surface mt-12 overflow-x-auto p-5">
            <p className="text-xs font-semibold tracking-[0.14em] text-muted-foreground uppercase">
              Scholarship application · live orchestration path
            </p>
            <div className="mt-4 flex min-w-max items-center gap-2">
              {stages.map((s, i) => (
                <div key={s.id} className="flex items-center gap-2">
                  <div className="w-32 rounded-xl border border-border bg-card p-3">
                    <p className="text-xs leading-tight font-semibold">{s.name}</p>
                    <p className="mt-1 truncate text-[10px] text-muted-foreground">
                      {s.department}
                    </p>
                  </div>
                  {i < stages.length - 1 ? <span className="h-px w-5 bg-border" /> : null}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
          Eight capabilities no portal offers together
        </h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((p) => (
            <div key={p.title} className="surface p-5">
              <div className="grid size-10 place-items-center rounded-xl bg-accent">
                <p.icon className="size-5 text-accent-foreground" />
              </div>
              <h3 className="mt-4 text-sm font-bold">{p.title}</h3>
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{p.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-y border-border bg-navy text-navy-foreground">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 py-14 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["24", "Active services orchestrated"],
            ["142", "Cross-department workflows"],
            ["98.7%", "API success rate"],
            ["18", "Departments connected"],
          ].map(([v, l]) => (
            <div key={l}>
              <p className="font-display text-4xl font-bold text-teal">{v}</p>
              <p className="mt-1 text-sm text-navy-foreground/70">{l}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <div className="surface flex flex-col items-start gap-5 p-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <h2 className="text-xl font-bold">
              See the scholarship journey recover from a live API failure
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Run the judging demo: nine stages, four departments, one automatic exception recovery.
            </p>
          </div>
          <Button size="lg" asChild>
            <Link to="/login">
              <Boxes className="mr-2 size-4" /> Open GovFlow
            </Link>
          </Button>
        </div>
      </section>

      <footer className="border-t border-border px-4 py-6 text-center text-xs text-muted-foreground">
        GovFlow · Smart India Hackathon problem statement 26129 · Mock data for demonstration
      </footer>
    </div>
  );
}
