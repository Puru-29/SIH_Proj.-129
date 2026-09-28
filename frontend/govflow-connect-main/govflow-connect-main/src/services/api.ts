import { api } from "@/lib/api";

export type DepartmentName =
  | "Revenue"
  | "Education"
  | "Social Welfare"
  | "Transport"
  | "Municipal"
  | "Employment"
  | "UIDAI";

export type ApplicationStatus =
  | "Submitted"
  | "Under Verification"
  | "Documents Verified"
  | "Department Review"
  | "Officer Review"
  | "Approved"
  | "Rejected"
  | "Action Required"
  | "Appointment Required";

export type ConsentStatus = "Awaiting Approval" | "Granted" | "Revoked" | "Expired";

export type NotificationType = "Application" | "Consent" | "Document" | "System";

export type CitizenProfile = {
  id: string;
  citizenId: string;
  fullName: string;
  email: string;
  phone: string;
  address: string;
  preferredLanguage: string;
  verifiedMobile: boolean;
  verifiedEmail: boolean;
  profileImage?: string;
};

export type GovernmentService = {
  id: string;
  name: string;
  department: DepartmentName;
  description: string;
  processingTime: string;
  estimatedProcessingTime: string;
  fee: string;
  requiredDocuments: string[];
  requiredData: string[];
  workflow: string[];
  interoperabilityRequirements: string[];
  onlineAvailability: boolean;
  category: "Revenue" | "Education" | "Social Welfare" | "Transport" | "Municipal" | "Employment";
  popular?: boolean;
  recommended?: boolean;
  recentlyUsed?: boolean;
};

export type RecordItem = {
  id: string;
  name: string;
  sourceDepartment: DepartmentName;
  sourceSystem: string;
  sourceType: "Department" | "System" | "External";
  verificationStatus: "Verified" | "Pending" | "Needs Review";
  retrievedAt: string;
  status: "Verified";
  lastVerified: string;
  usedByApplications: string[];
};

export type ApplicationItem = {
  id: string;
  service: string;
  department: DepartmentName;
  submittedDate: string;
  status: ApplicationStatus;
  progress: number;
  lastUpdated: string;
  applicationId: string;
  timeline: Array<{ label: string; date: string; completed: boolean; inProgress?: boolean }>; 
  interdepartmentalEvents: string[];
  expectedNextStep: string;
  contact: string;
};

export type ConsentRequest = {
  id: string;
  department: DepartmentName;
  data: string;
  purpose: string;
  status: ConsentStatus;
  grantedOn?: string;
  expires?: string;
  sourceDepartment?: DepartmentName;
};

export type NotificationItem = {
  id: string;
  title: string;
  description: string;
  time: string;
  type: NotificationType;
  read: boolean;
  relatedApplication?: string;
};

export type DocumentItem = {
  id: string;
  name: string;
  category: "Identity Documents" | "Certificates" | "Education" | "Income" | "Address" | "Other";
  issuingDepartment: DepartmentName;
  issueDate: string;
  expiryDate?: string;
  verificationStatus: "Verified" | "Pending" | "Needs Review";
};

export type GrievanceItem = {
  id: string;
  category: string;
  relatedApplication: string;
  department: DepartmentName;
  description: string;
  priority: "Low" | "Medium" | "High";
  status: "Submitted" | "Assigned" | "Under Review" | "Resolved" | "Closed";
};

