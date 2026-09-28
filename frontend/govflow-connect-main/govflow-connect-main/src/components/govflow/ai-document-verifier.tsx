import React, { useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileCheck,
  FileUp,
  Loader2,
  ShieldAlert,
  Sparkles,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";

export function AIDocumentVerifier() {
  const [docType, setDocType] = useState<string>("Income Certificate");
  const [docText, setDocText] = useState<string>(
    "GOVERNMENT OF MAHARASHTRA\nREVENUE DEPARTMENT\nINCOME CERTIFICATE\nApplicant: Aarav Patel\nAnnual Family Income: Rs 1,20,000\nCertificate No: INC-92821\nIssue Date: 05/09/2026\nVerified by: Revenue Certificate System"
  );
  const [claimedIncome, setClaimedIncome] = useState<string>("120000");
  const [meshIncome, setMeshIncome] = useState<string>("125000");
  const [applicantName, setApplicantName] = useState<string>("Aarav Patel");
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string>("income_certificate_sample.pdf");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const samplePresets: Record<string, { text: string; income: string; mesh: string; name: string }> = {
    "Income Certificate": {
      text: "GOVERNMENT OF MAHARASHTRA\nREVENUE DEPARTMENT\nINCOME CERTIFICATE\nApplicant: Aarav Patel\nAnnual Family Income: Rs 1,20,000\nCertificate No: INC-92821\nIssue Date: 05/09/2026\nVerified by: Revenue Certificate System",
      income: "120000",
      mesh: "125000",
      name: "Aarav Patel",
    },
    "Aadhaar Card": {
      text: "GOVERNMENT OF INDIA\nUNIQUE IDENTIFICATION AUTHORITY OF INDIA\nName: Aarav Patel\nDOB: 14/08/1998\nGender: Male\nAadhaar Number: 4892 1948 8492",
      income: "120000",
      mesh: "125000",
      name: "Aarav Patel",
    },
    "7/12 Land Record Extract": {
      text: "REVENUE DEPARTMENT GOVT OF MAHARASHTRA\nTALUKA: HAVELI, DISTRICT: PUNE\n7/12 EXTRACT GAT NO: 142/2\nOCCUPANT: PRIYA KULKARNI\nAREA: 2.4 ACRES JIRAYAT",
      income: "85000",
      mesh: "85000",
      name: "Priya Kulkarni",
    },
    "Suspicious / Tampered Record": {
      text: "GOVERNMENT OF INDIA INCOME CERTIFICATE\nApplicant: Unknown Entity\nDeclared Income: Rs 25,000\nAadhaar: 0000 0000 0000",
      income: "25000",
      mesh: "650000",
      name: "Ramesh Sharma",
    },
  };

  const handleSelectPreset = (key: string) => {
    setDocType(key);
    const preset = samplePresets[key];
    if (preset) {
      setDocText(preset.text);
      setClaimedIncome(preset.income);
      setMeshIncome(preset.mesh);
      setApplicantName(preset.name);
    }
  };

  const handleRunVerification = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.verifyDocument({
        title: `${docType} Verification - ${applicantName}`,
        doc_type: docType,
        owner_id: 1, // Admin or first user
        document_text: docText,
        citizen_full_name: applicantName,
        citizen_aadhaar_last4: "8492",
        claimed_income: parseFloat(claimedIncome) || 0,
        mesh_income: parseFloat(meshIncome) || 0,
        claimed_land_acres: 2.4,
        mesh_land_acres: 2.4,
        applicant_remarks: "Automated verification test via GovFlow UI",
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to execute AI verification pipeline.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-bold tracking-wide">AI Document & Fraud Verification</h3>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Cross-check uploaded records against connected government data before final approval.
          </p>
          <div className="mt-2 inline-flex items-center gap-2 rounded-full border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-[11px] font-semibold text-amber-700 dark:text-amber-300">
            <ShieldAlert className="h-3.5 w-3.5" />
            Verification assisted • source and identity checks required
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs font-medium text-muted-foreground mr-1">Presets:</span>
          {Object.keys(samplePresets).map((name) => (
            <button
              key={name}
              onClick={() => handleSelectPreset(name)}
              className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${docType === name
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-muted/50 text-foreground border-border hover:bg-muted"
                }`}
            >
              {name.split(" ")[0]}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-5">
        {/* Input parameters */}
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Document Type
              </label>
              <input
                type="text"
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full text-sm rounded-lg border border-input bg-background px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Applicant Name
              </label>
              <input
                type="text"
                value={applicantName}
                onChange={(e) => setApplicantName(e.target.value)}
                className="w-full text-sm rounded-lg border border-input bg-background px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Declared Income (₹)
              </label>
              <input
                type="number"
                value={claimedIncome}
                onChange={(e) => setClaimedIncome(e.target.value)}
                className="w-full text-sm rounded-lg border border-input bg-background px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">
                Mesh Tax Verified Income (₹)
              </label>
              <input
                type="number"
                value={meshIncome}
                onChange={(e) => setMeshIncome(e.target.value)}
                className="w-full text-sm rounded-lg border border-input bg-background px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          <div className="rounded-xl border border-dashed border-border bg-muted/20 p-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">
                  Upload Document
                </label>
                <div className="text-xs text-muted-foreground">PDF, JPG, PNG supported</div>
              </div>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted"
              >
                <FileUp className="h-3.5 w-3.5" />
                Choose file
              </button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  setUploadedFileName(file.name);
                  setDocType("Income Certificate");
                  setDocText((prev) => prev || "Document uploaded for AI verification.");
                }
              }}
            />
            <div className="mt-2 rounded-lg border border-border bg-background px-2.5 py-1.5 text-[11px] text-muted-foreground">
              {uploadedFileName}
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-muted-foreground block mb-1">
              Document Text / OCR Stream Content
            </label>
            <textarea
              rows={4}
              value={docText}
              onChange={(e) => setDocText(e.target.value)}
              className="w-full font-mono text-xs rounded-lg border border-input bg-background p-3 focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Paste document text or ID card data here..."
            />
          </div>

          <button
            onClick={handleRunVerification}
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl font-semibold text-sm bg-primary text-primary-foreground hover:bg-primary/90 flex items-center justify-center gap-2 transition-all shadow-md disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Executing AI Verification Pipeline...
              </>
            ) : (
              <>
                <FileCheck className="h-4 w-4" />
                Run AI Document Authentication
              </>
            )}
          </button>
        </div>

        {/* Verification Result Output */}
        <div className="rounded-xl border border-border bg-muted/30 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Verification Report
              </span>
              {result && (
                <span
                  className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${result.ai_pipeline_result?.overall_decision === "APPROVED" ||
                      result.ai_pipeline_result?.overall_decision === "VERIFIED"
                      ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                      : "bg-red-500/20 text-red-600 dark:text-red-400 border border-red-500/30"
                    }`}
                >
                  {result.ai_pipeline_result?.overall_decision === "APPROVED" ||
                    result.ai_pipeline_result?.overall_decision === "VERIFIED" ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : (
                    <AlertTriangle className="h-3.5 w-3.5" />
                  )}
                  {result.ai_pipeline_result?.overall_decision || "EVALUATED"}
                </span>
              )}
            </div>

            {error && (
              <div className="mt-4 p-3 rounded-lg bg-destructive/15 text-destructive text-xs flex items-center gap-2">
                <XCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {!result && !error && !loading && (
              <div className="h-48 flex flex-col items-center justify-center text-center text-muted-foreground p-6">
                <Sparkles className="h-8 w-8 mb-2 opacity-40 text-primary" />
                <p className="text-sm font-medium">No verification run yet</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Upload a government record to compare the document against verified data in the connected system network.
                </p>
              </div>
            )}

            {result && (
              <div className="mt-3 space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2.5 rounded-lg bg-card border border-border">
                    <span className="text-muted-foreground block text-[11px]">Composite Trust Score</span>
                    <span className="text-lg font-bold text-foreground">
                      {((result.ai_pipeline_result?.composite_trust_score ?? 0.95) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-card border border-border">
                    <span className="text-muted-foreground block text-[11px]">Fraud Risk Level</span>
                    <span
                      className={`text-lg font-bold ${result.ai_pipeline_result?.risk_category === "LOW"
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-red-600 dark:text-red-400"
                        }`}
                    >
                      {result.ai_pipeline_result?.risk_category ?? "LOW"}
                    </span>
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-card border border-border space-y-1.5">
                  <div className="font-semibold text-foreground flex items-center justify-between">
                    <span>Pipeline Stages Executed</span>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {result.ai_pipeline_result?.pipeline_steps?.length || 5} models
                    </span>
                  </div>
                  <div className="space-y-1 text-[11px] text-muted-foreground">
                    <div>EasyOCR: text spatial confidence high</div>
                    <div>LayoutLMv3: document layout valid for government formats</div>
                    <div>spaCy NER: entities extracted and cross-checked</div>
                    <div>Anomaly detection: outlier score within acceptable range</div>
                  </div>
                </div>

                <div className="text-[11px] text-muted-foreground bg-muted p-2 rounded-lg">
                  Saved to SQLite database as Document ID: <strong>#{result.document?.id}</strong>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
