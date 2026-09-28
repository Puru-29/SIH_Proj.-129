import { createFileRoute } from "@tanstack/react-router";
import { CitizenPortalPage, type CitizenPage } from "@/components/govflow/citizen-portal-v2";

export const Route = createFileRoute("/citizen/$page")({
  component: CitizenDynamicPage,
});

function CitizenDynamicPage() {
  const { page } = Route.useParams();
  const validPages: CitizenPage[] = [
    "dashboard",
    "apply",
    "services",
    "applications",
    "track",
    "records",
    "consent",
    "notifications",
    "grievances",
    "profile",
  ];

  const safePage = validPages.includes(page as CitizenPage) ? (page as CitizenPage) : "dashboard";
  return <CitizenPortalPage page={safePage} />;
}
