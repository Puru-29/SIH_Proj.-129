import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { AuthLayout } from "@/components/govflow/auth-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DEPARTMENTS, LOCATIONS, ROLES, type Role } from "@/lib/govflow/data";
import { useGovFlow } from "@/lib/govflow/store";
import { api } from "@/lib/api";

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Create account — GovFlow" },
      {
        name: "description",
        content:
          "Register a GovFlow account for your department and start orchestrating cross-department workflows.",
      },
      { property: "og:title", content: "Create account — GovFlow" },
      {
        property: "og:description",
        content: "Register a department officer, developer, operator or auditor account.",
      },
    ],
  }),
  component: SignupPage,
});

function SignupPage() {
  const navigate = useNavigate();
  const { signIn, setLocationId } = useGovFlow();
  const [form, setForm] = useState({
    name: "",
    email: "",
    mobile: "",
    password: "",
    role: "Department Officer" as Role,
    department: DEPARTMENTS[0]!.name,
    locationId: LOCATIONS[0]!.id,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const isDepartmentOfficer = form.role === "Department Officer";

  const handleRoleChange = (role: string) => {
    setForm((current) => ({
      ...current,
      role: role as Role,
      department: role === "Department Officer" ? DEPARTMENTS[0]!.name : "GovFlow Platform",
    }));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!/^[A-Za-z][A-Za-z .'-]{2,119}$/.test(form.name.trim())) return setError("Name must contain letters and spaces only.");
    if (!/^\S+@\S+\.\S+$/.test(form.email)) return setError("Enter a valid email address.");
    if (!/^[6-9]\d{9}$/.test(form.mobile)) return setError("Enter a valid 10-digit Indian mobile number.");
    if (form.password.length < 8 || form.password.length > 16) return setError("Password must be between 8 and 16 characters.");
    if (isDepartmentOfficer && !DEPARTMENTS.some((department) => department.name === form.department)) return setError("Select one valid department.");
    if (!isDepartmentOfficer && form.department !== "GovFlow Platform") return setError("This role uses GovFlow Platform.");
    setLoading(true);
    try {
      const authRes = await api.signup({
        full_name: form.name,
        email: form.email,
        password: form.password,
        phone: form.mobile,
        role: form.role === "Admin" ? "admin" : form.role === "Department Officer" ? "officer" : form.role.toLowerCase() as "developer" | "operator" | "auditor",
        department: form.department,
      });
      setLocationId(form.locationId);
      signIn({
        name: authRes.user.full_name,
        email: authRes.user.email,
        mobile: `+91 ${authRes.user.phone || form.mobile}`,
        role: authRes.user.role === "admin" ? "Admin" : authRes.user.role === "officer" ? "Department Officer" : authRes.user.role === "developer" ? "Developer" : authRes.user.role === "auditor" ? "Auditor" : "Operator",
        department: form.department,
        avatarInitial: form.name[0]!.toUpperCase(),
      });
      setLoading(false);
      toast.success("Account created — welcome to GovFlow");
      navigate({ to: "/dashboard" });
    } catch (error: any) {
      setLoading(false);
      setError(error.message || "Unable to create account.");
    }
  };

  return (
    <AuthLayout
      title="Create your GovFlow account"
      subtitle="Department access is provisioned instantly in this demonstration build."
    >
      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">Full name</Label>
          <Input
            id="name"
            value={form.name}
            onChange={(e) => set("name", e.target.value.replace(/[^A-Za-z .'-]/g, ""))}
            placeholder="Ramesh Patil"
            maxLength={120}
            autoComplete="name"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="su-email">Email</Label>
            <Input
              id="su-email"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
              placeholder="name@gov.in"
              type="email"
              autoComplete="email"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="su-mobile">Mobile</Label>
            <Input
              id="su-mobile"
              value={form.mobile}
              onChange={(e) => set("mobile", e.target.value.replace(/\D/g, "").slice(0, 10))}
              placeholder="9876543210"
              inputMode="numeric"
              maxLength={10}
              autoComplete="tel"
            />
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="su-pass">Password</Label>
          <Input
            id="su-pass"
            type="password"
            value={form.password}
            onChange={(e) => set("password", e.target.value.slice(0, 16))}
            minLength={8}
            maxLength={16}
            autoComplete="new-password"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>Role</Label>
            <Select value={form.role} onValueChange={handleRoleChange}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLES.map((r) => (
                  <SelectItem key={r} value={r}>
                    {r}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Jurisdiction</Label>
            <Select value={form.locationId} onValueChange={(v) => set("locationId", v)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LOCATIONS.map((l) => (
                  <SelectItem key={l.id} value={l.id}>
                    {l.city}, {l.state}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="space-y-2">
          <Label>Department</Label>
          {isDepartmentOfficer ? (
            <Select value={form.department} onValueChange={(v) => set("department", v)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DEPARTMENTS.map((d) => (
                  <SelectItem key={d.id} value={d.name}>
                    {d.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input value="GovFlow Platform" disabled aria-label="Department" />
          )}
        </div>
        {error ? (
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
        ) : null}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
          Create account
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted-foreground">
        Already registered?{" "}
        <Link to="/login" className="font-semibold text-primary">
          Sign in
        </Link>
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        Citizen?{" "}
        <Link to="/citizen/register" className="font-semibold text-primary">
          Create a Citizen account
        </Link>
      </p>
    </AuthLayout>
  );
}