export const governmentServices: GovernmentService[] = [
  {
    id: "income-certificate",
    name: "Income Certificate",
    department: "Revenue",
    description: "Request a verified income record for education, subsidy and public support eligibility.",
    processingTime: "7-10 working days",
    estimatedProcessingTime: "7-10 working days",
    fee: "₹50",
    requiredDocuments: ["Aadhaar card", "Salary slip or income proof", "Address proof"],
    requiredData: ["Annual family income", "Employment details", "Residence details"],
    workflow: ["Verification", "Revenue check", "Income validation", "Certificate issuance"],
    interoperabilityRequirements: ["Revenue Department", "Income Tax records", "Aadhaar e-KYC"],
    onlineAvailability: true,
    category: "Revenue",
    popular: true,
    recommended: true,
  },
  {
    id: "domicile-certificate",
    name: "Domicile Certificate",
    department: "Revenue",
    description: "Proof of residence issued from verified municipal and civic records.",
    processingTime: "6-8 working days",
    estimatedProcessingTime: "6-8 working days",
    fee: "₹30",
    requiredDocuments: ["Address proof", "Voter ID", "Aadhaar card"],
    requiredData: ["Current residence", "Locality verification", "Duration of stay"],
    workflow: ["Residence check", "Municipal validation", "Approval", "Certificate issuance"],
    interoperabilityRequirements: ["Municipal records", "Electoral roll", "Address verification"],
    onlineAvailability: true,
    category: "Revenue",
    popular: true,
  },
  {
    id: "caste-certificate",
    name: "Caste Certificate",
    department: "Revenue",
    description: "Request caste verification and category certification with consent-based records retrieval.",
    processingTime: "8-12 working days",
    estimatedProcessingTime: "8-12 working days",
    fee: "₹40",
    requiredDocuments: ["Identity proof", "Family records", "Residence proof"],
    requiredData: ["Family category", "Address", "Supporting declaration"],
    workflow: ["Request review", "Family record verification", "Department approval", "Certificate issuance"],
    interoperabilityRequirements: ["Revenue records", "Family registry", "District verification"],
    onlineAvailability: true,
    category: "Revenue",
  },
  {
    id: "land-record-verification",
    name: "Land Record Verification",
    department: "Revenue",
    description: "Verify land title, ownership and extraction records across the connected revenue systems.",
    processingTime: "10-15 working days",
    estimatedProcessingTime: "10-15 working days",
    fee: "₹75",
    requiredDocuments: ["Survey number", "Khata details", "Property ID"],
    requiredData: ["Plot details", "Ownership record", "Mutation history"],
    workflow: ["Ownership lookup", "Legacy record check", "Status validation", "Verification report"],
    interoperabilityRequirements: ["Land records system", "Survey database", "Property registry"],
    onlineAvailability: false,
    category: "Revenue",
  },
  {
    id: "scholarship",
    name: "Scholarship",
    department: "Social Welfare",
    description: "Support for education and higher study funding using verified academic and income records.",
    processingTime: "7-10 working days",
    estimatedProcessingTime: "7-10 working days",
    fee: "Free",
    requiredDocuments: ["Income certificate", "Academic marksheets", "Bank passbook"],
    requiredData: ["Family income", "Enrollment details", "Academic performance"],
    workflow: ["Student verification", "Income check", "Education validation", "Scholarship approval"],
    interoperabilityRequirements: ["Revenue Department", "Education Department", "Banking verification"],
    onlineAvailability: true,
    category: "Social Welfare",
    popular: true,
    recommended: true,
  },
  {
    id: "student-verification",
    name: "Student Verification",
    department: "Education",
    description: "Verify student identity, enrolment and academic status across participating institutions.",
    processingTime: "4-6 working days",
    estimatedProcessingTime: "4-6 working days",
    fee: "₹0",
    requiredDocuments: ["Student ID", "Enrollment proof", "Institution reference"],
    requiredData: ["Student identifier", "Institute status", "Current course details"],
    workflow: ["Identifier check", "Academic record retrieval", "Institution validation", "Verification result"],
    interoperabilityRequirements: ["Education Department", "Institution registry", "Student database"],
    onlineAvailability: true,
    category: "Education",
  },
  {
    id: "education-certificate",
    name: "Education Certificate",
    department: "Education",
    description: "Generate academic records for universities, institutions and eligibility-based programmes.",
    processingTime: "5-7 working days",
    estimatedProcessingTime: "5-7 working days",
    fee: "₹0",
    requiredDocuments: ["Academic records", "College ID", "Previous certificates"],
    requiredData: ["Course details", "Academic period", "Institution details"],
    workflow: ["Record retrieval", "Institution review", "Certificate generation", "Final issue"],
    interoperabilityRequirements: ["Education Department", "Institution verification", "Academic registry"],
    onlineAvailability: true,
    category: "Education",
  },
  {
    id: "driving-licence",
    name: "Driving Licence",
    department: "Transport",
    description: "Apply for or renew a driving licence using verified identity and address records.",
    processingTime: "15-20 days",
    estimatedProcessingTime: "15-20 days",
    fee: "₹600",
    requiredDocuments: ["Aadhaar card", "Address proof", "Medical certificate"],
    requiredData: ["Driving category", "Address", "Identity details"],
    workflow: ["Eligibility check", "Address verification", "Driving test scheduling", "Licence issuance"],
    interoperabilityRequirements: ["Transport Department", "Identity records", "Address verification"],
    onlineAvailability: true,
    category: "Transport",
    popular: true,
  },
  {
    id: "vehicle-registration",
    name: "Vehicle Registration",
    department: "Transport",
    description: "Complete vehicle registration and ownership validation across transport and insurance systems.",
    processingTime: "14-21 days",
    estimatedProcessingTime: "14-21 days",
    fee: "₹1,200",
    requiredDocuments: ["Insurance", "ID proof", "Vehicle documents"],
    requiredData: ["Vehicle details", "Owner identity", "Invoice / purchase record"],
    workflow: ["Ownership validation", "Insurance review", "Registration approval", "Number plate issue"],
    interoperabilityRequirements: ["Transport Department", "Insurance checks", "Registration records"],
    onlineAvailability: true,
    category: "Transport",
  },
  {
    id: "licence-verification",
    name: "Licence Verification",
    department: "Transport",
    description: "Verify licence ownership, history and compliance status with the connected transport network.",
    processingTime: "4-7 working days",
    estimatedProcessingTime: "4-7 working days",
    fee: "₹0",
    requiredDocuments: ["Driving licence", "Identity proof", "Address proof"],
    requiredData: ["Licence number", "Issue history", "Vehicle class"],
    workflow: ["Record lookup", "Transport validation", "Background check", "Verification result"],
    interoperabilityRequirements: ["Transport database", "RTO records", "Identity registry"],
    onlineAvailability: true,
    category: "Transport",
  },
  {
    id: "pension",
    name: "Pension",
    department: "Social Welfare",
    description: "Support for old-age and welfare pension disbursement through secure beneficiary verification.",
    processingTime: "12-18 working days",
    estimatedProcessingTime: "12-18 working days",
    fee: "Free",
    requiredDocuments: ["Age proof", "Bank passbook", "Aadhaar card"],
    requiredData: ["Age", "Citizenship status", "Bank account details"],
    workflow: ["Eligibility review", "Bank validation", "Life certificate check", "Pension approval"],
    interoperabilityRequirements: ["Social Welfare", "Banking", "Aadhaar registry"],
    onlineAvailability: true,
    category: "Social Welfare",
  },
  {
    id: "welfare-scheme",
    name: "Welfare Scheme",
    department: "Social Welfare",
    description: "Apply for public assistance programmes with consent-based cross-department validation.",
    processingTime: "10-14 working days",
    estimatedProcessingTime: "10-14 working days",
    fee: "Free",
    requiredDocuments: ["Identity proof", "Address proof", "Income support documents"],
    requiredData: ["Household details", "Income range", "Support category"],
    workflow: ["Eligibility screening", "Income verification", "Department approval", "Benefit sanction"],
    interoperabilityRequirements: ["Social Welfare", "Revenue", "Banking verification"],
    onlineAvailability: true,
    category: "Social Welfare",
  },
  {
    id: "scholarship-assistance",
    name: "Scholarship Assistance",
    department: "Social Welfare",
    description: "Receive support and guidance for scholarship applications and educational welfare benefits.",
    processingTime: "7-10 working days",
    estimatedProcessingTime: "7-10 working days",
    fee: "Free",
    requiredDocuments: ["Income certificate", "Marksheet", "Student ID"],
    requiredData: ["Course details", "Income band", "Family status"],
    workflow: ["Eligibility screening", "Income and academic check", "Scheme fit", "Outcome communication"],
    interoperabilityRequirements: ["Education records", "Revenue records", "Welfare eligibility"],
    onlineAvailability: true,
    category: "Social Welfare",
  },
  {
    id: "birth-certificate",
    name: "Birth Certificate",
    department: "Municipal",
    description: "Issue a birth record using municipal and hospital verification sources.",
    processingTime: "5-7 working days",
    estimatedProcessingTime: "5-7 working days",
    fee: "₹20",
    requiredDocuments: ["Hospital record", "Parent details", "Address proof"],
    requiredData: ["Birth record", "Parent names", "Municipal registration details"],
    workflow: ["Municipal lookup", "Record check", "Approval", "Certificate issue"],
    interoperabilityRequirements: ["Municipal registry", "Hospital records", "Identity verification"],
    onlineAvailability: true,
    category: "Municipal",
  },
  {
    id: "death-certificate",
    name: "Death Certificate",
    department: "Municipal",
    description: "Record and verify a death certificate using civic and hospital records.",
    processingTime: "5-7 working days",
    estimatedProcessingTime: "5-7 working days",
    fee: "₹20",
    requiredDocuments: ["Death record", "Hospital note", "Family details"],
    requiredData: ["Date of death", "Area of residence", "Family confirmation"],
    workflow: ["Death record validation", "Municipal verification", "Certificate processing", "Issue"],
    interoperabilityRequirements: ["Municipal records", "Hospital data", "Family registry"],
    onlineAvailability: true,
    category: "Municipal",
  },
  {
    id: "property-verification",
    name: "Property Verification",
    department: "Municipal",
    description: "Verify public property, ownership and civic records with connected municipal systems.",
    processingTime: "7-10 working days",
    estimatedProcessingTime: "7-10 working days",
    fee: "₹100",
    requiredDocuments: ["Property document", "ID proof", "Survey details"],
    requiredData: ["Property ID", "Owner details", "Address and boundary details"],
    workflow: ["Property lookup", "Boundary check", "Municipal validation", "Verification report"],
    interoperabilityRequirements: ["Municipal property registry", "Survey systems", "Ownership records"],
    onlineAvailability: true,
    category: "Municipal",
  },
  {
    id: "employment-registration",
    name: "Employment Registration",
    department: "Employment",
    description: "Register for employment assistance and public-sector support programmes with verified records.",
    processingTime: "10-14 working days",
    estimatedProcessingTime: "10-14 working days",
    fee: "Free",
    requiredDocuments: ["ID proof", "Qualification details", "Address proof"],
    requiredData: ["Qualification", "Experience", "Employment category"],
    workflow: ["Identity check", "Qualification review", "Skill match", "Registration approval"],
    interoperabilityRequirements: ["Employment department", "Skill registry", "Education verification"],
    onlineAvailability: true,
    category: "Employment",
  },
  {
    id: "skill-verification",
    name: "Skill Verification",
    department: "Employment",
    description: "Validate skills, training and certification with the employment support ecosystem.",
    processingTime: "6-9 working days",
    estimatedProcessingTime: "6-9 working days",
    fee: "₹0",
    requiredDocuments: ["Training certificate", "Qualification proof", "ID proof"],
    requiredData: ["Training history", "Skill competency", "Certification status"],
    workflow: ["Skill record lookup", "Verification", "Department review", "Certificate issue"],
    interoperabilityRequirements: ["Skill registry", "Training records", "Employment database"],
    onlineAvailability: true,
    category: "Employment",
  },
  {
    id: "employment-certificate",
    name: "Employment Certificate",
    department: "Employment",
    description: "Request employment-related eligibility proof for training, placement and social support access.",
    processingTime: "5-7 working days",
    estimatedProcessingTime: "5-7 working days",
    fee: "₹0",
    requiredDocuments: ["ID proof", "Qualification proof", "Work history"],
    requiredData: ["Employment status", "Qualification details", "Address details"],
    workflow: ["Employment record check", "Department review", "Validation", "Certificate issuance"],
    interoperabilityRequirements: ["Employment records", "Education verification", "Identity system"],
    onlineAvailability: true,
    category: "Employment",
  },
];

