import { documentList, type DocumentItem } from "./api";

export async function getDocuments(): Promise<DocumentItem[]> {
  return Promise.resolve(documentList);
}

export async function viewDocument(documentId: string): Promise<DocumentItem | undefined> {
  return Promise.resolve(documentList.find((document) => document.id === documentId));
}
