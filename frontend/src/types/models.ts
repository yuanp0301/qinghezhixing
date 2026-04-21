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
