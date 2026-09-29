import { api } from "@/lib/api";
import type { ConsentRequest } from "./api";

function mapConsent(consent: Awaited<ReturnType<typeof api.getConsents>>[number]): ConsentRequest {
  const status =
    consent.status === "granted" || consent.status === "active"
      ? "Granted"
      : consent.status === "denied"
        ? "Denied"
        : consent.status === "revoked"
          ? "Revoked"
          : consent.status === "expired"
            ? "Expired"
            : "Pending";
  return {
    id: String(consent.id),
    backendId: consent.id,
    department: consent.target_platform_name ?? "",
    sourceDepartment: consent.source_platform_name ?? "",
    data: consent.requested_data,
    purpose: consent.purpose,
    status,
    ...(consent.granted_at ? { grantedOn: consent.granted_at } : {}),
    ...(consent.expires_at ? { expires: consent.expires_at } : {}),
    ...(consent.application_id ? { applicationId: String(consent.application_id) } : {}),
  };
}

export async function getConsentRequests(): Promise<ConsentRequest[]> {
  return (await api.getConsents()).map(mapConsent);
}

export async function approveConsent(id: string): Promise<ConsentRequest> {
  return mapConsent(await api.approveConsent(Number(id)));
}

export async function rejectConsent(id: string): Promise<ConsentRequest> {
  return mapConsent(await api.rejectConsent(Number(id)));
}

export async function revokeConsent(id: string): Promise<ConsentRequest> {
  return mapConsent(await api.revokeConsent(Number(id)));
}
