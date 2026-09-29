import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { AuthLayout } from "@/components/govflow/auth-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useGovFlow } from "@/lib/govflow/store";
import { registerCitizen } from "@/services/authService";

export const Route = createFileRoute("/citizen/register")({ component: CitizenRegisterPage });

function CitizenRegisterPage() {
  const navigate = useNavigate();
  const { signIn, ready } = useGovFlow();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const update = (key: keyof typeof form, value: string) =>
    setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    setError("");
    if (!/^[A-Za-z][A-Za-z .'-]{2,119}$/.test(form.name.trim()))
      return setError("Name must contain letters and spaces only.");
    if (!/^[6-9]\d{9}$/.test(form.phone))
      return setError("Enter a valid 10-digit Indian mobile number.");
    if (form.password.length < 8 || form.password.length > 16)
      return setError("Password must be between 8 and 16 characters.");
    setLoading(true);
    try {
      const result = await registerCitizen({
        fullName: form.name,
        email: form.email,
        password: form.password,
        phone: form.phone,
      });
      signIn({
        name: result.fullName,
        email: result.email,
        mobile: result.phone,
        role: "Citizen",
        department: "Citizen",
        avatarInitial: result.fullName[0]?.toUpperCase() || "C",
      });
      toast.success("Citizen account created");
      navigate({ to: "/citizen" });
    } catch (registerError: unknown) {
      setError(
        registerError instanceof Error ? registerError.message : "Unable to create account.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Create citizen account"
      subtitle="Register once to apply for and track government services."
      variant="citizen"
    >
      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-2 text-left">
          <Label
            htmlFor="citizen-register-name"
            className="text-[1.05rem] font-semibold text-[#1a2b3a]"
          >
            Full name
          </Label>
          <Input
            id="citizen-register-name"
            value={form.name}
            onChange={(event) => update("name", event.target.value.replace(/[^A-Za-z .'-]/g, ""))}
            maxLength={120}
            autoComplete="name"
            required
            className="h-[56px] rounded-xl border-[#cbd8d3] bg-[#f2f4f2] px-4 text-[1.05rem] text-[#1a2b3a] shadow-none placeholder:text-[#738292] focus-visible:ring-2 focus-visible:ring-[#0d5a49]/15"
          />
        </div>
        <div className="space-y-2 text-left">
          <Label
            htmlFor="citizen-register-email"
            className="text-[1.05rem] font-semibold text-[#1a2b3a]"
          >
            Email
          </Label>
          <Input
            id="citizen-register-email"
            type="email"
            value={form.email}
            onChange={(event) => update("email", event.target.value)}
            autoComplete="email"
            required
            className="h-[56px] rounded-xl border-[#cbd8d3] bg-[#f2f4f2] px-4 text-[1.05rem] text-[#1a2b3a] shadow-none placeholder:text-[#738292] focus-visible:ring-2 focus-visible:ring-[#0d5a49]/15"
          />
        </div>
        <div className="space-y-2 text-left">
          <Label
            htmlFor="citizen-register-phone"
            className="text-[1.05rem] font-semibold text-[#1a2b3a]"
          >
            Mobile number
          </Label>
          <Input
            id="citizen-register-phone"
            value={form.phone}
            onChange={(event) =>
              update("phone", event.target.value.replace(/\D/g, "").slice(0, 10))
            }
            inputMode="numeric"
            maxLength={10}
            autoComplete="tel"
            required
            className="h-[56px] rounded-xl border-[#cbd8d3] bg-[#f2f4f2] px-4 text-[1.05rem] text-[#1a2b3a] shadow-none placeholder:text-[#738292] focus-visible:ring-2 focus-visible:ring-[#0d5a49]/15"
          />
        </div>
        <div className="space-y-2 text-left">
          <Label
            htmlFor="citizen-register-password"
            className="text-[1.05rem] font-semibold text-[#1a2b3a]"
          >
            Password
          </Label>
          <Input
            id="citizen-register-password"
            type="password"
            value={form.password}
            onChange={(event) => update("password", event.target.value.slice(0, 16))}
            minLength={8}
            maxLength={16}
            autoComplete="new-password"
            required
            className="h-[56px] rounded-xl border-[#cbd8d3] bg-[#f2f4f2] px-4 text-[1.05rem] text-[#1a2b3a] shadow-none placeholder:text-[#738292] focus-visible:ring-2 focus-visible:ring-[#0d5a49]/15"
          />
        </div>
        {error ? (
          <p className="rounded-xl border border-[#f4c7ce] bg-[#fce7e9] px-4 py-3 text-base font-medium text-[#bf3946]">
            {error}
          </p>
        ) : null}
        <Button
          type="submit"
          className="mt-2 h-[58px] w-full rounded-xl bg-[#0d5a49] text-lg font-bold text-white shadow-none hover:bg-[#0b4f42]"
          disabled={loading || !ready}
        >
          {loading || !ready ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
          {!ready ? "Checking session…" : loading ? "Creating account…" : "Register as Citizen"}
        </Button>
      </form>
      <p className="mt-6 text-center text-[1.05rem] text-[#4c5f6d]">
        Already registered?{" "}
        <Link
          to="/citizen/login"
          className="font-semibold text-[#0d5a49] underline-offset-4 hover:underline"
        >
          Citizen sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
