import { cn } from "@/lib/utils";
import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import type { Health } from "@/lib/govflow/data";

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4 sm:flex sm:flex-wrap sm:items-center sm:justify-between">
      <div className="min-w-0">
        {eyebrow ? (
          <span className="inline-flex rounded-full bg-accent px-3 py-1 text-[11px] font-semibold tracking-[0.14em] text-[#184f42] uppercase">
            {eyebrow}
          </span>
        ) : null}
        <h1 className="mt-2 truncate text-[30px] font-bold tracking-[-0.04em] text-foreground sm:text-[32px]">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-1 max-w-2xl text-[14px] font-medium leading-6 text-[#465f6f]">{subtitle}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function Surface({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("surface min-w-0 p-5", className)}>{children}</div>;
}

export function StatCard({
  icon,
  label,
  value,
  delta,
  tone = "primary",
  to,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  delta?: string;
  tone?: "primary" | "teal" | "success" | "warning" | "danger";
  to?: "applications" | "exceptions" | "consent" | "data-mapping" | "reports";
}) {
  const tones: Record<string, string> = {
    primary: "bg-primary/10 text-primary",
    teal: "bg-teal/15 text-teal",
    success: "bg-success/15 text-success",
    warning: "bg-warning/20 text-warning",
    danger: "bg-danger/15 text-danger",
  };
  const content = (
    <div className="flex min-w-0 items-start gap-3">
      <div
        aria-hidden="true"
        className={cn("grid size-11 shrink-0 place-items-center rounded-xl", tones[tone])}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[26px] font-bold leading-none tracking-[-0.04em] text-foreground">
          {value}
        </p>
        <p className="mt-1 whitespace-normal text-[13px] font-semibold leading-5 text-[#4c5f6d]">
          {label}
        </p>
        {delta ? (
          <p className="mt-1 whitespace-normal text-[11px] font-semibold leading-4 text-success">
            {delta}
          </p>
        ) : null}
      </div>
    </div>
  );

  if (to) {
    const destinations: Record<NonNullable<typeof to>, string> = {
      applications: "applications",
      exceptions: "exceptions",
      consent: "consent requests",
      "data-mapping": "data verification",
      reports: "reports",
    };
    return (
      <Link
        to="/$feature"
        params={{ feature: to }}
        aria-label={`${label}: ${value}.${delta ? ` ${delta}.` : ""} Open ${destinations[to]}.`}
        className="surface group block min-w-0 p-4 transition-colors hover:border-primary/40 hover:bg-muted/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
      >
        {content}
      </Link>
    );
  }

  return <div className="surface min-w-0 p-4">{content}</div>;
}

const healthTone: Record<Health, string> = {
  Healthy: "bg-success/12 text-success border-success/25",
  Degraded: "bg-warning/15 text-warning border-warning/30",
  Down: "bg-danger/12 text-danger border-danger/25",
};

export function HealthPill({ health }: { health: Health }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[12px] font-semibold",
        healthTone[health],
      )}
    >
      <span className="size-1.5 rounded-full bg-current" />
      {health}
    </span>
  );
}

export function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    Completed: "bg-success/12 text-success border-success/25",
    Active: "bg-success/12 text-success border-success/25",
    Recovered: "bg-success/12 text-success border-success/25",
    Published: "bg-success/12 text-success border-success/25",
    Success: "bg-success/12 text-success border-success/25",
    "In Progress": "bg-primary/10 text-primary border-primary/25",
    Running: "bg-primary/10 text-primary border-primary/25",
    Pending: "bg-warning/15 text-warning border-warning/30",
    Review: "bg-warning/15 text-warning border-warning/30",
    Draft: "bg-warning/15 text-warning border-warning/30",
    Open: "bg-warning/15 text-warning border-warning/30",
    Escalated: "bg-danger/12 text-danger border-danger/25",
    Failed: "bg-danger/12 text-danger border-danger/25",
    Failure: "bg-danger/12 text-danger border-danger/25",
    Revoked: "bg-danger/12 text-danger border-danger/25",
    Suspended: "bg-danger/12 text-danger border-danger/25",
  };
  return (
    <span
      className={cn(
        "inline-flex rounded-full border px-2.5 py-1 text-[12px] font-semibold",
        map[status] ?? "bg-muted text-muted-foreground border-border",
      )}
    >
      {status}
    </span>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="surface grid place-items-center p-10 text-center">
      <p className="font-semibold text-[15px] text-foreground">{title}</p>
      {hint ? <p className="mt-1 text-[13px] leading-5 text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export function KeyValue({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2">
      {items.map(([k, v]) => (
        <div key={k} className="min-w-0">
          <dt className="text-[11px] font-semibold tracking-[0.12em] text-muted-foreground uppercase">
            {k}
          </dt>
          <dd className="mt-0.5 text-[14px] font-medium leading-6 text-foreground wrap-break-word">{v}</dd>
        </div>
      ))}
    </dl>
  );
}
