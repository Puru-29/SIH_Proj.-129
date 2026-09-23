import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { AuthLayout } from "@/components/govflow/auth-layout";
import { Button } from "@/components/ui/button";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { useGovFlow } from "@/lib/govflow/store";
import type { Role } from "@/lib/govflow/data";

type OtpSearch = { mobile: string; role: string };

const cleanSearchValue = (value: unknown, fallback: string) => {
  if (typeof value !== "string") return fallback;
  return value.replace(/^"|"$/g, "") || fallback;
};

export const Route = createFileRoute("/otp")({
  validateSearch: (search: Record<string, unknown>): OtpSearch => ({
    mobile: cleanSearchValue(search["mobile"], "9876543210"),
    role: cleanSearchValue(search["role"], "Department Officer"),
  }),
  head: () => ({
    meta: [
      { title: "Verify OTP — GovFlow" },
      {
        name: "description",
        content:
          "Enter the one-time password sent to your registered mobile number to access GovFlow.",
      },
      { property: "og:title", content: "Verify OTP — GovFlow" },
      {
        property: "og:description",
        content: "Two-step verification for secure government platform access.",
      },
    ],
  }),
  component: OtpPage,
});

function OtpPage() {
  const { mobile, role } = Route.useSearch();
  const navigate = useNavigate();
  const { signIn } = useGovFlow();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [seconds, setSeconds] = useState(30);

  useEffect(() => {
    if (seconds <= 0) return;
    const t = setTimeout(() => setSeconds((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [seconds]);

  const verify = () => {
    setError("");
    if (code.length !== 6) return setError("Enter all 6 digits of the OTP.");
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      if (code === "000000") {
        setError("Invalid OTP. Please try again.");
        return;
      }
      signIn({
        name: "Ramesh Patil",
        email: "ramesh.patil@gov.in",
        mobile: `+91 ${mobile}`,
        role: role as Role,
        department: "Education Department",
        avatarInitial: "R",
      });
      toast.success("Mobile verified — signed in");
      navigate({ to: "/dashboard" });
    }, 900);
  };

  return (
    <AuthLayout
      title="Verify your mobile"
      subtitle={`Enter the 6-digit code sent to +91 ${mobile}. Any code except 000000 works in this demo.`}
    >
      <div className="space-y-6">
        <InputOTP maxLength={6} value={code} onChange={setCode}>
          <InputOTPGroup>
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <InputOTPSlot key={i} index={i} />
            ))}
          </InputOTPGroup>
        </InputOTP>

        {error ? (
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
        ) : null}

        <Button className="w-full" onClick={verify} disabled={loading}>
          {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
          Verify &amp; continue
        </Button>

        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {seconds > 0 ? `Resend available in ${seconds}s` : "Didn't receive a code?"}
          </span>
          <button
            className="font-semibold text-primary disabled:text-muted-foreground"
            disabled={seconds > 0}
            onClick={() => {
              setSeconds(30);
              toast.success("OTP resent");
            }}
          >
            Resend OTP
          </button>
        </div>

        <Link to="/login" className="block text-sm font-semibold text-primary">
          Use a different sign-in method
        </Link>
      </div>
    </AuthLayout>
  );
}
