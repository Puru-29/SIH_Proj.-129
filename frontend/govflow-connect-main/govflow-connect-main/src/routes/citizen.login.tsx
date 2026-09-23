import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { AuthLayout } from "@/components/govflow/auth-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { useGovFlow } from "@/lib/govflow/store";

export const Route = createFileRoute("/citizen/login")({ component: CitizenLoginPage });

function CitizenLoginPage() {
  const navigate = useNavigate();
  const { signIn } = useGovFlow();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (password.length < 8 || password.length > 16) { setError("Password must be between 8 and 16 characters."); return; }
    setLoading(true);
    try {
      const result = await api.login(email, password);
      if (result.user.role !== "citizen") throw new Error("This is a Government Staff account. Use staff sign in instead.");
      signIn({ name: result.user.full_name, email: result.user.email, mobile: result.user.phone || "", role: "Citizen", department: "Citizen", avatarInitial: result.user.full_name[0]?.toUpperCase() || "C" });
      toast.success("Welcome to the Citizen Portal");
      navigate({ to: "/citizen" });
    } catch (loginError: any) { setError(loginError.message || "Unable to sign in."); }
    finally { setLoading(false); }
  };

  return <AuthLayout title="Citizen sign in" subtitle="Access your government services and application journey."><div className="mb-5 flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-2 text-sm text-primary"><ShieldCheck className="size-4" /> Secure citizen access</div><form onSubmit={submit} className="space-y-4"><div className="space-y-2"><Label htmlFor="citizen-email">Email</Label><Input id="citizen-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></div><div className="space-y-2"><Label htmlFor="citizen-password">Password</Label><Input id="citizen-password" type="password" value={password} onChange={(event) => setPassword(event.target.value.slice(0, 16))} minLength={8} maxLength={16} autoComplete="current-password" required /></div>{error ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p> : null}<Button type="submit" className="w-full" disabled={loading}>{loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}Sign in as Citizen</Button></form><p className="mt-6 text-sm text-muted-foreground">New citizen? <Link to="/citizen/register" className="font-semibold text-primary">Create an account</Link></p><p className="mt-2 text-sm text-muted-foreground">Government Staff? <Link to="/login" className="font-semibold text-primary">Staff sign in</Link></p></AuthLayout>;
}