export const applicationsMock: ApplicationItem[] = [
  {
    id: "APP-2026-10294",
    service: "Income Certificate",
    department: "Revenue",
    submittedDate: "25 Sep 2026",
    status: "Under Verification",
    progress: 65,
    lastUpdated: "Today",
    applicationId: "APP-2026-10294",
    expectedNextStep: "Revenue officer verification in progress",
    contact: "Revenue Department Helpdesk · 1800-XXXX-001",
    timeline: [
      { label: "Application Submitted", date: "25 Sep, 10:30 AM", completed: true },
      { label: "Identity Verified", date: "25 Sep, 10:32 AM", completed: true },
      { label: "Documents Retrieved", date: "25 Sep, 10:33 AM", completed: true },
      { label: "Revenue Department Verification", date: "25 Sep, 11:10 AM", completed: true },
      { label: "Officer Review", date: "In Progress", completed: false, inProgress: true },
      { label: "Certificate Issued", date: "Pending", completed: false },
    ],
    interdepartmentalEvents: [
      "Social Welfare Department requested Income Certificate",
      "Revenue Department verified the record",
      "GovFlow securely transferred the permitted information",
      "Scholarship eligibility check completed",
    ],
  },
  {
    id: "APP-2026-10452",
    service: "Scholarship",
    department: "Social Welfare",
    submittedDate: "18 Sep 2026",
    status: "Documents Verified",
    progress: 80,
    lastUpdated: "Yesterday",
    applicationId: "APP-2026-10452",
    expectedNextStep: "Final eligibility review by social welfare officer",
    contact: "Social Welfare Support · 1800-XXXX-015",
    timeline: [
      { label: "Application Submitted", date: "18 Sep, 09:10 AM", completed: true },
      { label: "Identity Verified", date: "18 Sep, 09:12 AM", completed: true },
      { label: "Income Record Requested", date: "18 Sep, 09:15 AM", completed: true },
      { label: "Socio-Economic Review", date: "20 Sep, 10:25 AM", completed: true },
      { label: "Eligibility Check", date: "21 Sep, 02:05 PM", completed: false, inProgress: true },
      { label: "Scholarship Disbursal", date: "Pending", completed: false },
    ],
    interdepartmentalEvents: [
      "Education Department shared student verification record",
      "Revenue Department confirmed income eligibility",
      "GovFlow verified consent for data exchange",
      "Scholarship payment desk queued for final sanction",
    ],
  },
  {
    id: "APP-2026-10781",
    service: "Driving Licence",
    department: "Transport",
    submittedDate: "15 Sep 2026",
    status: "Appointment Required",
    progress: 45,
    lastUpdated: "2 days ago",
    applicationId: "APP-2026-10781",
    expectedNextStep: "Schedule driving test appointment",
    contact: "Transport Helpdesk · 1800-XXXX-908",
    timeline: [
      { label: "Application Submitted", date: "15 Sep, 08:40 AM", completed: true },
      { label: "Eligibility Check", date: "15 Sep, 08:45 AM", completed: true },
      { label: "Document Review", date: "16 Sep, 11:12 AM", completed: true },
      { label: "Appointment Scheduling", date: "Pending", completed: false, inProgress: true },
      { label: "Driving Test", date: "Pending", completed: false },
      { label: "Licence Issued", date: "Pending", completed: false },
    ],
    interdepartmentalEvents: [
      "Transport Department requested identity verification",
      "Aadhaar record matched successfully",
      "GovFlow linked residence details for address proof",
      "Driving test slot waiting for citizen confirmation",
    ],
  },
  {
    id: "APP-2026-10982",
    service: "Domicile Certificate",
    department: "Revenue",
    submittedDate: "23 Sep 2026",
    status: "Approved",
    progress: 100,
    lastUpdated: "Today",
    applicationId: "APP-2026-10982",
    expectedNextStep: "Certificate downloaded and ready for use",
    contact: "Revenue Department Support · 1800-XXXX-201",
    timeline: [
      { label: "Application Submitted", date: "23 Sep, 11:00 AM", completed: true },
      { label: "Identity Verified", date: "23 Sep, 11:02 AM", completed: true },
      { label: "Address Records Checked", date: "23 Sep, 11:08 AM", completed: true },
      { label: "Revenue Approval", date: "23 Sep, 04:30 PM", completed: true },
      { label: "Certificate Issued", date: "23 Sep, 04:35 PM", completed: true },
    ],
    interdepartmentalEvents: [
      "Municipal records confirmed residence",
      "Revenue Department approved the certificate",
      "Citizen can reuse the record across departments",
    ],
  },
];

