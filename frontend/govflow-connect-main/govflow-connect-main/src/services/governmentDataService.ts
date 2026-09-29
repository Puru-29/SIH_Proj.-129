import { api } from "@/lib/api";

export const governmentDataService = {
  getTransactions: () => api.getInteroperabilityTransactions(),
  getTransaction: (id: string) => api.getInteroperabilityTransaction(id),
  getExceptions: () => api.getExceptions(),
  retryException: (id: number) => api.retryException(id),
  getMappings: () => api.getDataMappings(),
  getDepartments: () => api.getDepartments(),
};
