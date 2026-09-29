import { api } from "@/lib/api";

export async function getConnectors() {
  return api.getConnectedSystems();
}

export async function getConnectorHealth(id: number | string) {
  return api.getIntegrationHealth(id);
}

export async function runConnectorHealthChecks() {
  return api.getSystemHealth();
}

export const connectorService = {
  getConnectors,
  getConnectorHealth,
  runConnectorHealthChecks,
};
