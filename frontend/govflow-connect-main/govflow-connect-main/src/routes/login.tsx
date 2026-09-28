import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { AuthLayout } from "@/components/govflow/auth-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ROLES, type Role } from "@/lib/govflow/data";
import { useGovFlow } from "@/lib/govflow/store";
import { api } from "@/lib/api";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in — GovFlow" },
      {
        name: "description",
        content:
          "Sign in to GovFlow with email or mobile OTP to orchestrate cross-department government workflows.",
      },
      { property: "og:title", content: "Sign in — GovFlow" },
      {
        property: "og:description",
        content: "Secure role-based access for Government Staff.",
      },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const { signIn } = useGovFlow();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mobile, setMobile] = useState("");
  const [role, setRole] = useState<Role>("Admin");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submitEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!/^\S+@\S+\.\S+$/.test(email)) return setError("Enter a valid government email address.");
    if (password.length < 8 || password.length > 16) return setError("Password must be between 8 and 16 characters.");
    setLoading(true);

    try {
      const authRes = await api.login(email, password);
      if (authRes && authRes.user) {
        signIn({
          name: authRes.user.full_name,
          email: authRes.user.email,
          mobile: authRes.user.phone || "",
          role: authRes.user.role === "citizen" ? "Citizen" : authRes.user.role === "admin" ? "Admin" : authRes.user.role === "officer" ? "Department Officer" : authRes.user.role === "developer" ? "Developer" : authRes.user.role === "auditor" ? "Auditor" : "Operator",
          department: authRes.user.department || "GovFlow Platform",
          avatarInitial: authRes.user.full_name[0]!.toUpperCase(),
        });
        setLoading(false);
        toast.success(`Signed in as ${authRes.user.full_name}`);
        navigate({ to: authRes.user.role === "citizen" ? "/citizen" : "/dashboard" });
        return;
      }
    } catch (backendErr: any) {
      setError(backendErr.message || "Unable to sign in. Check your credentials and try again.");
    }
    setLoading(false);
  };


  const sendOtp = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!/^\d{10}$/.test(mobile)) return setError("Enter a valid 10-digit mobile number.");
    setError("Mobile OTP sign-in is unavailable because backend authentication does not provide an OTP endpoint. Use email and password.");
  };

  return (
    <AuthLayout
      title="Sign in to GovFlow"
      subtitle="Secure sign in for Admin, Department Officer, Developer, Operator and Auditor roles."
      variant="staff"
    >
      <Tabs defaultValue="email">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="email">Email &amp; password</TabsTrigger>
          <TabsTrigger value="mobile">Mobile OTP</TabsTrigger>
        </TabsList>

        <div className="mt-6 space-y-2">
          <Label>Role</Label>
          <Select value={role} onValueChange={(v) => setRole(v as Role)}>
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

        <TabsContent value="email">
          <form onSubmit={submitEmail} className="mt-4 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Government email</Label>
              <Input
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@gov.in"
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link to="/forgot-password" className="text-xs font-semibold text-primary">
                  Forgot password?
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                maxLength={16}
                autoComplete="current-password"
              />
            </div>
            {error ? (
              <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </p>
            ) : null}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
              Sign in
            </Button>
          </form>
        </TabsContent>

        <TabsContent value="mobile">
          <form onSubmit={sendOtp} className="mt-4 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="mobile">Mobile number</Label>
              <Input
                id="mobile"
                value={mobile}
                onChange={(e) => setMobile(e.target.value)}
                placeholder="10-digit mobile"
                inputMode="numeric"
                maxLength={10}
              />
            </div>
            {error ? (
              <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </p>
            ) : null}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
              Send OTP
            </Button>
          </form>
        </TabsContent>
      </Tabs>

      <p className="mt-6 text-sm text-muted-foreground">
        New citizen?{" "}
        <Link to="/citizen/register" className="font-semibold text-primary">
          Create a citizen account
        </Link>
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        Citizen?{" "}
        <Link to="/citizen/login" className="font-semibold text-primary">
          Open Citizen Portal
        </Link>
      </p>
      <p className="mt-2 text-xs text-muted-foreground">
        Use your Government Staff account credentials to continue.
      </p>
    </AuthLayout>
  );
}
