import type { DepartmentName, GovernmentService } from "@/services/api";

export type ApplicationFieldConfig = {
  id: string;
  label: string;
  required: boolean;
  type?: "text" | "email" | "tel" | "date" | "number" | "select" | "checkbox";
  options?: string[];
  recordKey?: string;
};

export type VerifiedRecordRequirement = {
  key: string;
  name: string;
  aliases?: string[];
  sourceDepartment: DepartmentName;
  sourceSystem?: string;
  fieldsCovered: string[];
  dataRequested: string;
};

export type ConsentRequirement = {
  key: string;
  sourceDepartment: DepartmentName;
  dataRequested: string;
  purpose: string;
  whenField?: string;
  whenValue?: string;
};

export type ApplicationServiceConfig = {
  serviceId: string;
  serviceName: string;
  aliases: string[];
  backendServiceNames: string[];
  department: DepartmentName;
  description: string;
  requiredInformation: ApplicationFieldConfig[];
  requiredDocuments: string[];
  requiredVerifiedRecords: VerifiedRecordRequirement[];
  consentRequirements: ConsentRequirement[];
  connectedDepartments: DepartmentName[];
  interoperabilityWorkflow: string[];
  processingStages: string[];
};

const serviceConfigs: ApplicationServiceConfig[] = [
  {
    serviceId: "income-certificate",
    serviceName: "Income Certificate",
    aliases: ["Income Certificate", "INC-CERT"],
    backendServiceNames: ["Income Certificate"],
    department: "Revenue",
    description: "Request an official income certificate for public-service eligibility.",
    requiredInformation: [
      {
        id: "family_income",
        label: "Annual family income",
        required: true,
        type: "number",
        recordKey: "income",
      },
      {
        id: "family_members",
        label: "Number of family members",
        required: true,
        type: "number",
        recordKey: "income",
      },
      {
        id: "address",
        label: "Residential address",
        required: true,
        type: "text",
        recordKey: "income",
      },
    ],
    requiredDocuments: ["Identity proof", "Income proof", "Address proof"],
    requiredVerifiedRecords: [
      {
        key: "income",
        name: "Income Certificate",
        sourceDepartment: "Revenue",
        sourceSystem: "Revenue Department",
        fieldsCovered: ["family_income", "family_members", "address"],
        dataRequested: "Verified income and residence details",
      },
    ],
    consentRequirements: [],
    connectedDepartments: ["Revenue"],
    interoperabilityWorkflow: ["Revenue", "GovFlow", "Revenue"],
    processingStages: [
      "Application Submitted",
      "Income Verification",
      "Document Review",
      "Certificate Issued",
    ],
  },
  {
    serviceId: "scholarship",
    serviceName: "Scholarship",
    aliases: [
      "Scholarship",
      "Pre-Matric Scholarship",
      "Post-Matric Scholarship",
      "SCH-PRE",
      "SCH-POST",
    ],
    backendServiceNames: ["Post-Matric Scholarship"],
    department: "Social Welfare",
    description: "Apply for education funding using verified student and household records.",
    requiredInformation: [
      { id: "institution", label: "School or institution", required: true, recordKey: "student" },
      { id: "course_name", label: "Course or grade", required: true, recordKey: "student" },
      { id: "academic_year", label: "Academic year", required: true, recordKey: "student" },
      {
        id: "previous_marks",
        label: "Previous examination percentage",
        required: true,
        type: "number",
        recordKey: "student",
      },
      {
        id: "family_income",
        label: "Annual family income",
        required: true,
        type: "number",
        recordKey: "income",
      },
      { id: "guardian_name", label: "Parent or guardian name", required: true },
    ],
    requiredDocuments: ["Student identity proof", "Academic marksheet", "Bank account proof"],
    requiredVerifiedRecords: [
      {
        key: "student",
        name: "Student Record",
        aliases: ["Education Record", "Student Verification"],
        sourceDepartment: "Education",
        sourceSystem: "Education Department",
        fieldsCovered: ["institution", "course_name", "academic_year", "previous_marks"],
        dataRequested: "Student identity, enrolment and academic standing",
      },
      {
        key: "income",
        name: "Income Certificate",
        sourceDepartment: "Revenue",
        sourceSystem: "Revenue Department",
        fieldsCovered: ["family_income"],
        dataRequested: "Verified household income and eligibility category",
      },
    ],
    consentRequirements: [
      {
        key: "education",
        sourceDepartment: "Education",
        dataRequested: "Student enrolment and academic record",
        purpose: "Scholarship eligibility verification",
      },
      {
        key: "revenue",
        sourceDepartment: "Revenue",
        dataRequested: "Verified household income record",
        purpose: "Scholarship means-test and eligibility verification",
      },
    ],
    connectedDepartments: ["Social Welfare", "Education", "Revenue"],
    interoperabilityWorkflow: [
      "Social Welfare",
      "GovFlow",
      "Revenue",
      "GovFlow",
      "Education",
      "GovFlow",
      "Social Welfare",
    ],
    processingStages: [
      "Application Submitted",
      "Consent Verified",
      "Income Verification",
      "Education Verification",
      "Eligibility Review",
      "Scholarship Decision",
    ],
  },
  {
    serviceId: "driving-licence",
    serviceName: "Driving Licence",
    aliases: ["Driving Licence", "Driving License", "DL-APPLICATION"],
    backendServiceNames: ["Driving Licence"],
    department: "Transport",
    description:
      "Apply for or renew a driving licence with identity, address and appointment checks.",
    requiredInformation: [
      {
        id: "licence_application_type",
        label: "Application type",
        required: true,
        type: "select",
        options: ["New licence", "Renewal"],
      },
      {
        id: "driving_category",
        label: "Vehicle category",
        required: true,
        type: "select",
        options: ["Two-wheeler", "Four-wheeler", "Commercial"],
      },
      {
        id: "existing_licence_number",
        label: "Existing licence number (renewal only)",
        required: false,
      },
      {
        id: "appointment_preference",
        label: "Preferred appointment date",
        required: true,
        type: "date",
      },
      { id: "address", label: "Residential address", required: true, recordKey: "address" },
    ],
    requiredDocuments: [
      "Identity proof",
      "Medical certificate",
      "Learner licence (new application)",
    ],
    requiredVerifiedRecords: [
      {
        key: "licence",
        name: "Driving Licence",
        sourceDepartment: "Transport",
        sourceSystem: "Transport Department",
        fieldsCovered: ["existing_licence_number"],
        dataRequested: "Existing licence status and vehicle class",
      },
      {
        key: "address",
        name: "Address Record",
        sourceDepartment: "Revenue",
        sourceSystem: "Revenue Department",
        fieldsCovered: ["address"],
        dataRequested: "Verified residential address",
      },
    ],
    consentRequirements: [
      {
        key: "licence",
        sourceDepartment: "Transport",
        dataRequested: "Existing driving licence status and vehicle class",
        purpose: "Driving licence renewal and class verification",
        whenField: "licence_application_type",
        whenValue: "Renewal",
      },
      {
        key: "address",
        sourceDepartment: "Revenue",
        dataRequested: "Verified residential address",
        purpose: "Driving licence address verification",
      },
    ],
    connectedDepartments: ["Transport", "Revenue"],
    interoperabilityWorkflow: ["Transport", "GovFlow", "Revenue", "GovFlow", "Transport"],
    processingStages: [
      "Application Submitted",
      "Identity Verified",
      "Address Verified",
      "Documents Reviewed",
      "Appointment Scheduled",
      "Licence Decision",
    ],
  },
  {
    serviceId: "property-verification",
    serviceName: "Property Verification",
    aliases: ["Property Verification", "Land Record Verification", "Property Record"],
    backendServiceNames: ["Property Verification"],
    department: "Municipal",
    description: "Verify property ownership and civic details across municipal and land systems.",
    requiredInformation: [
      { id: "property_id", label: "Property ID", required: true },
      { id: "survey_number", label: "Survey number", required: true },
      { id: "property_address", label: "Property address", required: true },
      { id: "verification_purpose", label: "Reason for verification", required: true },
    ],
    requiredDocuments: ["Property tax receipt", "Ownership document", "Identity proof"],
    requiredVerifiedRecords: [
      {
        key: "property",
        name: "Property Record",
        sourceDepartment: "Municipal",
        sourceSystem: "Municipal Department",
        fieldsCovered: ["property_id", "property_address"],
        dataRequested: "Municipal property assessment and ownership record",
      },
      {
        key: "land",
        name: "Land Record",
        sourceDepartment: "Revenue",
        sourceSystem: "Revenue Department",
        fieldsCovered: ["survey_number"],
        dataRequested: "Land ownership and survey record",
      },
    ],
    consentRequirements: [
      {
        key: "municipal",
        sourceDepartment: "Municipal",
        dataRequested: "Property assessment and ownership record",
        purpose: "Property verification request",
      },
      {
        key: "revenue",
        sourceDepartment: "Revenue",
        dataRequested: "Land title and survey record",
        purpose: "Property ownership cross-verification",
      },
    ],
    connectedDepartments: ["Municipal", "Revenue"],
    interoperabilityWorkflow: ["Municipal", "GovFlow", "Revenue", "GovFlow", "Municipal"],
    processingStages: [
      "Application Submitted",
      "Municipal Record Requested",
      "Land Record Verified",
      "Ownership Validated",
      "Verification Issued",
    ],
  },
];