export const verifiedRecords: RecordItem[] = [
  { id: "record-income", name: "Income Certificate", sourceDepartment: "Revenue", sourceSystem: "Mahabhulekh Revenue Gateway", sourceType: "Department", verificationStatus: "Verified", retrievedAt: "25 Sep 2026, 10:05 AM", status: "Verified", lastVerified: "25 September 2026", usedByApplications: ["Scholarship Application"] },
  { id: "record-domicile", name: "Domicile", sourceDepartment: "Revenue", sourceSystem: "Revenue Registration System", sourceType: "System", verificationStatus: "Verified", retrievedAt: "20 Sep 2026, 09:15 AM", status: "Verified", lastVerified: "20 September 2026", usedByApplications: ["Domicile Certificate"] },
  { id: "record-education", name: "Education Record", sourceDepartment: "Education", sourceSystem: "SAMARTH Education Registry", sourceType: "Department", verificationStatus: "Verified", retrievedAt: "18 Sep 2026, 01:42 PM", status: "Verified", lastVerified: "18 September 2026", usedByApplications: ["Scholarship Application"] },
  { id: "record-driving", name: "Driving Licence", sourceDepartment: "Transport", sourceSystem: "Sarathi RTO Services", sourceType: "System", verificationStatus: "Verified", retrievedAt: "17 Sep 2026, 05:32 PM", status: "Verified", lastVerified: "17 September 2026", usedByApplications: ["Driving Licence Renewal"] },
];

