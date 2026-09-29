export { getCitizenProfile, loginCitizen, registerCitizen, signOutCitizen } from "./authService";

export { getApplications, getApplicationById, submitApplication } from "./applicationService";

export { getVerifiedRecords, getDocuments, viewDocument } from "./documentService";

export { approveConsent, getConsentRequests, rejectConsent, revokeConsent } from "./consentService";
export { getNotifications, markNotificationRead } from "./notificationService";
export { getServices, getServiceById } from "./serviceService";
export { getGrievances, createGrievance } from "./grievanceService";
