import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { getAccessToken, setAccessToken } from "@/lib/auth-token";

const configuredApiUrl =
  (typeof window !== "undefined" &&
    (window as Window & { __VITE_API_BASE_URL__?: string }).__VITE_API_BASE_URL__) ||
  import.meta.env["VITE_API_BASE_URL"] ||
  import.meta.env["VITE_API_URL"] ||
  "/api/v1";

export const authenticatedApiClient = axios.create({
  baseURL: configuredApiUrl.replace(/\/$/, ""),
  timeout: 15_000,
  withCredentials: true,
  headers: { Accept: "application/json" },
});

let refreshRequest: Promise<string | null> | null = null;
let sessionExpiryDispatched = false;
let refreshUnavailable = false;

function expireSession() {
  refreshUnavailable = true;
  setAccessToken(null);
  if (sessionExpiryDispatched || typeof window === "undefined") return;
  sessionExpiryDispatched = true;
  window.dispatchEvent(new Event("govflow:session-expired"));
}

export function markSessionActive() {
  sessionExpiryDispatched = false;
  refreshUnavailable = false;
}

export function refreshAccessToken(): Promise<string | null> {
  if (refreshUnavailable) return Promise.resolve(null);
  if (refreshRequest) return refreshRequest;
  refreshRequest = axios
    .post<{ access_token?: string }>(
      `${authenticatedApiClient.defaults.baseURL}/auth/refresh`,
      undefined,
      { withCredentials: true, timeout: 15_000 },
    )
    .then(({ data }) => {
      if (!data.access_token) {
        expireSession();
        return null;
      }
      setAccessToken(data.access_token);
      markSessionActive();
      return data.access_token;
    })
    .catch(() => {
      expireSession();
      return null;
    })
    .finally(() => {
      refreshRequest = null;
    });
  return refreshRequest;
}

authenticatedApiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token) config.headers.set("Authorization", `Bearer ${token}`);
  return config;
});

authenticatedApiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as
      (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    if (error.response?.status !== 401 || !config) {
      return Promise.reject(error);
    }
    const endpoint = config.url ?? "";
    if (/\/auth\/(login|signup|refresh|logout)(?:\?|$)/.test(endpoint)) {
      return Promise.reject(error);
    }
    if (config._retried) {
      expireSession();
      return Promise.reject(error);
    }

    config._retried = true;
    const token = await refreshAccessToken();
    if (!token) {
      return Promise.reject(error);
    }
    config.headers.set("Authorization", `Bearer ${token}`);
    return authenticatedApiClient.request(config);
  },
);

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
      return "The request timed out. Please try again.";
    }
    const responseData: unknown = error.response?.data;
    if (typeof responseData === "object" && responseData !== null && "detail" in responseData) {
      const detail = responseData.detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) {
        const validationMessages = detail.flatMap((issue: unknown) => {
          if (typeof issue !== "object" || issue === null || !("msg" in issue)) return [];
          const message = issue.msg;
          if (typeof message !== "string") return [];
          const location =
            "loc" in issue && Array.isArray(issue.loc)
              ? issue.loc.filter((part) => part !== "body").join(".")
              : "";
          return [location ? `${location}: ${message}` : message];
        });
        if (validationMessages.length) return validationMessages.join(" ");
      }
    }
    switch (error.response?.status) {
      case 401:
        return "Your session has expired. Please sign in again.";
      case 403:
        return "You do not have permission to perform this action.";
      case 404:
        return "The requested information could not be found.";
      case 500:
      case 502:
      case 503:
      case 504:
        return "The service is temporarily unavailable. Please try again later.";
      default:
        if (!error.response)
          return "Unable to reach the service. Check your connection and try again.";
        return "The request could not be completed.";
    }
  }
  return "The request could not be completed.";
}
