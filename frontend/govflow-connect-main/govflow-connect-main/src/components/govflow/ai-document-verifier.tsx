import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileCheck2,
  FileUp,
  Loader2,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { api, type MeshApplication, type MeshDocumentVerificationResponse } from "@/lib/api";
import { useGovFlow } from "@/lib/govflow/store";

export function AIDocumentVerifier() {
  const { user } = useGovFlow();
  const [applications, setApplications] = useState<MeshApplication[]>([]);
  const [applicationId, setApplicationId] = useState("");
  const [verifications, setVerifications] = useState<MeshDocumentVerificationResponse[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [reviewingId, setReviewingId] = useState<number | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const canReview =
    user?.backendRole === "department_officer" || user?.backendRole === "system_admin";

  const refresh = useCallback(async (selectedApplicationId?: number) => {
    setError("");
    try {
      const rows = await api.getDocumentVerifications({
        ...(selectedApplicationId ? { applicationId: selectedApplicationId } : {}),
        limit: 100,
      });
      setVerifications(rows);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Verification results could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([api.getApplications(), api.getDocumentVerifications({ limit: 100 })])
      .then(([applicationRows, verificationRows]) => {
        if (!active) return;
        setApplications(applicationRows);
        setVerifications(verificationRows);
        setApplicationId(applicationRows[0] ? String(applicationRows[0].id) : "");
      })
      .catch((loadError: unknown) => {
        if (!active) return;
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Document verification data could not be loaded.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleUpload = async () => {
    if (!selectedFile || !applicationId) {
      setError("Choose a document and the application it belongs to.");
      return;
    }
    setUploading(true);
    setError("");
    try {
      const result = await api.uploadAndVerifyDocument(
        selectedFile,
        Number(applicationId),
        documentType.trim() || undefined,
      );
      setVerifications((current) => [
        result,
        ...current.filter((item) => item.verification_result.id !== result.verification_result.id),
      ]);
      setSelectedFile(null);
      setDocumentType("");
      toast.success("Document received and queued for human review.");
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Document upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleReview = async (
    item: MeshDocumentVerificationResponse,
    decision: "VERIFIED" | "REJECTED",
  ) => {
    if (reviewNote.trim().length < 5) {
      setError("Add a review note of at least five characters before making a decision.");
      return;
    }
    setReviewingId(item.verification_result.id);
    setError("");
    try {
      const updated = await api.reviewDocumentVerification(item.verification_result.id, {
        decision,
        note: reviewNote.trim(),
      });
      setVerifications((current) =>
        current.map((entry) =>
          entry.verification_result.id === updated.verification_result.id ? updated : entry,
        ),
      );
      setReviewNote("");
      toast.success(`Document marked ${decision.toLowerCase()}.`);
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "Document review failed.");
    } finally {
      setReviewingId(null);
    }
  };

  const handleDownload = async (item: MeshDocumentVerificationResponse) => {
    setDownloadingId(item.document.id);
    setError("");
    try {
      const blob = await api.downloadDocument(item.document.id);
      const objectUrl = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = item.document.title;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (downloadError) {
      setError(
        downloadError instanceof Error
          ? downloadError.message
          : "The original document could not be downloaded.",
      );
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <section className="space-y-6 rounded-2xl border border-border bg-card p-6 shadow-sm">
      <header className="space-y-2 border-b border-border pb-5">
        <div className="flex items-center gap-2">
          <FileCheck2 className="size-5 text-primary" />
          <h2 className="text-lg font-bold">Document Verification</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Upload PDF, JPG, or PNG records for extraction, format checks, duplicate detection, and
          matching against stored verified source records.
        </p>
        <p className="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-800 dark:text-amber-300">
          <ShieldAlert className="mt-0.5 size-4 shrink-0" />
          Automated checks are assistive signals only. They do not establish authenticity or fraud
          probability; a department officer makes the final decision.
        </p>
      </header>

      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] md:items-end">
        <label className="space-y-1 text-xs font-semibold">
          Application
          <select
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-normal"
            value={applicationId}
            onChange={(event) => setApplicationId(event.target.value)}
            disabled={!applications.length}
          >
            {applications.map((application) => (
              <option key={application.id} value={application.id}>
                {application.reference_id} · {application.service_name ?? "Service"}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1 text-xs font-semibold">
          Document type hint (optional)
          <input
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-normal"
            value={documentType}
            onChange={(event) => setDocumentType(event.target.value)}
            placeholder="For example, Income Certificate"
          />
        </label>
        <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-semibold hover:bg-muted">
          <FileUp className="size-4" />
          {selectedFile?.name ?? "Choose file"}
          <input
            className="sr-only"
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
          onClick={() => void handleUpload()}
          disabled={uploading || !selectedFile || !applicationId}
        >
          {uploading ? (
            <span className="inline-flex items-center gap-2">
              <Loader2 className="size-4 animate-spin" /> Processing
            </span>
          ) : (
            "Upload and verify"
          )}
        </button>
        <button
          type="button"
          className="rounded-lg border border-border px-4 py-2 text-sm font-semibold hover:bg-muted"
          onClick={() => void refresh(applicationId ? Number(applicationId) : undefined)}
          disabled={loading}
        >
          Refresh results
        </button>
        <span className="text-xs text-muted-foreground">Maximum file size: 10 MB</span>
      </div>

      {error ? (
        <p
          role="alert"
          className="flex items-center gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive"
        >
          <XCircle className="size-4 shrink-0" /> {error}
        </p>
      ) : null}
      {!applications.length && !loading ? (
        <p className="rounded-lg border border-border p-4 text-sm text-muted-foreground">
          No applications are available to attach a document to.
        </p>
      ) : null}
      {loading ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Loading verification queue…
        </p>
      ) : null}

      <div className="space-y-4">
        {verifications.map((item) => {
          const result = item.verification_result;
          const isReviewing = reviewingId === result.id;
          return (
            <article key={result.id} className="space-y-4 rounded-xl border border-border p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold">{item.document.title}</h3>
                  <p className="text-xs text-muted-foreground">
                    {item.document.doc_type} · Application #{item.document.application_id} ·{" "}
                    {new Date(result.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusLabel status={result.verification_status} />
                  <button
                    type="button"
                    className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold hover:bg-muted disabled:opacity-50"
                    disabled={downloadingId === item.document.id}
                    onClick={() => void handleDownload(item)}
                  >
                    {downloadingId === item.document.id ? "Preparing…" : "Download original"}
                  </button>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <DataCell
                  label="Certificate number"
                  value={result.extracted_fields["certificate_number"]}
                />
                <DataCell label="Name" value={result.extracted_fields["name"]} />
                <DataCell label="Issue date" value={result.extracted_fields["issue_date"]} />
                <DataCell label="Issuer" value={result.extracted_fields["issuer"]} />
                <DataCell label="Income" value={result.extracted_fields["income"]} />
                <DataCell label="Source record" value={result.source_match_status} />
                <DataCell label="Duplicate check" value={result.duplicate_status} />
                <DataCell
                  label="Extraction signal"
                  value={`${(result.confidence * 100).toFixed(0)}%`}
                />
              </div>

              <div>
                <p className="mb-1 text-xs font-semibold">Pipeline</p>
                <ol className="flex flex-wrap gap-2">
                  {result.pipeline_steps.map((step) => (
                    <li
                      key={`${step.step}-${String(step["page"] ?? "")}`}
                      className="rounded-full border border-border px-2 py-1 text-[10px] text-muted-foreground"
                    >
                      {step.step.replaceAll("_", " ")} · {step.status}
                    </li>
                  ))}
                </ol>
              </div>

              {result.tampering_indicators.length ? (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                  <p className="mb-1 flex items-center gap-2 text-xs font-semibold">
                    <AlertTriangle className="size-4 text-amber-600" />
                    Review indicators (not fraud findings)
                  </p>
                  <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                    {result.tampering_indicators.map((indicator) => (
                      <li key={indicator}>{indicator}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {result.review_note ? (
                <p className="text-xs text-muted-foreground">Officer note: {result.review_note}</p>
              ) : null}

              {canReview && result.verification_status === "PENDING_REVIEW" ? (
                <div className="flex flex-wrap gap-2">
                  <input
                    className="min-w-55 flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm"
                    value={reviewNote}
                    onChange={(event) => setReviewNote(event.target.value)}
                    placeholder="Required review note"
                    aria-label={`Review note for ${item.document.title}`}
                  />
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                    disabled={isReviewing}
                    onClick={() => void handleReview(item, "VERIFIED")}
                  >
                    <CheckCircle2 className="size-4" /> Verify
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-lg border border-destructive/40 px-3 py-2 text-sm font-semibold text-destructive disabled:opacity-50"
                    disabled={isReviewing}
                    onClick={() => void handleReview(item, "REJECTED")}
                  >
                    <XCircle className="size-4" /> Reject
                  </button>
                </div>
              ) : null}
            </article>
          );
        })}
        {!loading && !verifications.length ? (
          <p className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
            No persisted document verification results are available.
          </p>
        ) : null}
      </div>
    </section>
  );
}

function DataCell({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-lg bg-muted/40 p-3">
      <p className="text-[10px] font-semibold uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 break-words text-sm font-medium">
        {value === undefined || value === null || value === "" ? "Not extracted" : String(value)}
      </p>
    </div>
  );
}

function StatusLabel({ status }: { status: string }) {
  const className =
    status === "VERIFIED"
      ? "bg-emerald-500/10 text-emerald-700"
      : status === "REJECTED"
        ? "bg-destructive/10 text-destructive"
        : "bg-amber-500/10 text-amber-700";
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-bold ${className}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
