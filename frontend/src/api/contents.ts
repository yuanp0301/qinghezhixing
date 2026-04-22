import { http } from "./http";
import type {
  ContentDetail,
  ContentSummary,
  Page,
} from "@/types/models";

export interface ListParams {
  q?: string;
  tag?: string;
  order?: "newest" | "oldest";
  page?: number;
  size?: number;
}

export async function listPublic(
  params: ListParams = {},
): Promise<Page<ContentSummary>> {
  const r = await http.get("/api/contents", { params });
  return r.data;
}

export async function listMine(
  params: ListParams = {},
): Promise<Page<ContentSummary>> {
  const r = await http.get("/api/contents/mine", { params });
  return r.data;
}

export async function detail(id: number): Promise<ContentDetail> {
  const r = await http.get(`/api/contents/${id}`);
  return r.data;
}

export async function patchContent(
  id: number,
  payload: { title?: string; description?: string | null; tags?: string[] },
): Promise<ContentDetail> {
  const r = await http.patch(`/api/contents/${id}`, payload);
  return r.data;
}

export async function removeContent(id: number): Promise<void> {
  await http.delete(`/api/contents/${id}`);
}

export async function uploadContent(
  file: File,
  meta: { title: string; description?: string; tags?: string[] },
  onProgress?: (pct: number) => void,
): Promise<ContentDetail> {
  const fd = new FormData();
  fd.append("title", meta.title);
  if (meta.description) fd.append("description", meta.description);
  for (const t of meta.tags ?? []) fd.append("tags", t);
  fd.append("file", file);
  const r = await http.post("/api/contents", fd, {
    onUploadProgress: (e) => {
      if (!onProgress || !e.total) return;
      onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return r.data;
}