const normalize = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");

const backendServiceAliases: Record<string, string[]> = {
  "domicile-certificate": ["Residence Certificate"],
  scholarship: ["Post-Matric Scholarship"],
  pension: ["Senior Citizen Pension"],
  "welfare-scheme": ["Direct Benefit Subsidy"],
};

const supportedDepartmentSystems: Array<{ pattern: RegExp; department: DepartmentName }> = [
  { pattern: /revenue|land record|survey|income|domicile|caste/i, department: "Revenue" },
  { pattern: /education|academic|student|institution/i, department: "Education" },
  { pattern: /social welfare|welfare/i, department: "Social Welfare" },
  { pattern: /transport|licen[cs]e|rto|vehicle/i, department: "Transport" },
  {
    pattern: /municipal|civic|property|birth registration|death registration/i,
    department: "Municipal",
  },
  { pattern: /employment|skill|training/i, department: "Employment" },
];

export function getApplicationServiceConfig(service: GovernmentService): ApplicationServiceConfig {
  const serviceName = normalize(service.name);
  const serviceId = normalize(service.id);
  const configured = serviceConfigs.find((config) =>
    [config.serviceId, config.serviceName, ...config.aliases].some((alias) => {
      const normalizedAlias = normalize(alias);
      return normalizedAlias === serviceName || normalizedAlias === serviceId;
    }),
  );
  if (configured) return configured;

  const connectedDepartments = [
    ...new Set([
      service.department,
      ...service.interoperabilityRequirements.flatMap((requirement) => {
        const match = supportedDepartmentSystems.find(({ pattern }) => pattern.test(requirement));
        return match ? [match.department] : [];
      }),
    ]),
  ];
  const consentRequirements = service.interoperabilityRequirements.flatMap((requirement, index) => {
    const source = supportedDepartmentSystems.find(({ pattern }) =>
      pattern.test(requirement),
    )?.department;
    if (!source || source === service.department) return [];
    return [
      {
        key: `external-${index + 1}`,
        sourceDepartment: source,
        dataRequested: requirement,
        purpose: `${service.name} eligibility and application verification`,
      },
    ];
  });
  const normalizedService = normalize(service.name);
  const existingRecordName = normalizedService.includes("domicile")
    ? "Domicile"
    : normalizedService.includes("student") || normalizedService.includes("education")
      ? "Education Record"
      : normalizedService.includes("licence")
        ? "Driving Licence"
        : normalizedService.includes("scholarship") ||
            normalizedService.includes("welfare") ||
            normalizedService.includes("pension")
          ? "Income Certificate"
          : service.name;
  const aliases = backendServiceAliases[service.id] ?? [service.name];
  return {
    serviceId: service.id,
    serviceName: service.name,
    aliases,
    backendServiceNames: aliases,
    department: service.department,
    description: service.description,
    requiredInformation: service.requiredData.map((label, index) => ({
      id: `service_information_${index + 1}`,
      label,
      required: true,
    })),
    requiredDocuments: service.requiredDocuments,
    requiredVerifiedRecords: [
      {
        key: `record-${service.id}`,
        name: existingRecordName,
        sourceDepartment: service.department,
        sourceSystem: `${service.department} Department`,
        fieldsCovered: [],
        dataRequested: `${service.name} record and eligibility details`,
      },
    ],
    consentRequirements,
    connectedDepartments,
    interoperabilityWorkflow: [
      service.department,
      "GovFlow",
      ...connectedDepartments
        .filter((department) => department !== service.department)
        .flatMap((department) => [department, "GovFlow"]),
      service.department,
    ],
    processingStages: service.workflow,
  };
}
