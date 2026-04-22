export type Role = "admin" | "creator" | "viewer";

export interface User {
  id: number;
  username: string;
  role: Role;
  status: "active" | "disabled";
}

export interface Tag {
  id: number;
  name: string;
}

export interface ContentSummary {
  id: number;
  title: string;
  uploader_id: number;
  uploader_username: string;
  created_at: string;
  size_bytes: number;
  tags: Tag[];
}

export interface ContentDetail extends ContentSummary {
  description: string | null;
  original_filename: string;
  content_type: string;
  sha256: string;
  visibility: "public_in_site" | "private";
  status: "active" | "deleted";
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface ShareLink {
  token: string;
  url: string;
  content_id: number;
  created_by: number;
  created_at: string;
  expires_at: string;
  revoked_at: string | null;
  allow_download: boolean;
  state: "active" | "expired" | "revoked";
}

export interface ShareAccessLog {
  viewed_at: string;
  client_ip_masked: string | null;
  user_agent: string | null;
  result: "success" | "expired" | "revoked" | "not_found";
}

// ---- Admin back-office types ----

export interface UserAdmin {
  id: number;
  username: string;
  role: Role;
  status: "active" | "disabled";
  note: string | null;
  last_login_at: string | null;
  created_at: string;
}

export interface UserCreatePayload {
  username: string;
  password: string;
  role: Role;
  note?: string | null;
}

export interface UserUpdatePayload {
  role?: Role;
  status?: "active" | "disabled";
  note?: string | null;
}

export interface PasswordResetResult {
  new_password: string;
}

export interface TagAdmin {
  id: number;
  name: string;
  content_count: number;
  created_at: string;
}

export interface AdminUserQuery {
  q?: string;
  role?: Role;
  status?: "active" | "disabled";
  page?: number;
  size?: number;
}

export interface AdminContentQuery {
  q?: string;
  tag?: string;
  status?: "active" | "deleted";
  page?: number;
  size?: number;
}
