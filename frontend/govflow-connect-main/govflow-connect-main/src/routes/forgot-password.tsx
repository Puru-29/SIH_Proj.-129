import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { AuthLayout } from "@/components/govflow/auth-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/forgot-password")({
  head: () => ({
    meta: [
      { title: "Reset password — GovFlow" },
      {
        name: "description",
        content: "Recover access to your GovFlow department account with a verification code.",
      },
      { property: "og:title", content: "Reset password — GovFlow" },
      {
        property: "og:description",
        content: "Send a recovery code to your registered government email or mobile.",
      },
    ],
  }),
  component: ForgotPasswordPage,
});

function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!/^\S+@\S+\.\S+$/.test(email))
      return setError("Enter the email registered with your department.");
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setSent(true);
      toast.success("Recovery code sent");
    }, 800);
  };

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="We will send a 6-digit recovery code to your registered address."
    >
      {sent ? (
        <div className="space-y-5">
          <div className="surface flex items-start gap-3 p-4">
            <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" />
            <div>
              <p className="text-sm font-semibold">Recovery code sent to {email}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                The code is valid for 10 minutes.
              </p>
            </div>
          </div>
          <Button
            className="w-full"
            onClick={() =>
              navigate({ to: "/otp", search: { mobile: "9876543210", role: "Department Officer" } })
            }
          >
            Enter verification code
          </Button>
          <Button variant="ghost" className="w-full" onClick={() => setSent(false)}>
            Use a different email
          </Button>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="fp-email">Registered email</Label>
            <Input
              id="fp-email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@gov.in"
            />
          </div>
          {error ? (
            <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          ) : null}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}
            Send recovery code
          </Button>
        </form>
      )}
      <p className="mt-6 text-sm text-muted-foreground">
        Remembered it?{" "}
        <Link to="/login" className="font-semibold text-primary">
          Back to sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
