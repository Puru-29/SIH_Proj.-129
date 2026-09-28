import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ArrowLeft, ArrowRight, Check, FileCheck2, Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { GovernmentService, RecordItem } from "@/services/api";
import {
  type MeshApplication,
  type MeshDepartment,
  type MeshDocument,
  type MeshNodePlatform,
  type MeshService,
  type ServiceFormField,
  type ServiceFormSchema,
  api,
} from "@/lib/api";
import { getApplicationServiceConfig } from "@/lib/govflow/application-config";

type Props = {
  service: GovernmentService;
  records: RecordItem[];
  citizenAddress: string;
  onBack: () => void;
  onTrack: (referenceId: string) => void;
};

type WizardStep = {
  id: "service" | "information" | "records" | "consent" | "documents" | "review" | "submit";
  label: string;
};

const normalize = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");

function verifiedDocumentMatch(requiredDocument: string, documents: MeshDocument[]) {
  const requested = normalize(requiredDocument);
  const aliases: Record<string, string[]> = {
    identityproof: ["aadhaarcard", "identitydocuments"],
    incomeproof: ["incomecertificate"],
    addressproof: ["domicilecertificate"],
    academicmarksheet: ["educationrecord"],
    studentidentityproof: ["aadhaarcard"],
    bankaccountproof: ["bankpassbook"],
    ownershipdocument: ["propertydocument"],
    propertytaxreceipt: ["propertytaxreceipt"],
  };
  const names = [requested, ...(aliases[requested] ?? [])];
  return documents.find(
    (document) =>
      document.is_verified &&
      names.some(
        (name) =>
          normalize(document.title).includes(name) ||
          normalize(document.doc_type).includes(name) ||
          name.includes(normalize(document.title)) ||
          name.includes(normalize(document.doc_type)),
      ),
  );
}

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error(`Could not read ${file.name}.`));
    reader.onload = () => {
      if (typeof reader.result !== "string") {
        reject(new Error(`Could not read ${file.name}.`));
        return;
      }
      resolve(reader.result.split(",")[1] ?? "");
    };
    reader.readAsDataURL(file);
  });
}

function backendServiceFor(
  configNames: string[],
  services: MeshService[],
): MeshService | undefined {
  const names = configNames.map(normalize);
  return services.find(
    (service) => names.includes(normalize(service.name)) || names.includes(normalize(service.code)),
  );
}

function fieldProfileValue(
  fieldId: string,
  citizen: {
    full_name: string;
    email: string;
    phone?: string | null;
    aadhaar_last4?: string | null;
  },
  address: string,
): string {
  const profileValues: Record<string, string | null | undefined> = {
    full_name: citizen.full_name,
    email: citizen.email,
    mobile: citizen.phone?.replace(/\D/g, "").slice(-10),
    aadhaar_last4: citizen.aadhaar_last4,
    address,
  };
  return profileValues[fieldId] ?? "";
}

