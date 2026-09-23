import { Link } from "@tanstack/react-router";
import { Landmark, ShieldCheck, GitBranch, Activity } from "lucide-react";
import type { ComponentType, ReactNode } from "react";

const AUTH_POINTS: [ComponentType<{ className?: string }>, string][] = [
  [GitBranch, "Cross-department workflow orchestration with live telemetry"],
  [ShieldCheck, "Consent artefacts with purpose, expiry and revocation"],
  [Activity, "Interoperability monitoring across 18 connected systems"],
];

export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <aside className="hidden flex-col justify-between bg-navy p-10 text-navy-foreground lg:flex">
        <Link to="/" className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-sidebar-accent">
            <Landmark className="size-5 text-teal" />
          </div>
          <div>
            <p className="text-lg leading-none font-bold">
              Gov<span className="text-teal">Flow</span>
            </p>
            <p className="mt-1 text-[11px] text-navy-foreground/60">
              Connected Government · Stronger Citizens
            </p>
          </div>
        </Link>

        <div>
          <h2 className="font-display text-3xl leading-tight font-bold">
            One orchestration layer across every department, protocol and legacy system.
          </h2>
          <ul className="mt-8 space-y-4 text-sm text-navy-foreground/75">
            {AUTH_POINTS.map(([Icon, text]) => (
              <li key={text} className="flex items-start gap-3">
                <Icon className="mt-0.5 size-4 shrink-0 text-teal" />
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-navy-foreground/50">
          SIH 26129 · Demonstration build with mock data
        </p>
      </aside>

      <main className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-8 flex items-center gap-2 lg:hidden">
            <Landmark className="size-5 text-primary" />
            <span className="font-bold">GovFlow</span>
          </Link>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </main>
    </div>
  );
}
