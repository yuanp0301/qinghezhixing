import { defineStore } from "pinia";
import { ref } from "vue";
import { me as apiMe } from "@/api/auth";

export interface CurrentUser {
  id: number;
  username: string;
  role: "admin" | "creator" | "viewer";
  status: "active" | "disabled";
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<CurrentUser | null>(null);
  const ready = ref(false);

  async function ensureLoaded() {
    if (ready.value) return;
    try {
      user.value = await apiMe();
    } catch {
      user.value = null;
    } finally {
      ready.value = true;
    }
  }

  function setUser(u: CurrentUser | null) {
    user.value = u;
    ready.value = true;
  }

  function reset() {
    user.value = null;
    ready.value = true;
  }

  return { user, ready, ensureLoaded, setUser, reset };
});
