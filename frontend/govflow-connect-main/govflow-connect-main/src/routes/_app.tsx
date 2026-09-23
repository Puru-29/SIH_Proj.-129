import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell } from "@/components/govflow/shell";
import { useGovFlow } from "@/lib/govflow/store";

export const Route = createFileRoute("/_app")({
  component: AppLayout,
});

function AppLayout() {
  const { user, ready } = useGovFlow();
  const navigate = useNavigate();

  useEffect(() => {
    if (ready && !user) navigate({ to: "/login", replace: true });
    if (ready && user?.role === "Citizen") navigate({ to: "/citizen", replace: true });
  }, [ready, user, navigate]);

  if (!ready || !user) {
    return (
      <div className="grid min-h-screen place-items-center bg-background">
        <p className="text-sm text-muted-foreground">Verifying session…</p>
      </div>
    );
  }

  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
