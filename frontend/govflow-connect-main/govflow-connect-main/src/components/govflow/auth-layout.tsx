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
  variant = "staff",
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  variant?: "staff" | "citizen";
}) {
  const isCitizen = variant === "citizen";

  if (isCitizen) {
    return (
      <div className="min-h-screen bg-[#f5f7f4] px-4 py-8 sm:px-6 lg:px-8">
        <main className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-[560px] items-center justify-center">
          <div className="w-full">
            <Link to="/" className="mb-8 flex items-center justify-center gap-3">
              <div className="grid size-10 place-items-center rounded-lg bg-[#0d5a49]/10">
                <Landmark className="size-5 text-[#0d5a49]" />
              </div>
              <span className="text-[2rem] font-bold leading-none tracking-[-0.05em] text-[#1a2b3a]">
                GovFlow
              </span>
            </Link>

            <div className="text-center">
              <h1 className="text-[clamp(2.3rem,4vw,3.7rem)] font-extrabold tracking-[-0.06em] text-[#1a2b3a]">
                {title}
              </h1>
              <p className="mt-2 text-[1.05rem] font-medium text-[#4c5f6d]">{subtitle}</p>
            </div>

            <div className="mt-8">{children}</div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
      <aside className="hidden flex-col justify-between bg-[#13283d] p-10 text-white lg:flex">
        <Link to="/" className="flex items-center gap-3">
          <div className="grid size-11 place-items-center rounded-xl bg-white/5">
            <Landmark className="size-5 text-[#7ae0c9]" />
          </div>
          <div>
            <p className="text-[2rem] leading-none font-bold tracking-[-0.06em] text-white">
              Gov<span className="text-[#7ae0c9]">Flow</span>
            </p>
            <p className="mt-2 text-[0.9rem] font-medium text-white/70">
              Connected Government · Stronger Citizens
            </p>
          </div>
        </Link>

        <div>
          <h2 className="max-w-[620px] text-[3.2rem] leading-[1.06] font-extrabold tracking-[-0.06em] text-white">
            One orchestration layer across every department, protocol and legacy system.
          </h2>
          <ul className="mt-8 space-y-5 text-[1.1rem] font-medium leading-7 text-white/80">
            {AUTH_POINTS.map(([Icon, text]) => (
              <li key={text} className="flex items-start gap-3">
                <Icon className="mt-1 size-4 shrink-0 text-[#7ae0c9]" />
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-[0.95rem] font-medium text-white/70">Secure public service coordination</p>
      </aside>

      <main className="flex items-center justify-center bg-[#f5f7f4] px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full max-w-[560px]">
          <Link to="/" className="mb-8 flex items-center gap-2 lg:hidden">
            <Landmark className="size-5 text-primary" />
            <span className="text-[2rem] font-bold tracking-[-0.05em] text-[#1c2a36]">GovFlow</span>
          </Link>
          <h1 className="text-[clamp(2.3rem,3.2vw,4rem)] font-extrabold tracking-[-0.06em] text-[#1c2a36]">{title}</h1>
          <p className="mt-2 text-[1.05rem] font-medium text-[#4c5f6d]">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </main>
    </div>
  );
}
