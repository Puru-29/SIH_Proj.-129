import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowRight,
  CheckCircle2,
  Database,
  Landmark,
  Layers3,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "GovFlow — One citizen experience. Multiple government systems." },
      {
        name: "description",
        content:
          "GovFlow connects existing government platforms through a common interoperability layer, enabling secure data exchange, consent-based access, workflow orchestration and unified application tracking.",
      },
      { property: "og:title", content: "GovFlow — Government Interoperability Platform" },
      {
        property: "og:description",
        content:
          "GovFlow connects existing government systems through a common interoperability layer so citizens move across services without repeated forms and fragmented workflows.",
      },
    ],
  }),
  component: Landing,
});

const capabilities = [
  { icon: Layers3, title: "Cross-System Data Integration", text: "Unify records from legacy and digital government systems into one connected citizen experience." },
  { icon: ShieldCheck, title: "Consent-Based Data Sharing", text: "Validate purpose, scope and expiry before exchanging records across departments." },
  { icon: Workflow, title: "Unified Application Tracking", text: "Follow one application across departments without losing context or re-submitting documents." },
  { icon: Workflow, title: "Workflow Orchestration", text: "Coordinate department actions, approvals and exceptions through a single orchestration layer." },
  { icon: Database, title: "AI Document Verification", text: "Match uploaded and existing records to reduce duplication, fraud and manual review delays." },
  { icon: CheckCircle2, title: "Interoperability Monitoring", text: "Track system health, audit flows and consent events across the connected network." },
];

const problemPoints = [
  "Multiple portals",
  "Repeated information",
  "Repeated documents",
  "Fragmented tracking",
  "Disconnected workflows",
];

const steps = [
  "Existing Systems",
  "Connectors",
  "Data Normalization",
  "Consent",
  "Validation",
  "Workflow",
  "Audit & Monitoring",
  "Unified Citizen Experience",
];

function Landing() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b border-border bg-background/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <Landmark className="size-5" />
            </div>
            <div>
              <p className="text-lg font-bold leading-none tracking-tight text-foreground">
                Gov<span className="text-primary">Flow</span>
              </p>
              <p className="text-[11px] font-medium text-[#4b5f6f]">Government interoperability platform</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" asChild>
              <Link to="/login">Sign in</Link>
            </Button>
          </div>
        </div>
      </header>

      <main>
        <section className="border-b border-border bg-background">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 lg:grid-cols-[1.2fr_0.8fr] lg:py-20">
            <div>
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#0c4f40]">
                <Sparkles className="size-3.5" />
                Government Interoperability Layer
              </div>

              <h1 className="max-w-2xl text-4xl font-bold leading-[1.08] tracking-[-0.06em] text-foreground sm:text-5xl lg:text-[64px]">
                One citizen experience.
                <span className="mt-2 block text-primary">Multiple government systems.</span>
                <span className="mt-2 block text-secondary">One interoperability layer.</span>
              </h1>

              <p className="mt-6 max-w-xl text-base font-medium leading-7 text-[#475f6f] sm:text-lg">
                GovFlow connects existing government platforms through a common interoperability layer, enabling secure data exchange, consent-based access, workflow orchestration and unified application tracking.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Button size="lg" asChild>
                  <Link to="/citizen/login">
                    Explore Citizen Portal
                    <ArrowRight className="ml-2 size-4" />
                  </Link>
                </Button>
                <Button size="lg" variant="outline" asChild>
                  <Link to="/login">Explore Government Operations</Link>
                </Button>
              </div>

              <div className="mt-8 flex flex-wrap gap-3 text-xs font-medium text-[#425a6c]">
                <span className="rounded-full border border-border bg-card px-3 py-1.5">Connected public services</span>
                <span className="rounded-full border border-border bg-card px-3 py-1.5">Secure data exchange</span>
              </div>
            </div>

            <div className="rounded-[28px] border border-border bg-card p-5 shadow-[0_12px_30px_rgba(20,33,61,0.06)]">
              <div className="rounded-[24px] border border-border bg-[#F5FAF7] p-5">
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#446075]">Architecture</p>
                    <p className="mt-1 text-xl font-bold text-foreground">GovFlow Mesh</p>
                  </div>
                  <div className="rounded-full bg-primary/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#0d4e40]">
                    Active network
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-primary/20 bg-white p-3 text-center">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Citizen</p>
                  </div>
                  <div className="flex justify-center">
                    <ArrowRight className="size-4 text-primary" />
                  </div>
                  <div className="rounded-2xl border border-primary/20 bg-primary px-3 py-3 text-center text-primary-foreground shadow-sm">
                    <p className="text-sm font-bold tracking-[0.12em] uppercase">GovFlow</p>
                  </div>
                  <div className="flex justify-center">
                    <ArrowRight className="size-4 text-primary" />
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {[
                      "Revenue",
                      "Education",
                      "Transport",
                      "Municipal",
                      "Social Welfare",
                      "Employment",
                    ].map((department) => (
                      <div key={department} className="rounded-xl border border-border bg-white px-2.5 py-2 text-center text-xs font-medium text-foreground">
                        {department}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16">
          <div className="mb-8 max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">The Problem</p>
            <h2 className="mt-3 text-3xl font-bold tracking-[-0.05em] text-foreground">Fragmented public service delivery slows citizens down.</h2>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {problemPoints.map((point) => (
              <div key={point} className="rounded-2xl border border-border bg-card p-4 text-sm font-medium text-foreground shadow-sm">
                <div className="mb-3 inline-flex size-9 items-center justify-center rounded-full bg-primary/8 text-primary">
                  <CheckCircle2 className="size-4" />
                </div>
                <p>{point}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="border-y border-border bg-[#F0F6F3]">
          <div className="mx-auto max-w-6xl px-4 py-16">
            <div className="mb-8 max-w-2xl">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#0d4e40]">How GovFlow Works</p>
              <h2 className="mt-3 text-3xl font-bold tracking-[-0.05em] text-foreground">One connected workflow from existing systems to a unified citizen journey.</h2>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3">
              {steps.map((step, index) => (
                <div key={step} className="flex items-center gap-3">
                  <div className="rounded-full border border-border bg-white px-4 py-2 text-center text-xs font-semibold text-foreground shadow-sm">
                    {step}
                  </div>
                  {index < steps.length - 1 ? <ArrowRight className="size-4 text-primary" /> : null}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16">
          <div className="mb-8 max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#0d4e40]">Capabilities</p>
            <h2 className="mt-3 text-3xl font-bold tracking-[-0.05em] text-foreground">Built to connect public services without replacing existing systems.</h2>
          </div>

          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {capabilities.map(({ icon: Icon, title, text }) => (
              <div key={title} className="rounded-[24px] border border-border bg-card p-5 shadow-[0_8px_24px_rgba(20,33,61,0.04)]">
                <div className="mb-4 inline-flex size-12 items-center justify-center rounded-2xl bg-primary/8 text-primary">
                  <Icon className="size-5" />
                </div>
                <h3 className="text-lg font-bold text-foreground">{title}</h3>
                <p className="mt-2 text-sm font-medium leading-6 text-[#4a5f70]">{text}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-6 text-sm font-medium text-[#465d6c] sm:flex-row sm:items-center sm:justify-between">
          <p>GovFlow connects citizen services through secure, consent-based interoperability.</p>
          <p>Public sector coordination and service visibility.</p>
        </div>
      </footer>
    </div>
  );
}
