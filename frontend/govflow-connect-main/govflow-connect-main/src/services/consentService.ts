import { approveConsent as approve, consentRequests, rejectConsent as reject, revokeConsent as revoke, type ConsentRequest } from "./api";

export async function getConsentRequests(): Promise<ConsentRequest[]> {
  return Promise.resolve(consentRequests);
}

export async function approveConsent(id: string): Promise<boolean> {
  return approve(id);
}

export async function rejectConsent(id: string): Promise<boolean> {
  return reject(id);
}

export async function revokeConsent(id: string): Promise<boolean> {
  return revoke(id);
}