export const consentRequests: ConsentRequest[] = [
  { id: "consent-1", department: "Social Welfare", data: "Income Certificate", purpose: "Scholarship eligibility verification", status: "Awaiting Approval", sourceDepartment: "Revenue" },
  { id: "consent-2", department: "Education", data: "Education Record", purpose: "Student verification for aid distribution", status: "Granted", grantedOn: "12 Sep 2026", expires: "Application completion", sourceDepartment: "Education" },
  { id: "consent-3", department: "Transport", data: "Address Record", purpose: "Driving licence verification", status: "Revoked", grantedOn: "08 Sep 2026", expires: "Revoked on 11 Sep 2026", sourceDepartment: "Revenue" },
];

export const notificationsMock: NotificationItem[] = [
  { id: "n-1", title: "Income Certificate", description: "Your application has moved to document verification.", time: "15 minutes ago", type: "Application", read: false, relatedApplication: "APP-2026-10294" },
  { id: "n-2", title: "Scholarship", description: "Social Welfare Department requested access to your income certificate.", time: "1 hour ago", type: "Consent", read: false, relatedApplication: "APP-2026-10452" },
  { id: "n-3", title: "Driving Licence", description: "Your appointment has been scheduled.", time: "Today", type: "Application", read: true, relatedApplication: "APP-2026-10781" },
  { id: "n-4", title: "Profile verified", description: "Your profile has been successfully verified.", time: "2 days ago", type: "System", read: true },
  { id: "n-5", title: "Document shared", description: "Your education record was shared with the Education Department.", time: "3 days ago", type: "Document", read: true },
];

