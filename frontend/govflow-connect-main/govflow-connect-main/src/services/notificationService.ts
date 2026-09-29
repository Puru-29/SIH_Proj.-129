import { api } from "@/lib/api";
import type { NotificationItem } from "./api";

function mapNotification(
  item: Awaited<ReturnType<typeof api.getNotifications>>[number],
): NotificationItem {
  return {
    id: String(item.id),
    title: item.title,
    description: item.message,
    time: item.created_at,
    type: item.event_type,
    read: item.read,
    ...(item.application_reference ? { relatedApplication: item.application_reference } : {}),
    ...(item.transaction_id ? { relatedTransaction: item.transaction_id } : {}),
  };
}

export async function getNotifications(): Promise<NotificationItem[]> {
  return (await api.getNotifications()).map(mapNotification);
}

export async function markNotificationRead(id: string): Promise<NotificationItem> {
  return mapNotification(await api.markNotificationRead(Number(id)));
}
