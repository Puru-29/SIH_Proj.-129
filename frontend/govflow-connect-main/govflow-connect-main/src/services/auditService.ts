import { api, type AuditLogFilters, type MeshAuditLog } from "@/lib/api";
import type { AuditEvent } from "./api";

export async function getAuditEvents(filters: AuditLogFilters = {}): Promise<AuditEvent[]> {
  const events: MeshAuditLog[] = await api.getAuditLogs(filters);
  return events.map((event) => ({
    id: event.id,
    timestamp: event.timestamp,
    actor_id: event.actor_id,
    actor_name: event.actor_name,
    actor_role: event.actor_role,
    department_id: event.department_id,
    action: event.action,
    resource_type: event.resource_type,
    resource_id: event.resource_id,
    transaction_id: event.transaction_id,
    result: event.result,
    metadata: event.metadata,
  }));
}

export const auditService = {
  getLogs: (filters: AuditLogFilters = {}) => api.getAuditLogs(filters),
};