export const documentList: DocumentItem[] = [
  { id: "doc-1", name: "Income Certificate", category: "Income", issuingDepartment: "Revenue", issueDate: "10 Aug 2026", expiryDate: "10 Aug 2029", verificationStatus: "Verified" },
  { id: "doc-2", name: "Aadhaar Card", category: "Identity Documents", issuingDepartment: "UIDAI", issueDate: "12 May 2017", expiryDate: "No expiry", verificationStatus: "Verified" },
  { id: "doc-3", name: "Education Record", category: "Education", issuingDepartment: "Education", issueDate: "05 Jul 2026", expiryDate: "No expiry", verificationStatus: "Verified" },
  { id: "doc-4", name: "Domicile Certificate", category: "Address", issuingDepartment: "Revenue", issueDate: "08 Sep 2025", expiryDate: "No expiry", verificationStatus: "Verified" },
  { id: "doc-5", name: "Driving Licence", category: "Identity Documents", issuingDepartment: "Transport", issueDate: "18 Jan 2024", expiryDate: "18 Jan 2034", verificationStatus: "Verified" },
];

export const grievanceList: GrievanceItem[] = [
  { id: "GRV-2026-00321", category: "Service delay", relatedApplication: "APP-2026-10294", department: "Revenue", description: "I have not received an update on my income certificate verification even after 7 working days.", priority: "Medium", status: "Submitted" },
  { id: "GRV-2026-00298", category: "Document issue", relatedApplication: "APP-2026-10452", department: "Social Welfare", description: "My uploaded marksheet was rejected despite being valid.", priority: "High", status: "Under Review" },
];

