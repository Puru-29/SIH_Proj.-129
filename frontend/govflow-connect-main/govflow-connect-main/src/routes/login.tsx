import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { AuthLayout } from "@/components/govflow/auth-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { displayBackendRole, useGovFlow } from "@/lib/govflow/store";
import { authenticate } from "@/services/authService";

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submitEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!/^\S+@\S+\.\S+$/.test(email)) return setError("Enter a valid government email address.");
    if (password.length < 8 || password.length > 16)
      return setError("Password must be between 8 and 16 characters.");
    setLoading(true);

    try {
      const authRes = await authenticate(email, password);
      if (authRes && authRes.user) {
        signIn({
          id: authRes.user.id,
          name: authRes.user.full_name,
          email: authRes.user.email,
          mobile: authRes.user.phone || "",
          role: displayBackendRole(authRes.user.role),
          backendRole: authRes.user.role,
          department: authRes.user.department || "GovFlow Platform",
          avatarInitial: authRes.user.full_name[0]!.toUpperCase(),
        });
        setLoading(false);
        toast.success(`Signed in as ${authRes.user.full_name}`);
        navigate({ to: authRes.user.role === "citizen" ? "/citizen" : "/dashboard" });
        return;
      }
    } catch (backendErr: unknown) {
      setError(
        backendErr instanceof Error
          ? backendErr.message
          : "Unable to sign in. Check your credentials and try again.",
      );
    }
    setLoading(false);
  };

  const sendOtp = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!/^\d{10}$/.test(mobile)) return setError("Enter a valid 10-digit mobile number.");
    setError(
      "Mobile OTP sign-in is unavailable because backend authentication does not provide an OTP endpoint. Use email and password.",
    );
  };

  return (
    <AuthLayout
      title="Sign in to GovFlow"
      subtitle="Secure sign in for Admin, Department Officer, Developer, Operator and Auditor roles."
      variant="staff"
    >
      <Tabs defaultValue="email" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2 rounded-xl border border-[#dfe4e1] bg-[#edf2ef] p-1">
          <TabsTrigger
            value="email"
            className="h-12 rounded-xl text-[1.05rem] font-semibold data-[state=active]:bg-white data-[state=active]:text-[#1d2d3d] data-[state=active]:shadow-none"
          >
            Email &amp; password
          </TabsTrigger>
          <TabsTrigger
            value="mobile"
            className="h-12 rounded-xl text-[1.05rem] font-semibold data-[state=active]:bg-white data-[state=active]:text-[#1d2d3d] data-[state=active]:shadow-none"
          >
            Mobile OTP
          </TabsTrigger>
        </TabsList>

        <TabsContent value="email">
          <form onSubmit={submitEmail} className="space-y-4">
            <div className="space-y-2 text-left">
              <Label htmlFor="email" className="text-[1.1rem] font-semibold text-[#1d2d3d]">
                Government email
              </Label>
              <Input
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@gov.in"
                className="h-[56px] rounded-xl border-[#cbd8d3] bg-[#f2f4f2] px-4 text-[1.05rem] text-[#1d2d3d] shadow-none placeholder:text-[#738292] focus-visible:ring-2 focus-visible:ring-[#0d5a49]/15"
              />
            </div>
            <div className="space-y-2 text-left">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-[1.1rem] font-semibold text-[#1d2d3d]">
                  Password
                </Label>
                <Link to="/forgot-password" className="text-[0.95rem] font-semibold text-[#0d5a49] hover:underline">
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
                className="h-[56px] rounded-xl border-[#cbd8d3] bg-[#f2f4f2] px-4 text-[1.05rem] text-[#1d2d3d] shadow-none placeholder:text-[#738292] focus-visible:ring-2 focus-visible:ring-[#0d5a49]/15"
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
              disabled={loading}
            >
              {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
              Sign in
            </Button>
          </form>
        </TabsContent>

        <TabsContent value="mobile">
          <form onSubmit={sendOtp} className="space-y-4">
            <div className="space-y-2 text-left">
              <Label htmlFor="mobile" className="text-[1.1rem] font-semibold text-[#1d2d3d]">
                Mobile number
              </Label>
              <Input
                id="mobile"
                value={mobile}
                onChange={(e) => setMobile(e.target.value)}
                placeholder="10-digit mobile"
                inputMode="numeric"
                maxLength={10}
                className="h-[56px] rounded-xl border-[#cbd8d3] bg-[#f2f4f2] px-4 text-[1.05rem] text-[#1d2d3d] shadow-none placeholder:text-[#738292] focus-visible:ring-2 focus-visible:ring-[#0d5a49]/15"
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
              disabled={loading}
            >
              {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
              Send OTP
            </Button>
          </form>
        </TabsContent>
      </Tabs>

      <p className="mt-6 text-center text-[1.05rem] text-[#4c5f6d]">
        New citizen?{" "}
        <Link to="/citizen/register" className="font-semibold text-[#0d5a49] underline-offset-4 hover:underline">
          Create a citizen account
        </Link>
      </p>
      <p className="mt-2 text-center text-[1.05rem] text-[#4c5f6d]">
        Citizen?{" "}
        <Link to="/citizen/login" className="font-semibold text-[#0d5a49] underline-offset-4 hover:underline">
          Open Citizen Portal
        </Link>
      </p>
      <p className="mt-2 text-center text-[0.95rem] text-[#4c5f6d]">
        Use your Government Staff account credentials to continue.
      </p>
    </AuthLayout>
  );
}
