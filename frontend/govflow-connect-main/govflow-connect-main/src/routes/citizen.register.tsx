import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { AuthLayout } from "@/components/govflow/auth-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { useGovFlow } from "@/lib/govflow/store";

export const Route = createFileRoute("/citizen/register")({ component: CitizenRegisterPage });

function CitizenRegisterPage() {
  const navigate = useNavigate();
  const { signIn } = useGovFlow();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (!/^[A-Za-z][A-Za-z .'-]{2,119}$/.test(form.name.trim())) return setError("Name must contain letters and spaces only.");
    if (!/^[6-9]\d{9}$/.test(form.phone)) return setError("Enter a valid 10-digit Indian mobile number.");
    if (form.password.length < 8 || form.password.length > 16) return setError("Password must be between 8 and 16 characters.");
    setLoading(true);
    try {
      const result = await api.signup({ full_name: form.name, email: form.email, password: form.password, phone: form.phone, role: "citizen" });
      signIn({ name: result.user.full_name, email: result.user.email, mobile: result.user.phone || "", role: "Citizen", department: "Citizen", avatarInitial: result.user.full_name[0]?.toUpperCase() || "C" });
      toast.success("Citizen account created");
      navigate({ to: "/citizen" });
    } catch (registerError: any) { setError(registerError.message || "Unable to create account."); }
    finally { setLoading(false); }
  };

  return <AuthLayout title="Create citizen account" subtitle="Register once to apply for and track government services."><form onSubmit={submit} className="space-y-4"><div className="space-y-2"><Label htmlFor="citizen-register-name">Full name</Label><Input id="citizen-register-name" value={form.name} onChange={(event) => update("name", event.target.value.replace(/[^A-Za-z .'-]/g, ""))} maxLength={120} autoComplete="name" required /></div><div className="space-y-2"><Label htmlFor="citizen-register-email">Email</Label><Input id="citizen-register-email" type="email" value={form.email} onChange={(event) => update("email", event.target.value)} autoComplete="email" required /></div><div className="space-y-2"><Label htmlFor="citizen-register-phone">Mobile number</Label><Input id="citizen-register-phone" value={form.phone} onChange={(event) => update("phone", event.target.value.replace(/\D/g, "").slice(0, 10))} inputMode="numeric" maxLength={10} autoComplete="tel" required /></div><div className="space-y-2"><Label htmlFor="citizen-register-password">Password</Label><Input id="citizen-register-password" type="password" value={form.password} onChange={(event) => update("password", event.target.value.slice(0, 16))} minLength={8} maxLength={16} autoComplete="new-password" required /></div>{error ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p> : null}<Button type="submit" className="w-full" disabled={loading}>{loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}Register as Citizen</Button></form><p className="mt-6 text-sm text-muted-foreground">Already registered? <Link to="/citizen/login" className="font-semibold text-primary">Citizen sign in</Link></p><p className="mt-2 text-sm text-muted-foreground">Government Staff? <Link to="/signup" className="font-semibold text-primary">Staff registration</Link></p></AuthLayout>;
}