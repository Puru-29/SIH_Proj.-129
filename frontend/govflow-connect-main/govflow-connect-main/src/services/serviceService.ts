import { authenticatedApiClient, apiErrorMessage } from "@/lib/http";
import type { MeshDepartment, MeshService, ServiceFormSchema } from "@/lib/api";
import type { GovernmentService } from "./api";

export async function getServices(): Promise<GovernmentService[]> {
  try {
    const [services, departments] = await Promise.all([
      authenticatedApiClient.get<MeshService[]>("/services"),
      authenticatedApiClient.get<MeshDepartment[]>("/departments"),
    ]);
    const departmentById = new Map(
      departments.data.map((department) => [department.id, department.name]),
    );
    return services.data.map((service) => ({
      id: String(service.id),
      backendId: service.id,
      name: service.name,
      code: service.code,
      department: departmentById.get(service.department_id) ?? "",
      departmentId: service.department_id,
      platformId: service.platform_id,
      description: service.description ?? "",
      active: service.is_active,
    }));
  } catch (error) {
    throw new Error(apiErrorMessage(error));
  }
}

export async function getServiceById(id: string): Promise<GovernmentService> {
  try {
    const { data } = await authenticatedApiClient.get<MeshService>(
      `/services/${encodeURIComponent(id)}`,
    );
    const { data: department } = await authenticatedApiClient.get<MeshDepartment>(
      `/departments/${data.department_id}`,
    );
    return {
      id: String(data.id),
      backendId: data.id,
      name: data.name,
      code: data.code,
      department: department.name,
      departmentId: data.department_id,
      platformId: data.platform_id,
      description: data.description ?? "",
      active: data.is_active,
    };
  } catch (error) {
    throw new Error(apiErrorMessage(error));
  }
}

export async function getServiceForm(id: number): Promise<ServiceFormSchema> {
  try {
    const { data } = await authenticatedApiClient.get<ServiceFormSchema>(
      `/services/${id}/form-schema`,
    );
    return data;
  } catch (error) {
    throw new Error(apiErrorMessage(error));
  }
}
