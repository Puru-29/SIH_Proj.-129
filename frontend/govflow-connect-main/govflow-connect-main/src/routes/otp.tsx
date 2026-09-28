import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AuthLayout } from "@/components/govflow/auth-layout";
import { Button } from "@/components/ui/button";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";

type OtpSearch = { mobile: string; role: string };

const cleanSearchValue = (value: unknown, fallback: string) => {
  if (typeof value !== "string") return fallback;
  return value.replace(/^"|"$/g, "") || fallback;
};

export const Route = createFileRoute("/otp")({
  validateSearch: (search: Record<string, unknown>): OtpSearch => ({
    mobile: cleanSearchValue(search["mobile"], ""),
    role: cleanSearchValue(search["role"], "Department Officer"),
  }),
  head: () => ({
    meta: [
      { title: "Verify OTP — GovFlow" },
      {
        name: "description",
        content: "Mobile OTP sign-in is unavailable because backend authentication has no OTP endpoint.",
      },
      { property: "og:title", content: "Verify OTP — GovFlow" },
      {
        property: "og:description",
        content: "Mobile OTP sign-in is unavailable.",
      },
    ],
  }),
  component: OtpPage,
});

function OtpPage() {
  const { mobile } = Route.useSearch();
  const [code, setCode] = useState("");
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
    setError("Mobile OTP sign-in is unavailable because backend authentication does not provide an OTP endpoint. Use email and password.");
  };

  return (
    <AuthLayout
      title="Verify your mobile"
      subtitle={`Mobile OTP sign-in for +91 ${mobile} is unavailable. No code can authenticate a GovFlow session; use email and password instead.`}
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

        <Button className="w-full" onClick={verify}>
          Verify &amp; continue
        </Button>

        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {seconds > 0 ? `Retry available in ${seconds}s` : "Mobile OTP is unavailable"}
          </span>
          <button
            className="font-semibold text-primary disabled:text-muted-foreground"
            disabled={seconds > 0}
            onClick={() => {
              setSeconds(30);
              setError("OTP resend is unavailable because backend authentication does not provide an OTP endpoint.");
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
