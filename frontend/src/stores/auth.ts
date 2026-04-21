import { defineStore } from "pinia";
import { ref } from "vue";

export interface CurrentUser {
  id: number;
  username: string;
  role: "admin" | "creator" | "viewer";
  status: "active" | "disabled";
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<CurrentUser | null>(null);
  const ready = ref(false);

  function setUser(u: CurrentUser | null) {
    user.value = u;
    ready.value = true;
  }

  return { user, ready, setUser };
});
