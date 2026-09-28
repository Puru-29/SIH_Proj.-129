import { createGrievance as create, getGrievances as list, type GrievanceItem } from "./api";

export async function getGrievances(): Promise<GrievanceItem[]> {
  return list();
}

export async function createGrievance(grievance: Omit<GrievanceItem, "id">): Promise<GrievanceItem> {
  return create(grievance);
}
