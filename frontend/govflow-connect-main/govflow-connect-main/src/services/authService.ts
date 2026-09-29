import { api } from "@/lib/api";
import type { AuthResponse } from "@/lib/api";
import type { CitizenProfile } from "./api";

export async function authenticate(email: string, password: string): Promise<AuthResponse> {
  return api.login(email, password);
}

function citizenProfile(
  profile: NonNullable<Awaited<ReturnType<typeof api.getMe>>>,
): CitizenProfile {
  return {
    id: String(profile.id),
    citizenId: String(profile.id),
    fullName: profile.full_name,
    email: profile.email,
    phone: profile.phone ?? "",
    ...(profile.aadhaar_last4 !== undefined ? { aadhaarLast4: profile.aadhaar_last4 } : {}),
  };
}

export async function getCitizenProfile(): Promise<CitizenProfile | null> {
  const profile = await api.getMe();
  return profile?.role === "citizen" ? citizenProfile(profile) : null;
}

export async function loginCitizen(email: string, password: string): Promise<CitizenProfile> {
  const result = await api.login(email, password);
  if (result.user.role !== "citizen") {
    await api.logout();
    throw new Error("This account is not a citizen account.");
  }
  return citizenProfile(result.user);
}

export async function registerCitizen(payload: {
  fullName: string;
  email: string;
  phone: string;
  password: string;
}): Promise<CitizenProfile> {
  const result = await api.signup({
    full_name: payload.fullName,
    email: payload.email,
    phone: payload.phone,
    password: payload.password,
  });
  return citizenProfile(result.user);
}

export async function signOutCitizen(): Promise<void> {
  await api.logout();
}
