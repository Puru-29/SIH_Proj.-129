import { authenticatedApiClient, apiErrorMessage } from "@/lib/http";
import type { GrievanceItem } from "./api";

export async function getGrievances(): Promise<GrievanceItem[]> {
  try {
    const { data } = await authenticatedApiClient.get<GrievanceItem[]>("/grievances");
    return data;
  } catch (error) {
    throw new Error(apiErrorMessage(error));
  }
}

export async function createGrievance(
  grievance: Omit<GrievanceItem, "id" | "status">,
): Promise<GrievanceItem> {
  try {
    const { data } = await authenticatedApiClient.post<GrievanceItem>("/grievances", grievance);
    return data;
  } catch (error) {
    throw new Error(apiErrorMessage(error));
  }
}
