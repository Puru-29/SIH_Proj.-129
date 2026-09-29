import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { Loader2 } from "lucide-react";
import { AuthLayout } from "@/components/govflow/auth-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type MeshDepartment, type StaffRequestRole } from "@/lib/api";

export const Route = createFileRoute("/staff/request")({
  component: StaffRequestPage,
});

function StaffRequestPage() {
  const [departments, setDepartments] = useState<MeshDepartment[]>([]);
  const [form, setForm] = useState({
    fullName: "",
    email: "",
    password: "",
    phone: "",
    role: "department_officer" as StaffRequestRole,
    departmentId: "",
  });
  const [loadingDepartments, setLoadingDepartments] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    let active = true;
    void api
      .getDepartments()
      .then((items) => {
        if (active) setDepartments(items);
      })
      .catch((loadError: unknown) => {
        if (active) {
          setError(
            loadError instanceof Error ? loadError.message : "Departments could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (active) setLoadingDepartments(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    if (form.role === "department_officer" && !form.departmentId) {
      setError("Select the department where you work.");
      return;
    }

    setSubmitting(true);
    try {
      await api.requestStaffAccount({
        full_name: form.fullName.trim(),
        email: form.email.trim(),
        password: form.password,
        role: form.role,
        ...(form.phone ? { phone: form.phone } : {}),
        ...(form.departmentId ? { department_id: Number(form.departmentId) } : {}),
      });
      setSubmitted(true);
    } catch (requestError: unknown) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Staff account request could not be submitted.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title={submitted ? "Request submitted" : "Request a staff account"}
      subtitle={
        submitted
          ? "Your account cannot be used until a system administrator approves it."
          : "A system administrator must approve your request before you can sign in."
      }
      variant="staff"
    >
      {submitted ? (
        <div className="space-y-5 text-center">
          <p className="rounded-xl border border-[#b9dfd2] bg-[#e7f4ef] px-4 py-3 text-base font-medium text-[#155d4b]">
            Your request was received. You can sign in after your administrator approves the
            account.
          </p>
          <Link
            to="/login"
            className="font-semibold text-[#0d5a49] underline-offset-4 hover:underline"
          >
            Return to staff sign in
          </Link>
        </div>
      ) : (
        <>
          <form onSubmit={submit} className="space-y-4 text-left">
            <div className="space-y-2">
              <Label htmlFor="staff-request-name">Full name</Label>
              <Input
                id="staff-request-name"
                required
                minLength={3}
                maxLength={120}
                autoComplete="name"
                value={form.fullName}
                onChange={(event) =>
                  setForm((current) => ({ ...current, fullName: event.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="staff-request-email">Work email</Label>
              <Input
                id="staff-request-email"
                required
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={(event) =>
                  setForm((current) => ({ ...current, email: event.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="staff-request-password">Password</Label>
              <Input
                id="staff-request-password"
                required
                type="password"
                minLength={8}
                maxLength={16}
                autoComplete="new-password"
                value={form.password}
                onChange={(event) =>
                  setForm((current) => ({ ...current, password: event.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="staff-request-role">Staff role requested</Label>
              <select
                id="staff-request-role"
                required
                value={form.role}
                onChange={(event) => {
                  const role: StaffRequestRole =
                    event.target.value === "interoperability_admin"
                      ? "interoperability_admin"
                      : "department_officer";
                  setForm((current) => ({ ...current, role, departmentId: "" }));
                }}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="department_officer">Department officer</option>
                <option value="interoperability_admin">Interoperability administrator</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="staff-request-department">
                Department {form.role === "department_officer" ? "(required)" : "(optional)"}
              </Label>
              <select
                id="staff-request-department"
                required={form.role === "department_officer"}
                disabled={loadingDepartments || departments.length === 0}
                value={form.departmentId}
                onChange={(event) =>
                  setForm((current) => ({ ...current, departmentId: event.target.value }))
                }
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm disabled:opacity-50"
              >
                <option value="">
                  {loadingDepartments ? "Loading departments…" : "Select a department"}
                </option>
                {departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="staff-request-phone">Mobile number (optional)</Label>
              <Input
                id="staff-request-phone"
                type="tel"
                inputMode="numeric"
                pattern="[6-9][0-9]{9}"
                maxLength={10}
                autoComplete="tel"
                value={form.phone}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    phone: event.target.value.replace(/\D/g, "").slice(0, 10),
                  }))
                }
              />
            </div>
            {error ? (
              <p
                role="alert"
                className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {error}
              </p>
            ) : null}
            <Button
              type="submit"
              className="w-full"
              disabled={
                submitting ||
                loadingDepartments ||
                (form.role === "department_officer" && departments.length === 0)
              }
            >
              {submitting ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
              {submitting ? "Submitting request…" : "Request staff account"}
            </Button>
          </form>
          <p className="mt-6 text-center text-sm text-muted-foreground">
            Already approved?{" "}
            <Link to="/login" className="font-semibold text-primary">
              Sign in
            </Link>
          </p>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            Need a citizen account?{" "}
            <Link to="/citizen/register" className="font-semibold text-primary">
              Register here
            </Link>
          </p>
        </>
      )}
    </AuthLayout>
  );
}
