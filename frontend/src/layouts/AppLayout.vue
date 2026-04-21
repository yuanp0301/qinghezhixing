<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { logout as apiLogout } from "@/api/auth";
import BrandLogo from "@/components/BrandLogo.vue";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const menuItems = computed(() => {
  const items: Array<{ key: string; label: string; to: string }> = [
    { key: "contents", label: "公开库", to: "/contents" },
  ];
  if (auth.user && ["creator", "admin"].includes(auth.user.role)) {
    items.push({ key: "mine", label: "我的上传", to: "/contents/mine" });
  }
  if (auth.user?.role === "admin") {
    items.push(
      { key: "admin-contents", label: "全部内容", to: "/admin/contents" },
      { key: "admin-users", label: "用户管理", to: "/admin/users" },
      { key: "admin-tags", label: "标签管理", to: "/admin/tags" },
    );
  }
  return items;
});

const activeKey = computed(() => {
  const p = route.path;
  if (p.startsWith("/contents/mine")) return "mine";
  if (p.startsWith("/admin/contents")) return "admin-contents";
  if (p.startsWith("/admin/users")) return "admin-users";
  if (p.startsWith("/admin/tags")) return "admin-tags";
  return "contents";
});

async function onLogout() {
  await apiLogout();
  auth.reset();
  router.push("/login");
}
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <router-link to="/contents" class="brand-link">
        <BrandLogo />
      </router-link>
      <div class="spacer" />
      <el-dropdown trigger="click">
        <span class="user-chip">
          <span class="avatar">
            {{ auth.user?.username?.[0]?.toUpperCase() }}
          </span>
          <span class="username">{{ auth.user?.username }}</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              {{ auth.user?.role }}
            </el-dropdown-item>
            <el-dropdown-item divided @click="onLogout">
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </header>

    <div class="body">
      <aside class="sidebar">
        <nav>
          <router-link
            v-for="m in menuItems"
            :key="m.key"
            :to="m.to"
            class="nav-item"
            :class="{ active: m.key === activeKey }"
          >
            {{ m.label }}
          </router-link>
        </nav>
      </aside>
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout { min-height: 100vh; display: flex; flex-direction: column; }
.topbar {
  height: var(--layout-header-h);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-divider);
  display: flex; align-items: center;
  padding: 0 var(--space-5);
  gap: var(--space-4);
}
.brand-link { color: inherit; }
.spacer { flex: 1; }
.user-chip {
  display: inline-flex; align-items: center; gap: 8px;
  cursor: pointer; padding: 4px 8px; border-radius: 20px;
}
.user-chip:hover { background: var(--color-bg-soft); }
.avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--color-brand-soft); color: var(--color-brand);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 500;
}
.username { color: var(--color-text-secondary); font-size: 13px; }

.body { flex: 1; display: flex; }
.sidebar {
  width: var(--layout-sidebar-w);
  background: var(--color-bg);
  border-right: 1px solid var(--color-divider);
  padding: var(--space-4) 0;
}
.sidebar nav { display: flex; flex-direction: column; }
.nav-item {
  display: block; padding: 10px var(--space-5);
  color: var(--color-text-secondary);
  border-left: 2px solid transparent;
  transition: var(--motion-fast);
}
.nav-item:hover { background: var(--color-bg-soft); color: var(--color-text); }
.nav-item.active {
  color: var(--color-brand);
  border-left-color: var(--color-brand);
  background: var(--color-brand-soft);
}
.content {
  flex: 1; padding: var(--layout-content-pad);
  background: var(--color-bg-soft);
  overflow-y: auto;
}
</style>
