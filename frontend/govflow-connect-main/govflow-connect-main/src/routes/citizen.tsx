import { Outlet, createFileRoute, useLocation } from "@tanstack/react-router";
import { CitizenPortalPage } from "@/components/govflow/citizen-portal-v2";

export const Route = createFileRoute("/citizen")({
  component: CitizenRoot,
});

function CitizenRoot() {
  const location = useLocation();

  if (location.pathname === "/citizen") {
    return <CitizenPortalPage page="dashboard" />;
  }

  return <Outlet />;
}
