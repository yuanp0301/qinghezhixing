import { http } from "./http";
import type { Tag } from "@/types/models";

export async function listTags(q?: string): Promise<Tag[]> {
  const r = await http.get("/api/tags", { params: { q } });
  return r.data;
}