export async function getCitizenProfile(): Promise<CitizenProfile | null> {
  try {
    const authUser = await api.getMe();
    if (!authUser || authUser.role !== "citizen") return null;

    return {
      id: String(authUser.id),
      citizenId: `CIT-${String(authUser.id).padStart(6, "0")}`,
      fullName: authUser.full_name,
      email: authUser.email,
      phone: authUser.phone || "",
      address: "",
      preferredLanguage: "English",
      verifiedMobile: Boolean(authUser.phone),
      verifiedEmail: true,
    };
  } catch {
    return null;
  }
}

export function getServices(): Promise<GovernmentService[]> {
  return Promise.resolve(governmentServices);
}

export function getApplications(): Promise<ApplicationItem[]> {
  return Promise.resolve(applicationsMock);
}

export function getApplicationById(applicationId: string): Promise<ApplicationItem | undefined> {
  return Promise.resolve(applicationsMock.find((item) => item.applicationId === applicationId || item.id === applicationId));
}

export function submitApplication(service: GovernmentService): Promise<ApplicationItem> {
  const nextId = `APP-2026-${Math.floor(10980 + Math.random() * 50)}`;
  const app: ApplicationItem = {
    id: nextId,
    service: service.name,
    department: service.department,
    submittedDate: "25 September 2026",
    status: "Submitted",
    progress: 12,
    lastUpdated: "Just now",
    applicationId: nextId,
    expectedNextStep: "Department review has started",
    contact: `${service.department} Helpdesk · 1800-XXXX-0${Math.floor(Math.random() * 9)}`,
    timeline: [
      { label: "Application Submitted", date: "25 Sep, 10:30 AM", completed: true },
      { label: "Identity Verified", date: "Pending", completed: false },
      { label: "Department Review", date: "Pending", completed: false },
      { label: "Decision", date: "Pending", completed: false },
    ],
    interdepartmentalEvents: [
      `${service.department} intake received`,
      "GovFlow validated your requested records and consent scope",
      "Department verification has started",
    ],
  };
  return Promise.resolve(app);
}

export function getVerifiedRecords(): Promise<RecordItem[]> {
  return Promise.resolve(verifiedRecords);
}

export function getConsentRequests(): Promise<ConsentRequest[]> {
  return Promise.resolve(consentRequests);
}

export function getDocuments(): Promise<DocumentItem[]> {
  return Promise.resolve(documentList);
}

export function getNotifications(): Promise<NotificationItem[]> {
  return Promise.resolve(notificationsMock);
}

export function markNotificationRead(id: string): Promise<boolean> {
  const item = notificationsMock.find((notification) => notification.id === id);
  if (item) item.read = true;
  return Promise.resolve(true);
}

export function approveConsent(id: string): Promise<boolean> {
  const item = consentRequests.find((request) => request.id === id);
  if (item) item.status = "Granted";
  return Promise.resolve(true);
}

export function rejectConsent(id: string): Promise<boolean> {
  const item = consentRequests.find((request) => request.id === id);
  if (item) item.status = "Revoked";
  return Promise.resolve(true);
}

export function revokeConsent(id: string): Promise<boolean> {
  const item = consentRequests.find((request) => request.id === id);
  if (item) item.status = "Revoked";
  return Promise.resolve(true);
}

export function getGrievances(): Promise<GrievanceItem[]> {
  return Promise.resolve(grievanceList);
}

export function createGrievance(grievance: Omit<GrievanceItem, "id">): Promise<GrievanceItem> {
  const record: GrievanceItem = {
    ...grievance,
    id: `GRV-${new Date().getFullYear()}-${String(Math.floor(10000 + Math.random() * 90000)).slice(-5)}`,
  };
  grievanceList.unshift(record);
  return Promise.resolve(record);
}
