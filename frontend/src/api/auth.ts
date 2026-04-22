import { http } from "./http";
import type { User } from "@/types/models";

export async function login(username: string, password: string): Promise<User> {
  const r = await http.post("/api/auth/login", { username, password });
  return r.data.user;
}

export async function logout(): Promise<void> {
  await http.post("/api/auth/logout");
}

export async function me(): Promise<User> {
  const r = await http.get("/api/auth/me");
  return r.data;
}
