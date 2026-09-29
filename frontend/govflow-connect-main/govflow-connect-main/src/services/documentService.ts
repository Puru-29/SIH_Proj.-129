import { api, type MeshDocument } from "@/lib/api";
import type { DocumentItem, RecordItem } from "./api";

function mapDocument(document: MeshDocument): DocumentItem {
  return {
    id: String(document.id),
    name: document.title,
    category: document.doc_type,
    uploadedAt: document.created_at,
    verificationStatus: document.is_verified ? "Verified" : "Pending",
  };
}

export async function getDocuments(): Promise<DocumentItem[]> {
  const profile = await api.getMe();
  if (!profile) return [];
  return (await api.getDocuments(profile.id)).map(mapDocument);
}

export async function viewDocument(documentId: string): Promise<DocumentItem | undefined> {
  const document = await api.getDocument(Number(documentId));
  return document ? mapDocument(document) : undefined;
}

export async function getVerifiedRecords(): Promise<RecordItem[]> {
  const applications = await api.getApplications();
  const workspaces = await Promise.all(
    applications.map((application) => api.getApplicationWorkspace(application.id)),
  );
  return workspaces.flatMap((workspace) =>
    workspace.verified_records.map((record) => ({
      id: record.id,
      name: record.record_type,
      sourceDepartment: record.department ?? "",
      verificationStatus: record.status,
      lastVerified: record.verified_at,
      usedByApplications: [workspace.application.reference_id],
    })),
  );
}
