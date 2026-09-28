import { api } from "@/lib/api";
import type { CitizenProfile } from "./api";

export async function loginCitizen(email: string, password: string): Promise<CitizenProfile> {
  if (!email || !password) {
    throw new Error("Please enter your email and password.");
  }

  const result = await api.login(email, password);
  if (result.user.role !== "citizen") {
    throw new Error("This account is not a citizen account.");
  }

  return {
    id: String(result.user.id),
    citizenId: `CIT-${String(result.user.id).padStart(6, "0")}`,
    fullName: result.user.full_name,
    email: result.user.email,
    phone: result.user.phone || "",
    address: "",
    preferredLanguage: "English",
    verifiedMobile: Boolean(result.user.phone),
    verifiedEmail: true,
  };
}

export async function registerCitizen(payload: Partial<CitizenProfile> & { fullName: string; email: string; phone: string; password: string }): Promise<CitizenProfile> {
  const result = await api.signup({
    full_name: payload.fullName,
    email: payload.email,
    password: payload.password,
    phone: payload.phone,
  });

  return {
    id: String(result.user.id),
    citizenId: `CIT-${String(result.user.id).padStart(6, "0")}`,
    fullName: result.user.full_name,
    email: result.user.email,
    phone: result.user.phone || payload.phone,
    address: "",
    preferredLanguage: "English",
    verifiedMobile: Boolean(result.user.phone),
    verifiedEmail: true,
  };
}

export async function signOutCitizen(): Promise<boolean> {
  await api.logout();
  return true;
}
