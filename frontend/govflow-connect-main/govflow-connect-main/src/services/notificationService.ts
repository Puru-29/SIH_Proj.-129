import { markNotificationRead as markRead, notificationsMock, type NotificationItem } from "./api";

export async function getNotifications(): Promise<NotificationItem[]> {
  return Promise.resolve(notificationsMock);
}

export async function markNotificationRead(id: string): Promise<boolean> {
  return markRead(id);
}
