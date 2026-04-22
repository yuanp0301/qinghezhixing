import { http } from "./http";
import type { Page, ShareAccessLog, ShareLink } from "@/types/models";

export async function createShare(
  contentId: number,
  payload: { expires_in_seconds: number; allow_download: boolean },
): Promise<ShareLink> {
  const r = await http.post(
    `/api/contents/${contentId}/shares`, payload,
  );
  return r.data;
}

export async function listShares(
  contentId: number,
): Promise<ShareLink[]> {
  const r = await http.get(`/api/contents/${contentId}/shares`);
  return r.data;
}

export async function revokeShare(token: string): Promise<void> {
  await http.delete(`/api/shares/${token}`);
}

export async function listShareLogs(
  token: string,
  page = 1,
  size = 20,
): Promise<Page<ShareAccessLog>> {
  const r = await http.get(`/api/shares/${token}/logs`, {
    params: { page, size },
  });
  return r.data;
}
