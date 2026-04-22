import { http } from "./http";
import type {
  AdminContentQuery,
  AdminUserQuery,
  ContentDetail,
  ContentSummary,
  Page,
  PasswordResetResult,
  TagAdmin,
  UserAdmin,
  UserCreatePayload,
  UserUpdatePayload,
} from "@/types/models";

// ---- Users ----

export async function listUsers(
  params: AdminUserQuery = {},
): Promise<Page<UserAdmin>> {
  const r = await http.get("/api/admin/users", { params });
  return r.data;
}

export async function createUser(
  payload: UserCreatePayload,
): Promise<UserAdmin> {
  const r = await http.post("/api/admin/users", payload);
  return r.data;
}

export async function updateUser(
  id: number,
  payload: UserUpdatePayload,
): Promise<UserAdmin> {
  const r = await http.patch(`/api/admin/users/${id}`, payload);
  return r.data;
}

export async function resetUserPassword(
  id: number,
): Promise<PasswordResetResult> {
  const r = await http.post(`/api/admin/users/${id}/reset-password`);
  return r.data;
}

// ---- Tags ----

export async function listAdminTags(q?: string): Promise<TagAdmin[]> {
  const r = await http.get("/api/admin/tags", { params: { q } });
  return r.data;
}

export async function createAdminTag(name: string): Promise<{ id: number; name: string }> {
  const r = await http.post("/api/admin/tags", { name });
  return r.data;
}

export async function renameAdminTag(
  id: number,
  name: string,
): Promise<{ id: number; name: string }> {
  const r = await http.patch(`/api/admin/tags/${id}`, { name });
  return r.data;
}

export async function mergeAdminTag(
  id: number,
  targetId: number,
): Promise<{ affected: number }> {
  const r = await http.post(`/api/admin/tags/${id}/merge`, {
    target_id: targetId,
  });
  return r.data;
}

export async function deleteAdminTag(id: number): Promise<void> {
  await http.delete(`/api/admin/tags/${id}`);
}

// ---- Contents (admin) ----

export async function listAdminContents(
  params: AdminContentQuery = {},
): Promise<Page<ContentSummary>> {
  const r = await http.get("/api/contents/admin/all", { params });
  return r.data;
}

export async function restoreContent(id: number): Promise<ContentDetail> {
  const r = await http.post(`/api/contents/${id}/restore`);
  return r.data;
}
