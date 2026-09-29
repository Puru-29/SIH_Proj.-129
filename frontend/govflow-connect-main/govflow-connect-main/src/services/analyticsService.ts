import { api } from "@/lib/api";

export const analyticsService = {
  getDashboardStatistics: () => api.getStats(),
  getGovernmentDashboard: () => api.getGovernmentDashboard(),
};