export function ApplicationWizard({ service, records, citizenAddress, onBack, onTrack }: Props) {
  const config = useMemo(() => getApplicationServiceConfig(service), [service]);
  const [stepIndex, setStepIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [setupError, setSetupError] = useState("");
  const [submissionError, setSubmissionError] = useState("");
  const [backendService, setBackendService] = useState<MeshService | null>(null);
  const [formSchema, setFormSchema] = useState<ServiceFormSchema | null>(null);
  const [citizen, setCitizen] = useState<Awaited<ReturnType<typeof api.getMe>>>(null);
  const [departments, setDepartments] = useState<MeshDepartment[]>([]);
  const [platforms, setPlatforms] = useState<MeshNodePlatform[]>([]);
  const [documents, setDocuments] = useState<MeshDocument[]>([]);
  const [formValues, setFormValues] = useState<Record<string, string | boolean>>({});
  const [selectedRecords, setSelectedRecords] = useState<Record<string, string>>({});
  const [consentDecisions, setConsentDecisions] = useState<Record<string, "allow" | "deny">>({});
  const [consentIds, setConsentIds] = useState<Record<string, number>>({});
  const [uploadedFiles, setUploadedFiles] = useState<Record<string, File>>({});
  const [createdApplication, setCreatedApplication] = useState<MeshApplication | null>(null);
  const [exchangeResults, setExchangeResults] = useState<
    Array<{ department: string; status: string; transactionId: string }>
  >([]);

  const activeConsentRequirements = useMemo(
    () =>
      config.consentRequirements.filter(
        (requirement) =>
          !requirement.whenField || formValues[requirement.whenField] === requirement.whenValue,
      ),
    [config.consentRequirements, formValues],
  );

  const steps = useMemo<WizardStep[]>(
    () => [
      { id: "service", label: "Service" },
      { id: "information", label: "Information" },
      ...(config.requiredVerifiedRecords.length
        ? [{ id: "records" as const, label: "Verified Records" }]
        : []),
      ...(activeConsentRequirements.length ? [{ id: "consent" as const, label: "Consent" }] : []),
      ...(config.requiredDocuments.length
        ? [{ id: "documents" as const, label: "Documents" }]
        : []),
      { id: "review", label: "Review" },
      { id: "submit", label: "Submit" },
    ],
    [activeConsentRequirements.length, config],
  );
  const activeStep = steps[stepIndex]!;

  const requiredRecords = config.requiredVerifiedRecords.map((requirement) => ({
    requirement,
    record: records.find(
      (record) =>
        record.verificationStatus === "Verified" &&
        [requirement.name, ...(requirement.aliases ?? [])].some(
          (name) =>
            normalize(record.name).includes(normalize(name)) ||
            normalize(name).includes(normalize(record.name)),
        ) &&
        normalize(record.sourceDepartment).includes(normalize(requirement.sourceDepartment)),
    ),
  }));

  const visibleFields = useMemo(() => {
    const configuredFields = new Map(config.requiredInformation.map((field) => [field.id, field]));
    const fields = formSchema?.fields.filter((field) => !field.id.startsWith("consent_")) ?? [];
    return fields
      .filter((field) => {
        if (field.visible_if && formValues[field.visible_if.field] !== field.visible_if.equals)
          return false;
        const metadata = configuredFields.get(field.id);
        return !metadata?.recordKey || !selectedRecords[metadata.recordKey];
      })
      .map((field) => {
        const recordKey = configuredFields.get(field.id)?.recordKey;
        return {
          ...field,
          required: field.required && (!recordKey || !selectedRecords[recordKey]),
        };
      });
  }, [config.requiredInformation, formSchema, formValues, selectedRecords]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setSetupError("");
    Promise.all([api.getMe(), api.getServices(), api.getPlatforms(), api.getDepartments()])
      .then(async ([me, services, meshPlatforms, meshDepartments]) => {
        if (!me || me.role !== "citizen") {
          throw new Error("Sign in with a citizen account before starting an application.");
        }
        const citizenDocuments = await api.getDocuments(me.id);
        const match = backendServiceFor(config.backendServiceNames, services);
        if (!match) {
          throw new Error(`The backend does not have a service entry for ${service.name}.`);
        }
        const schema = await api.getServiceFormSchema(match.id);
        if (cancelled) return;
        setCitizen(me);
        setBackendService(match);
        setFormSchema(schema);
        setPlatforms(meshPlatforms);
        setDepartments(meshDepartments);
        setDocuments(citizenDocuments);
        setFormValues((current) => {
          const initial = Object.fromEntries(
            schema.fields
              .filter((field) => !field.id.startsWith("consent_"))
              .map((field) => [
                field.id,
                fieldProfileValue(field.id, me, citizenAddress) || field.default || "",
              ]),
          );
          return { ...initial, ...current };
        });
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setSetupError(
            error instanceof Error ? error.message : "Unable to prepare the application.",
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [citizenAddress, config, records, service.name]);

  const matchingVerifiedDocument = (name: string) => verifiedDocumentMatch(name, documents);
  const consentPurpose = (requirement: (typeof config.consentRequirements)[number]) =>
    `${requirement.purpose} | Data requested: ${requirement.dataRequested}`;

  const updateField = (field: ServiceFormField, value: string | boolean) => {
    setFormValues((current) => ({ ...current, [field.id]: value }));
  };

  const continueFromInformation = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const missing = visibleFields.find(
      (field) =>
        field.required &&
        (formValues[field.id] === undefined ||
          formValues[field.id] === "" ||
          formValues[field.id] === false),
    );
    if (missing) {
      toast.error(`${missing.label} is required.`);
      return;
    }
    setStepIndex((current) => Math.min(steps.length - 1, current + 1));
  };

  const setRecordChoice = (key: string, recordId: string | null) => {
    setSelectedRecords((current) => {
      const next = { ...current };
      if (recordId) next[key] = recordId;
      else delete next[key];
      return next;
    });
  };

  const saveConsentDecision = async (
    requirement: (typeof config.consentRequirements)[number],
    decision: "allow" | "deny",
  ) => {
    if (!citizen || !backendService) {
      setSubmissionError("Citizen and service details must load before recording consent.");
      return;
    }
    const sourceDepartment = departments.find((department) =>
      normalize(department.name).includes(normalize(requirement.sourceDepartment)),
    );
    const sourcePlatform = sourceDepartment
      ? platforms.find((platform) => platform.department_id === sourceDepartment.id)
      : undefined;
    const targetPlatform = platforms.find((platform) => platform.id === backendService.platform_id);
    if (!sourcePlatform || !targetPlatform) {
      setSubmissionError(
        `No connected platform is configured for ${requirement.sourceDepartment} data.`,
      );
      return;
    }
    setSubmissionError("");
    try {
      const consent = await api.createConsent({
        purpose: consentPurpose(requirement),
        source_platform_id: sourcePlatform.id,
        target_platform_id: targetPlatform.id,
        citizen_id: citizen.id,
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
        status: decision === "allow" ? "granted" : "denied",
      });
      setConsentIds((current) => ({ ...current, [requirement.key]: consent.id }));
      setConsentDecisions((current) => ({ ...current, [requirement.key]: decision }));
      toast.success(decision === "allow" ? "Consent recorded." : "Consent denial recorded.");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to save your consent decision.";
      setSubmissionError(message);
      toast.error(message);
    }
  };

  const submitApplication = async () => {
    if (!citizen || !backendService || !formSchema) {
      toast.error("The service application configuration is incomplete.");
      return;
    }
    const missingDocument = config.requiredDocuments.find(
      (document) => !matchingVerifiedDocument(document) && !uploadedFiles[document],
    );
    if (missingDocument) {
      setSubmissionError(`Upload ${missingDocument} or use a verified document already on file.`);
      setStepIndex(steps.findIndex((step) => step.id === "documents"));
      return;
    }
    setSubmitting(true);
    setSubmissionError("");
    let applicationCreated = false;
    let applicationReference = "";
    try {
      const submittedData = Object.fromEntries(
        formSchema.fields
          .filter((field) => !field.id.startsWith("consent_"))
          .filter(
            (field) =>
              !config.requiredInformation.some(
                (configured) =>
                  configured.recordKey &&
                  selectedRecords[configured.recordKey] &&
                  configured.id === field.id,
              ),
          )
          .filter(
            (field) =>
              !field.visible_if || formValues[field.visible_if.field] === field.visible_if.equals,
          )
          .filter((field) => formValues[field.id] !== undefined && formValues[field.id] !== "")
          .map((field) => [field.id, formValues[field.id]]),
      );
      const consentGranted =
        activeConsentRequirements.length > 0 &&
        activeConsentRequirements.every(
          (requirement) => consentDecisions[requirement.key] === "allow",
        );
      const application = await api.createApplication({
        citizen_id: citizen.id,
        service_id: backendService.id,
        form_data: submittedData,
        verified_records: selectedRecords,
        consent: consentGranted,
        remarks: `Submitted through the service-specific GovFlow application wizard. Connected departments: ${config.connectedDepartments.join(", ")}.`,
      });
      applicationCreated = true;
      applicationReference = application.reference_id;
      setCreatedApplication(application);

      for (const requirement of activeConsentRequirements) {
        if (consentDecisions[requirement.key] !== "allow") continue;
        const consentId = consentIds[requirement.key];
        if (!consentId) {
          throw new Error(
            `The ${requirement.sourceDepartment} consent is missing. External data was not requested.`,
          );
        }
        const result = await api.requestInteroperability({
          citizen_id: citizen.id,
          service_id: backendService.id,
          application_id: application.id,
          requesting_department: config.department,
          source_department: requirement.sourceDepartment,
          data_requested: requirement.dataRequested,
          purpose: consentPurpose(requirement),
          consent_id: consentId,
        });
        if (result.status !== "success" && result.status !== "completed") {
          throw new Error(
            result.message || `The ${requirement.sourceDepartment} data request was not completed.`,
          );
        }
        setExchangeResults((current) => [
          ...current,
          {
            department: requirement.sourceDepartment,
            status: result.status,
            transactionId: result.transactionId,
          },
        ]);
      }

      for (const [documentName, file] of Object.entries(uploadedFiles)) {
        const image = await readFileAsBase64(file);
        await api.verifyDocument({
          title: documentName,
          doc_type: documentName,
          owner_id: citizen.id,
          application_id: application.id,
          image_base64: image,
          citizen_full_name: citizen.full_name,
          ...(citizen.aadhaar_last4 ? { citizen_aadhaar_last4: citizen.aadhaar_last4 } : {}),
          applicant_remarks: `Required document for ${service.name}.`,
        });
      }

      const updated = await api.getApplication(application.id);
      const workflow = await api.getApplicationWorkflow(application.id);
      const trackedApplication = updated ? { ...application, ...updated } : application;
      setCreatedApplication({
        ...trackedApplication,
        workflow: workflow ?? trackedApplication.workflow ?? [],
      });
      toast.success(`Application submitted. Reference: ${application.reference_id}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Application submission failed.";
      setSubmissionError(message);
      toast.error(
        applicationCreated
          ? `Application ${applicationReference} was created, but a later step failed: ${message}`
          : message,
      );
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (field: ServiceFormField) => {
    const metadata = config.requiredInformation.find((configured) => configured.id === field.id);
    const value = formValues[field.id] ?? field.default ?? "";
    const fieldLabel = field.label;
    const commonProps = {
      id: field.id,
      name: field.id,
      required: field.required,
      "aria-describedby": field.help_text ? `${field.id}-help` : undefined,
    };
    return (
      <div className="application-field" key={field.id}>
        <label htmlFor={field.id}>
          {fieldLabel}
          {field.required ? " *" : ""}
        </label>
        {field.type === "select" ? (
          <select
            {...commonProps}
            value={String(value)}
            onChange={(event) => updateField(field, event.target.value)}
          >
            <option value="">Select {fieldLabel.toLowerCase()}</option>
            {(field.options ?? []).map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        ) : field.type === "checkbox" ? (
          <input
            {...commonProps}
            type="checkbox"
            checked={Boolean(value)}
            onChange={(event) => updateField(field, event.target.checked)}
          />
        ) : (
          <Input
            {...commonProps}
            type={field.type === "number" ? "number" : (field.type ?? "text")}
            value={String(value)}
            maxLength={field.max_length}
            pattern={field.pattern}
            onChange={(event) => updateField(field, event.target.value)}
          />
        )}
        {metadata?.recordKey && selectedRecords[metadata.recordKey] ? (
          <p className="application-verified-hint">
            This information will be taken from your verified record.
          </p>
        ) : null}
        {field.help_text ? (
          <p id={`${field.id}-help`} className="application-field-help">
            {field.help_text}
          </p>
        ) : null}
      </div>
    );
  };

  if (createdApplication) {
    const workflow = createdApplication.workflow ?? [];
    return (
      <Card className="application-wizard application-tracking">
        <CardHeader className="application-wizard-header application-tracking-header">
          <span className="citizen-eyebrow">Application tracking</span>
          <CardTitle>{service.name} submitted</CardTitle>
          <p>
            Reference: <strong>{createdApplication.reference_id}</strong>
          </p>
          <p>
            {createdApplication.department_name ?? config.department} · {createdApplication.status}
          </p>
        </CardHeader>
        <CardContent className="application-wizard-content">
          {submissionError ? (
            <p role="alert" className="application-error">
              {submissionError}
            </p>
          ) : null}
          <h2>Processing timeline</h2>
          <ol className="application-timeline">
            {workflow.map((stage) => (
              <li key={stage.key} className={`application-timeline-stage ${stage.status}`}>
                <span className="application-timeline-dot" aria-hidden="true" />
                <div>
                  <strong>{stage.label}</strong>
                  <p>{stage.detail || stage.status.replaceAll("_", " ")}</p>
                </div>
                <span className="application-stage-status">
                  {stage.status.replaceAll("_", " ")}
                </span>
              </li>
            ))}
          </ol>
          {exchangeResults.length ? (
            <section className="application-exchanges">
              <h2>Government system exchanges</h2>
              {exchangeResults.map((result) => (
                <p key={result.transactionId}>
                  {result.department}: {result.status} · {result.transactionId}
                </p>
              ))}
            </section>
          ) : null}
          <div className="application-wizard-actions">
            <Button onClick={() => onTrack(createdApplication.reference_id)}>
              Track Application
            </Button>
            <Button variant="outline" onClick={onBack}>
              Back to Services
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <div className="application-wizard-loading" role="status">
        <Loader2 className="size-5 animate-spin" /> Preparing {service.name} application…
      </div>
    );
  }

  if (setupError) {
    return (
      <Card className="application-wizard">
        <CardHeader>
          <CardTitle>Unable to start this application</CardTitle>
          <p>{setupError}</p>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={onBack}>
            Back to Services
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="application-wizard">
      <CardHeader className="application-wizard-header">
        <div>
          <span className="citizen-eyebrow">Service application</span>
          <CardTitle>{service.name}</CardTitle>
          <p>
            {config.department} · Estimated processing: {service.estimatedProcessingTime}
          </p>
        </div>
        <span className="application-wizard-count">
          Step {stepIndex + 1} of {steps.length}
        </span>
      </CardHeader>
      <CardContent className="application-wizard-content">
        <nav className="application-stepper" aria-label="Application progress">
          <ol>
            {steps.map((step, index) => (
              <li
                key={step.id}
                className={
                  index === stepIndex ? "is-current" : index < stepIndex ? "is-complete" : ""
                }
              >
                <span className="application-step-number">
                  {index < stepIndex ? <Check aria-hidden="true" /> : index + 1}
                </span>
                <span>{step.label}</span>
              </li>
            ))}
          </ol>
        </nav>

        {submissionError ? (
          <p role="alert" className="application-error">
            {submissionError}
          </p>
        ) : null}

        <section
          className="application-step-panel"
          aria-labelledby={`application-step-${activeStep.id}`}
        >
          <h2 id={`application-step-${activeStep.id}`}>{activeStep.label}</h2>

          {activeStep.id === "service" ? (
            <div className="application-service-details">
              <p>{config.description}</p>
              <dl>
                <div>
                  <dt>Department</dt>
                  <dd>{config.department}</dd>
                </div>
                <div>
                  <dt>Purpose</dt>
                  <dd>{service.description}</dd>
                </div>
                <div>
                  <dt>Processing time</dt>
                  <dd>{service.estimatedProcessingTime}</dd>
                </div>
                <div>
                  <dt>Fee</dt>
                  <dd>{service.fee}</dd>
                </div>
                <div>
                  <dt>Connected systems</dt>
                  <dd>{config.connectedDepartments.join(" · ")}</dd>
                </div>
                <div>
                  <dt>Workflow</dt>
                  <dd>{config.interoperabilityWorkflow.join(" → ")}</dd>
                </div>
              </dl>
              <h3>Required information</h3>
              <p>
                {config.requiredInformation.map((field) => field.label).join(" · ") ||
                  "Citizen identity and service details"}
              </p>
              <h3>Required documents</h3>
              <p>{config.requiredDocuments.join(" · ") || "No documents required"}</p>
            </div>
          ) : null}

          {activeStep.id === "information" ? (
            <form
              id="application-information-form"
              className="application-information-form"
              onSubmit={continueFromInformation}
            >
              <div className="application-citizen-summary">
                <ShieldCheck aria-hidden="true" />
                <div>
                  <strong>{citizen?.full_name}</strong>
                  <span>
                    {citizen?.email} · Citizen information is linked to your signed-in account.
                  </span>
                </div>
              </div>
              {visibleFields.length ? (
                <div className="application-fields-grid">{visibleFields.map(renderField)}</div>
              ) : (
                <p>
                  All required service information is already available from your verified records.
                </p>
              )}
            </form>
          ) : null}

          {activeStep.id === "records" ? (
            <div className="application-record-list">
              {requiredRecords.map(({ requirement, record }) => (
                <article className="application-record-card" key={requirement.key}>
                  <div>
                    <h3>{requirement.name}</h3>
                    <p>
                      Source: {record?.sourceDepartment ?? requirement.sourceDepartment} Department
                    </p>
                    <p>Status: {record ? "Verified" : "Information not available"}</p>
                  </div>
                  {record ? (
                    <div className="application-record-actions">
                      <Button
                        variant={
                          selectedRecords[requirement.key] === record.id ? "secondary" : "outline"
                        }
                        onClick={() =>
                          setRecordChoice(
                            requirement.key,
                            selectedRecords[requirement.key] === record.id ? null : record.id,
                          )
                        }
                      >
                        {selectedRecords[requirement.key] === record.id
                          ? "Using Existing Record"
                          : "Use Existing Record"}
                      </Button>
                      <p>
                        {selectedRecords[requirement.key] === record.id
                          ? "GovFlow will reuse this verified record and omit duplicate information fields."
                          : "Choose the verified record or enter the information yourself."}
                      </p>
                    </div>
                  ) : (
                    <div className="application-record-actions">
                      <p>
                        Information not available. Enter the required information and upload
                        supporting documents in the next steps.
                      </p>
                      <Button
                        variant="outline"
                        onClick={() =>
                          setStepIndex(steps.findIndex((step) => step.id === "information"))
                        }
                      >
                        Enter Information
                      </Button>
                    </div>
                  )}
                </article>
              ))}
            </div>
          ) : null}

          {activeStep.id === "consent" ? (
            <div className="application-consent-list">
              {activeConsentRequirements.map((requirement) => (
                <article className="application-consent-card" key={requirement.key}>
                  <h3>Share data with {config.department}</h3>
                  <dl>
                    <div>
                      <dt>Requesting department</dt>
                      <dd>{config.department}</dd>
                    </div>
                    <div>
                      <dt>Source department</dt>
                      <dd>{requirement.sourceDepartment}</dd>
                    </div>
                    <div>
                      <dt>Data requested</dt>
                      <dd>{requirement.dataRequested}</dd>
                    </div>
                    <div>
                      <dt>Purpose</dt>
                      <dd>{requirement.purpose}</dd>
                    </div>
                    <div>
                      <dt>Duration</dt>
                      <dd>24 hours or until revoked</dd>
                    </div>
                  </dl>
                  <div className="application-consent-actions">
                    <Button
                      disabled={Boolean(consentDecisions[requirement.key])}
                      onClick={() => void saveConsentDecision(requirement, "allow")}
                    >
                      Allow
                    </Button>
                    <Button
                      variant="outline"
                      disabled={Boolean(consentDecisions[requirement.key])}
                      onClick={() => void saveConsentDecision(requirement, "deny")}
                    >
                      Deny
                    </Button>
                    {consentDecisions[requirement.key] ? (
                      <strong>Decision saved: {consentDecisions[requirement.key]}</strong>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : null}

          {activeStep.id === "documents" ? (
            <div className="application-document-list">
              {config.requiredDocuments.map((document) => {
                const verified = matchingVerifiedDocument(document);
                return (
                  <article className="application-document-card" key={document}>
                    <div>
                      <FileCheck2 aria-hidden="true" />
                      <div>
                        <strong>{document}</strong>
                        <p>
                          {verified
                            ? `Verified record available in GovFlow as “${verified.title}” — no upload required.`
                            : "Upload a clear image of this required document."}
                        </p>
                      </div>
                    </div>
                    {verified ? (
                      <span className="application-document-status">
                        Verified: {verified.title}
                      </span>
                    ) : (
                      <label className="application-file-input">
                        Upload document
                        <Input
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          onChange={(event) => {
                            const file = event.currentTarget.files?.[0];
                            if (file)
                              setUploadedFiles((current) => ({ ...current, [document]: file }));
                          }}
                        />
                        {uploadedFiles[document] ? (
                          <span>{uploadedFiles[document].name}</span>
                        ) : null}
                      </label>
                    )}
                  </article>
                );
              })}
            </div>
          ) : null}

          {activeStep.id === "review" ? (
            <div className="application-review">
              <dl>
                <div>
                  <dt>Service</dt>
                  <dd>{service.name}</dd>
                </div>
                <div>
                  <dt>Department</dt>
                  <dd>{config.department}</dd>
                </div>
                <div>
                  <dt>Citizen</dt>
                  <dd>
                    {citizen?.full_name} · {citizen?.email}
                  </dd>
                </div>
                <div>
                  <dt>Information</dt>
                  <dd>
                    {Object.entries(formValues)
                      .filter(([, value]) => value !== "" && value !== false)
                      .map(([key, value]) => `${key.replaceAll("_", " ")}: ${String(value)}`)
                      .join(" · ") || "Provided by verified records"}
                  </dd>
                </div>
                <div>
                  <dt>Verified records</dt>
                  <dd>
                    {Object.keys(selectedRecords).length
                      ? Object.keys(selectedRecords)
                          .map(
                            (key) =>
                              config.requiredVerifiedRecords.find((item) => item.key === key)
                                ?.name ?? key,
                          )
                          .join(" · ")
                      : "None selected"}
                  </dd>
                </div>
                <div>
                  <dt>Consent</dt>
                  <dd>
                    {activeConsentRequirements.length
                      ? activeConsentRequirements
                          .map(
                            (item) =>
                              `${item.sourceDepartment}: ${consentDecisions[item.key] ?? "not decided"}`,
                          )
                          .join(" · ")
                      : "Not required for this service"}
                  </dd>
                </div>
                <div>
                  <dt>Documents</dt>
                  <dd>
                    {config.requiredDocuments
                      .map(
                        (name) =>
                          matchingVerifiedDocument(name)?.title ??
                          uploadedFiles[name]?.name ??
                          `${name} missing`,
                      )
                      .join(" · ") || "None required"}
                  </dd>
                </div>
                <div>
                  <dt>Connected workflow</dt>
                  <dd>{config.interoperabilityWorkflow.join(" → ")}</dd>
                </div>
              </dl>
              <div className="application-review-edit">
                <Button
                  variant="outline"
                  onClick={() => setStepIndex(steps.findIndex((step) => step.id === "information"))}
                >
                  Edit Information
                </Button>
                {steps.some((step) => step.id === "records") ? (
                  <Button
                    variant="outline"
                    onClick={() => setStepIndex(steps.findIndex((step) => step.id === "records"))}
                  >
                    Edit Records
                  </Button>
                ) : null}
                {steps.some((step) => step.id === "consent") ? (
                  <Button
                    variant="outline"
                    onClick={() => setStepIndex(steps.findIndex((step) => step.id === "consent"))}
                  >
                    Edit Consent
                  </Button>
                ) : null}
                {steps.some((step) => step.id === "documents") ? (
                  <Button
                    variant="outline"
                    onClick={() => setStepIndex(steps.findIndex((step) => step.id === "documents"))}
                  >
                    Edit Documents
                  </Button>
                ) : null}
              </div>
            </div>
          ) : null}

          {activeStep.id === "submit" ? (
            <div className="application-submit-summary">
              <p>
                Submitting creates a real application record and initializes the configured
                department workflow.
              </p>
              <p>
                <strong>{service.name}</strong> · {config.department} ·{" "}
                {service.estimatedProcessingTime}
              </p>
              <p>
                External data will only be requested where you recorded consent. Denied requests
                will not be sent to connected systems.
              </p>
              <Button onClick={() => void submitApplication()} disabled={submitting}>
                {submitting ? (
                  <>
                    <Loader2 className="size-4 animate-spin" /> Submitting application
                  </>
                ) : (
                  "Submit Application"
                )}
              </Button>
            </div>
          ) : null}
        </section>

        <div className="application-wizard-actions">
          <Button
            variant="outline"
            onClick={() => (stepIndex === 0 ? onBack() : setStepIndex((current) => current - 1))}
          >
            <ArrowLeft aria-hidden="true" /> {stepIndex === 0 ? "Back to Services" : "Previous"}
          </Button>
          {activeStep.id === "information" ? (
            <Button type="submit" form="application-information-form">
              Continue <ArrowRight aria-hidden="true" />
            </Button>
          ) : activeStep.id !== "submit" ? (
            <Button
              onClick={() => setStepIndex((current) => current + 1)}
              disabled={
                activeStep.id === "consent" &&
                activeConsentRequirements.some((requirement) => !consentDecisions[requirement.key])
              }
            >
              Continue <ArrowRight aria-hidden="true" />
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
