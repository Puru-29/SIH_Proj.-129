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
    if (error.response?.status !== 401 || !config || config._retried) {
      return Promise.reject(error);
    }
    const endpoint = config.url ?? "";
    if (/\/auth\/(login|signup|refresh|logout)(?:\?|$)/.test(endpoint)) {
      return Promise.reject(error);
    }

    config._retried = true;
    refreshRequest ??= axios
      .post<{ access_token?: string }>(
        `${authenticatedApiClient.defaults.baseURL}/auth/refresh`,
        undefined,
        { withCredentials: true, timeout: 15_000 },
      )
      .then(({ data }) => data.access_token ?? null)
      .catch(() => null)
      .finally(() => {
        refreshRequest = null;
      });

    const token = await refreshRequest;
    if (!token) {
      setAccessToken(null);
      return Promise.reject(error);
    }
    setAccessToken(token);
    config.headers.set("Authorization", `Bearer ${token}`);
    return authenticatedApiClient.request(config);
  },
);

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
      return "The request timed out. Please try again.";
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
