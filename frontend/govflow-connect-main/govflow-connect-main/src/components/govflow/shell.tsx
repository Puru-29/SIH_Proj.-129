import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Activity,
  Bell,
  Boxes,
  Building2,
  ChevronDown,
  FileStack,
  FileText,
  GitBranch,
  Landmark,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  Settings,
  Shield,
  ShieldCheck,
  Shuffle,
  TriangleAlert,
  User,
  Users,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { useGovFlow } from "@/lib/govflow/store";
const NAV = [
  {
    group: "Overview",
    items: [{ to: "dashboard", label: "Overview", icon: LayoutDashboard }],
  },
  {
    group: "Operations",
    items: [{ to: "applications", label: "Applications", icon: FileStack }],
  },
  {
    group: "Interoperability",
    items: [
      { to: "monitoring", label: "Interoperability Hub", icon: Activity },
      { to: "integrations", label: "Connected Systems", icon: Boxes },
      { to: "consent", label: "Consent Requests", icon: ShieldCheck },
    ],
  },
  {
    group: "Execution",
    items: [
      { to: "workflows", label: "Workflows", icon: GitBranch },
      { to: "data-mapping", label: "Data & Verification", icon: Shuffle },
      { to: "exceptions", label: "Exceptions", icon: TriangleAlert },
    ],
  },
  {
    group: "Trust & Governance",
    items: [
      { to: "audit-logs", label: "Audit Trail", icon: FileText },
      { to: "ai-document-verification", label: "AI Document Verification", icon: ShieldCheck },
      { to: "settings", label: "Profile / Settings", icon: Settings },
    ],
  },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const {
    user,
    signOut,
    notifications,
    markAllRead,
    markRead,
    applications,
    workflows,
    integrations,
    services,
    departments,
    users,
  } = useGovFlow();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [open, setOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const unread = notifications.filter((n) => !n.read).length;

  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setSearchOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const results = useMemo(
    () => ({
      applications: applications.slice(0, 30),
      services,
      departments,
      workflows,
      integrations,
      users,
    }),
    [applications, departments, integrations, services, users, workflows],
  );

  const goFeature = (feature: string) => {
    setSearchOpen(false);
    navigate({ to: "/$feature", params: { feature } });
  };

  const goDetail = (feature: string, id: string) => {
    setSearchOpen(false);
    if (feature === "applications") {
      const application = applications.find((item) => item.id === id);
      if (application?.backendId) {
        navigate({ to: "/applications/$id", params: { id: String(application.backendId) } });
        return;
      }
    }
    navigate({ to: "/$feature/$id", params: { feature, id } });
  };

  return (
    <div className="flex min-h-screen w-full bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-65 flex-col overflow-hidden bg-sidebar text-sidebar-foreground transition-transform lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center gap-3 border-b border-sidebar-border px-5 py-5">
          <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-sidebar-accent">
            <Landmark className="size-5 text-sidebar-primary" />
          </div>
          <div className="min-w-0">
            <p className="text-lg leading-none font-bold text-sidebar-foreground">
              Gov<span className="text-sidebar-primary">Flow</span>
            </p>
            <p className="mt-1 text-[10px] font-medium leading-tight text-[#4f6473]">
              Connected Government · Stronger Citizens
            </p>
          </div>
          <button
            className="ml-auto lg:hidden"
            onClick={() => setOpen(false)}
            aria-label="Close menu"
          >
            <X className="size-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
          {NAV.map((group) => (
            <div key={group.group} className="space-y-1">
              <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#50657a]">
                {group.group}
              </p>
              {group.items.map((item) => (
                <Link
                  key={`${group.group}-${item.label}`}
                  to={item.to === "dashboard" ? "/dashboard" : "/$feature"}
                  params={item.to === "dashboard" ? {} : { feature: item.to }}
                  className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-sidebar-foreground/75 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground data-[status=active]:bg-sidebar-accent data-[status=active]:text-sidebar-accent-foreground"
                  activeProps={{ className: "bg-sidebar-accent text-sidebar-accent-foreground" }}
                >
                  <item.icon className="size-4.5 shrink-0" />
                  <span className="truncate">{item.label}</span>
                </Link>
              ))}
            </div>
          ))}
        </nav>

        <div className="border-t border-sidebar-border px-5 py-4 text-xs font-medium text-[#4b5f6f]">
          One Government. Connected for a Better Tomorrow.
        </div>
      </aside>

      {open ? (
        <button
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          aria-label="Close navigation overlay"
          onClick={() => setOpen(false)}
        />
      ) : null}

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col lg:ml-65">
        <header className="sticky top-0 z-30 grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-b border-border bg-card/85 px-4 py-3 backdrop-blur lg:px-6">
          <button className="lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu className="size-5" />
          </button>
          <button
            onClick={() => setSearchOpen(true)}
            className="hidden min-w-0 items-center gap-2 rounded-xl border border-border bg-muted/50 px-3 py-2 text-sm font-medium text-[#355067] transition-colors hover:bg-muted sm:flex sm:w-full sm:max-w-md"
          >
            <Search className="size-4 shrink-0" />
            <span className="truncate">Search services, departments, workflows…</span>
            <kbd className="ml-auto hidden shrink-0 rounded border border-border px-1.5 text-[10px] md:block">
              ⌘K
            </kbd>
          </button>
          <span className="sm:hidden" />

          <div className="flex shrink-0 items-center gap-2">
            <button className="sm:hidden" onClick={() => setSearchOpen(true)} aria-label="Search">
              <Search className="size-5" />
            </button>
            <Popover>
              <PopoverTrigger asChild>
                <button
                  className="relative rounded-lg p-2 hover:bg-muted"
                  aria-label="Notifications"
                >
                  <Bell className="size-5" />
                  {unread ? (
                    <span className="absolute top-1 right-1 grid size-4 place-items-center rounded-full bg-danger text-[9px] font-bold text-white">
                      {unread}
                    </span>
                  ) : null}
                </button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-85 p-0">
                <div className="flex items-center justify-between border-b border-border px-4 py-3">
                  <p className="text-sm font-semibold">Notifications</p>
                  <button className="text-xs font-semibold text-primary" onClick={markAllRead}>
                    Mark all read
                  </button>
                </div>
                <ul className="max-h-80 overflow-y-auto">
                  {notifications.slice(0, 8).map((n) => (
                    <li key={n.id}>
                      <button
                        onClick={() => markRead(n.id)}
                        className={cn(
                          "w-full border-b border-border px-4 py-3 text-left hover:bg-muted/60",
                          !n.read && "bg-primary/5",
                        )}
                      >
                        <p className="text-sm font-semibold">{n.title}</p>
                        <p className="text-xs font-medium text-[#425a6c]">{n.body}</p>
                        <p className="mt-1 text-[11px] font-medium text-[#5f7280]">{n.time}</p>
                      </button>
                    </li>
                  ))}
                </ul>
                <div className="p-2">
                  <Button
                    variant="ghost"
                    className="w-full"
                    onClick={() =>
                      navigate({ to: "/$feature", params: { feature: "notifications" } })
                    }
                  >
                    View all notifications
                  </Button>
                </div>
              </PopoverContent>
            </Popover>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 rounded-xl border border-border px-2 py-1.5 hover:bg-muted">
                  <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
                    {user?.avatarInitial ?? "G"}
                  </span>
                  <span className="hidden text-left lg:block">
                    <span className="block text-xs font-semibold">{user?.name ?? "Guest"}</span>
                    <span className="block text-[11px] font-medium text-[#536d7f]">
                      {user?.role ?? "Viewer"}
                    </span>
                  </span>
                  <ChevronDown className="hidden size-4 text-muted-foreground lg:block" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <p className="text-sm">{user?.name}</p>
                  <p className="text-xs font-medium text-[#425a6c]">{user?.email}</p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => navigate({ to: "/$feature", params: { feature: "profile" } })}
                >
                  <User className="mr-2 size-4" /> Profile
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => navigate({ to: "/$feature", params: { feature: "settings" } })}
                >
                  <Settings className="mr-2 size-4" /> Settings
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => navigate({ to: "/$feature", params: { feature: "audit-logs" } })}
                >
                  <Shield className="mr-2 size-4" /> My audit trail
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={async () => {
                    await signOut();
                    navigate({ to: "/login" });
                  }}
                >
                  <LogOut className="mr-2 size-4" /> Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="min-w-0 flex-1 space-y-6 px-4 py-6 lg:px-6">{children}</main>
        <footer className="border-t border-border px-4 py-4 text-xs text-muted-foreground lg:px-6">
          Government Interoperability &amp; Workflow Orchestration
        </footer>
      </div>

      <CommandDialog open={searchOpen} onOpenChange={setSearchOpen}>
        <CommandInput placeholder="Search applications, services, departments, workflows, integrations, users…" />
        <CommandList>
          <CommandEmpty>No matches found.</CommandEmpty>
          <CommandGroup heading="Applications">
            {results.applications.map((a) => (
              <CommandItem
                key={a.id}
                value={`${a.id} ${a.citizen}`}
                onSelect={() => goDetail("applications", a.id)}
              >
                {a.id} — {a.citizen}
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandGroup heading="Services">
            {results.services.map((s) => (
              <CommandItem key={s.id} value={s.name} onSelect={() => goDetail("services", s.id)}>
                {s.name}
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandGroup heading="Workflows">
            {results.workflows.map((w) => (
              <CommandItem key={w.id} value={w.name} onSelect={() => goDetail("workflows", w.id)}>
                {w.name}
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandGroup heading="Departments">
            {results.departments.map((d) => (
              <CommandItem key={d.id} value={d.name} onSelect={() => goFeature("departments")}>
                {d.name}
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandGroup heading="Integrations">
            {results.integrations.map((i) => (
              <CommandItem
                key={i.id}
                value={i.name}
                onSelect={() => goDetail("integrations", i.id)}
              >
                {i.name}
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandGroup heading="Users">
            {results.users.map((u) => (
              <CommandItem key={u.id} value={u.name} onSelect={() => goFeature("users")}>
                {u.name} — {u.role}
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </div>
  );
}

export function SearchInline({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="relative w-full sm:max-w-xs">
      <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? "Search…"}
        className="pl-9"
      />
    </div>
  );
}
