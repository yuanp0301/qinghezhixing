import type { Router, RouteLocationNormalized } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const PUBLIC = new Set(["login"]);

function requiredRole(to: RouteLocationNormalized): "admin" | "creator" | null {
  const m = to.meta as { requiresRole?: "admin" | "creator" };
  return m.requiresRole ?? null;
}

export function installGuards(router: Router) {
  router.beforeEach(async (to) => {
    const auth = useAuthStore();
    await auth.ensureLoaded();

    if (PUBLIC.has(String(to.name))) {
      // already logged in => redirect away from login
      if (auth.user && to.name === "login") {
        const next = (to.query.next as string) || "/contents";
        return next;
      }
      return true;
    }

    if (!auth.user) {
      const next = encodeURIComponent(to.fullPath);
      return `/login?next=${next}`;
    }

    const need = requiredRole(to);
    if (need === "admin" && auth.user.role !== "admin") {
      return "/contents";
    }
    if (need === "creator" && !["creator", "admin"].includes(auth.user.role)) {
      return "/contents";
    }
    return true;
  });
}
