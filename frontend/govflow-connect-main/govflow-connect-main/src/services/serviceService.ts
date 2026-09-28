import { governmentServices, type GovernmentService } from "./api";

export async function getServices(): Promise<GovernmentService[]> {
  return Promise.resolve(governmentServices);
}

export async function getServiceById(id: string): Promise<GovernmentService | undefined> {
  return Promise.resolve(governmentServices.find((service) => service.id === id));
}
