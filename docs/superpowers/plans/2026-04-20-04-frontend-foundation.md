# Plan 4 / 5 — Frontend Foundation 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `frontend/` 下建 Vue 3 + Vite + TypeScript + Element Plus 工程，落地苹果式 design tokens（色/字号/圆角/控件高度），实现登录页、三栏布局与左侧菜单、路由守卫、公开库、详情/观看页、我的上传、上传页、分发链接弹窗与列表（含访问记录抽屉）。后台与外部观看页留给 Plan 5。

**Architecture:** Vite 单页应用。Pinia 管全局态（当前用户、token 缓存）。所有 API 走 `axios` + 统一 `withCredentials: true`（共用后端 session cookie）。设计 tokens 写在 `src/styles/tokens.css`，覆盖 Element Plus 的 CSS 变量以贴合苹果式克制风格——不引入第三方主题。组件按"页面/容器/展示组件"三层；页面级路由 lazy-loaded。

**Tech Stack:** Vue 3.4+, Vite 5, TypeScript 5, Vue Router 4, Pinia 2, Element Plus 2.6+, axios 1, dayjs。开发器代理后端到 `localhost:8000`。

**前置:** Plan 1/2/3 后端已能本地起。

**Spec 引用:**
- PRD §0 通用规范、§1 登录、§2 公开库、§3 详情/观看、§4 上传、§5 分发链接、§6 我的上传、§9 错误空态、§10 权限矩阵。
- 设计文档 §6.1 沙箱（前端 iframe sandbox 写法）。

---

## 文件结构

```
frontend/
├── package.json
├── pnpm-lock.yaml            # 由 pnpm 生成；首选 pnpm
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── index.html
├── .env.development
├── .env.production
├── .eslintrc.cjs
├── .prettierrc
├── README.md
└── src/
    ├── main.ts
    ├── App.vue
    ├── router/
    │   ├── index.ts
    │   └── guards.ts
    ├── stores/
    │   └── auth.ts
    ├── api/
    │   ├── http.ts            # axios 实例 + 401 拦截
    │   ├── auth.ts
    │   ├── contents.ts
    │   ├── tags.ts
    │   └── shares.ts
    ├── types/
    │   └── models.ts          # 与后端 schema 对应的 TS 类型
    ├── utils/
    │   ├── time.ts            # 相对时间、倒计时
    │   ├── format.ts
    │   └── feedback.ts        # 统一 toast/确认弹窗
    ├── styles/
    │   ├── tokens.css         # 苹果式 design tokens
    │   ├── element-overrides.css
    │   └── global.css
    ├── layouts/
    │   ├── AppLayout.vue      # 顶部 + 侧栏 + 内容
    │   └── BlankLayout.vue    # 登录、外部页等
    ├── components/
    │   ├── BrandLogo.vue
    │   ├── EmptyState.vue
    │   ├── PageHeader.vue
    │   ├── TagChips.vue
    │   ├── ContentCard.vue
    │   ├── ContentTable.vue
    │   ├── HtmlSandboxFrame.vue
    │   ├── ShareCreateDialog.vue
    │   ├── ShareLinkList.vue
    │   └── ShareAccessDrawer.vue
    └── views/
        ├── LoginView.vue
        ├── ContentsView.vue
        ├── ContentDetailView.vue
        ├── MyContentsView.vue
        └── ContentUploadView.vue
```

设计要点：
- TypeScript + Composition API + `<script setup>`。
- 组件文件 < 200 行原则；页面只编排、复杂度下沉到 `components/`。
- `api/*` 只做请求与类型，返回原始数据；UI 反馈在调用方。

---

### Task 1: 工程脚手架

**Files:** 全新建。

- [ ] **Step 1: 在仓库根新建 `frontend/`**

```bash
mkdir -p frontend
cd frontend
```

- [ ] **Step 2: 用 pnpm 初始化（npm 也可，命令等价替换）**

Run:

```bash
pnpm init
```

- [ ] **Step 3: 写 `package.json`（覆盖默认）**

```json
{
  "name": "qinghe-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview --port 4173",
    "lint": "eslint . --ext .ts,.vue --max-warnings 0",
    "format": "prettier --write \"src/**/*.{ts,vue,css,html}\""
  },
  "dependencies": {
    "axios": "^1.6.8",
    "dayjs": "^1.11.10",
    "element-plus": "^2.7.0",
    "pinia": "^2.1.7",
    "vue": "^3.4.21",
    "vue-router": "^4.3.0"
  },
  "devDependencies": {
    "@types/node": "^20.11.30",
    "@vitejs/plugin-vue": "^5.0.4",
    "@vue/tsconfig": "^0.5.1",
    "eslint": "^8.57.0",
    "eslint-plugin-vue": "^9.23.0",
    "prettier": "^3.2.5",
    "typescript": "^5.4.5",
    "vite": "^5.2.0",
    "vue-tsc": "^2.0.10"
  }
}
```

- [ ] **Step 4: 安装**

Run: `pnpm install`
Expected: 无错误。

- [ ] **Step 5: `tsconfig.json`**

```json
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] },
    "types": ["node"],
    "strict": true
  },
  "include": ["src/**/*", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`tsconfig.node.json`：

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "types": ["node"]
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 6: `vite.config.ts`**

```ts
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      "/api":   "http://localhost:8000",
      "/view":  "http://localhost:8000",
      "/s":     "http://localhost:8000",
      "/d":     "http://localhost:8000",
      "/view-share": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
```

- [ ] **Step 7: `index.html`**

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>青禾知行</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 8: `.env.development` / `.env.production`**

```
VITE_API_BASE=
```

（留空表示同源；生产环境 Nginx 反代后亦同源。）

- [ ] **Step 9: `.gitignore`**

```
node_modules
dist
.DS_Store
.vite
```

- [ ] **Step 10: 提交**

```bash
git add frontend/
git commit -m "chore(frontend): scaffold vue3 + vite + ts project"
```

---

### Task 2: 入口、路由占位、基础样式

**Files:** `src/main.ts`、`src/App.vue`、`src/router/index.ts`、`src/router/guards.ts`、`src/styles/*.css`、`src/stores/auth.ts`

- [ ] **Step 1: `src/styles/tokens.css`（苹果式 tokens）**

```css
:root {
  color-scheme: light;

  /* Base palette */
  --color-bg: #ffffff;
  --color-bg-soft: #f7f8fa;
  --color-divider: #ebedf0;
  --color-text: #1d1d1f;
  --color-text-secondary: #6e6e73;
  --color-text-tertiary: #a1a1a6;

  /* Brand: fresh teal */
  --color-brand: #06b6a4;
  --color-brand-hover: #04a092;
  --color-brand-pressed: #038a7d;
  --color-brand-soft: #e6f8f5;

  /* Status */
  --color-success: #34c759;
  --color-warning: #ff9f0a;
  --color-danger:  #ff3b30;
  --color-info:    #6e6e73;

  /* Typography */
  --font-sans: -apple-system, BlinkMacSystemFont, "PingFang SC",
    "Helvetica Neue", "Segoe UI", "Noto Sans CJK SC", sans-serif;
  --font-size-h1: 28px;
  --font-size-h2: 22px;
  --font-size-h3: 18px;
  --font-size-body: 14px;
  --font-size-secondary: 13px;
  --font-size-caption: 12px;
  --line-height-base: 1.5;

  /* Radii */
  --radius-card: 12px;
  --radius-button: 8px;
  --radius-input: 8px;
  --radius-chip: 6px;

  /* Spacing scale */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;

  /* Layout */
  --layout-header-h: 56px;
  --layout-sidebar-w: 220px;
  --layout-content-pad: 32px;

  /* Controls */
  --control-h: 36px;
  --control-h-primary: 40px;

  /* Shadows: minimal */
  --shadow-card: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-popover: 0 8px 24px rgba(0, 0, 0, 0.08);

  /* Motion */
  --motion-fast: 150ms ease-out;
  --motion-modal: 200ms ease-out;
}
```

- [ ] **Step 2: `src/styles/element-overrides.css`（让 Element Plus 贴近 tokens）**

```css
:root {
  --el-color-primary: var(--color-brand);
  --el-color-primary-light-3: var(--color-brand-hover);
  --el-color-primary-light-5: #4dccc0;
  --el-color-primary-light-7: var(--color-brand-soft);
  --el-color-primary-light-8: #f0fbf9;
  --el-color-primary-light-9: #f7fdfc;
  --el-color-primary-dark-2: var(--color-brand-pressed);

  --el-color-success: var(--color-success);
  --el-color-warning: var(--color-warning);
  --el-color-danger:  var(--color-danger);
  --el-color-info:    var(--color-info);

  --el-text-color-primary: var(--color-text);
  --el-text-color-regular: var(--color-text);
  --el-text-color-secondary: var(--color-text-secondary);
  --el-text-color-placeholder: var(--color-text-tertiary);

  --el-border-color: var(--color-divider);
  --el-border-color-light: var(--color-divider);
  --el-border-color-lighter: var(--color-divider);
  --el-fill-color-light: var(--color-bg-soft);
  --el-fill-color-blank: var(--color-bg);

  --el-border-radius-base: var(--radius-button);
  --el-font-family: var(--font-sans);
  --el-font-size-base: var(--font-size-body);

  --el-component-size: 36px;
  --el-component-size-large: 40px;
  --el-component-size-small: 32px;
}

.el-button {
  font-weight: 500;
  border-radius: var(--radius-button);
}
.el-card,
.el-dialog,
.el-drawer__body,
.el-popover.el-popper {
  border-radius: var(--radius-card);
}
.el-input__wrapper,
.el-textarea__inner,
.el-select__wrapper {
  box-shadow: 0 0 0 1px var(--color-divider) inset !important;
  border-radius: var(--radius-input);
}
.el-table th, .el-table td {
  border-bottom: 1px solid var(--color-divider);
}
```

- [ ] **Step 3: `src/styles/global.css`**

```css
@import "./tokens.css";
@import "./element-overrides.css";
@import "element-plus/dist/index.css";

* { box-sizing: border-box; }
html, body, #app { height: 100%; margin: 0; }
body {
  font-family: var(--font-sans);
  font-size: var(--font-size-body);
  line-height: var(--line-height-base);
  color: var(--color-text);
  background: var(--color-bg-soft);
  -webkit-font-smoothing: antialiased;
}
a { color: var(--color-brand); text-decoration: none; }
a:hover { color: var(--color-brand-hover); }

/* Apple-ish minimal scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,.18);
  border-radius: 8px;
}
```

- [ ] **Step 4: `src/main.ts`**

```ts
import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import App from "./App.vue";
import { router } from "./router";
import "./styles/global.css";

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(ElementPlus);
app.mount("#app");
```

- [ ] **Step 5: `src/App.vue`**

```vue
<script setup lang="ts"></script>
<template>
  <router-view />
</template>
```

- [ ] **Step 6: `src/stores/auth.ts`（占位）**

```ts
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
```

- [ ] **Step 7: `src/router/index.ts`（先空架子）**

```ts
import { createRouter, createWebHistory } from "vue-router";
import { installGuards } from "./guards";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/contents",
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
      meta: { layout: "blank" },
    },
    {
      path: "/contents",
      component: () => import("@/layouts/AppLayout.vue"),
      children: [
        {
          path: "",
          name: "contents",
          component: () => import("@/views/ContentsView.vue"),
        },
      ],
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/contents",
    },
  ],
});

installGuards(router);
```

- [ ] **Step 8: `src/router/guards.ts`（占位，后续 Task 4 完善）**

```ts
import type { Router } from "vue-router";

export function installGuards(_router: Router) {
  // see Task 4
}
```

- [ ] **Step 9: 占位 view**

`src/views/LoginView.vue`:

```vue
<template><div class="p-8">Login (placeholder)</div></template>
```

`src/views/ContentsView.vue`:

```vue
<template><div class="p-8">Contents (placeholder)</div></template>
```

`src/layouts/AppLayout.vue`:

```vue
<template><router-view /></template>
```

- [ ] **Step 10: 启动检查**

Run: `pnpm dev` 然后浏览器访问 `http://localhost:5173/`
Expected: 看到 "Contents (placeholder)"。

- [ ] **Step 11: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): bootstrap router/store/styles with apple-style tokens"
```

---

### Task 3: HTTP 客户端、API 类型、auth 接口

**Files:** `src/api/http.ts`、`src/api/auth.ts`、`src/types/models.ts`、`src/utils/feedback.ts`

- [ ] **Step 1: `src/types/models.ts`**

```ts
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
```

- [ ] **Step 2: `src/utils/feedback.ts`**

```ts
import { ElMessage, ElMessageBox } from "element-plus";

export function toastSuccess(msg: string) {
  ElMessage({ type: "success", message: msg, duration: 3000 });
}
export function toastError(msg: string) {
  ElMessage({ type: "error", message: msg, duration: 5000 });
}
export function toastInfo(msg: string) {
  ElMessage({ type: "info", message: msg });
}
export async function confirm(
  title: string,
  message: string,
  confirmText = "确认",
  type: "warning" | "danger" = "warning",
): Promise<boolean> {
  try {
    await ElMessageBox.confirm(message, title, {
      confirmButtonText: confirmText,
      cancelButtonText: "取消",
      type: type === "danger" ? "warning" : "warning",
      confirmButtonClass:
        type === "danger" ? "el-button--danger" : undefined,
    });
    return true;
  } catch {
    return false;
  }
}
```

- [ ] **Step 3: `src/api/http.ts`**

```ts
import axios, { AxiosError } from "axios";
import { toastError } from "@/utils/feedback";

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "",
  withCredentials: true,
  timeout: 30_000,
});

let isRedirectingToLogin = false;

http.interceptors.response.use(
  (r) => r,
  (err: AxiosError<any>) => {
    const status = err.response?.status;
    if (status === 401 && !isRedirectingToLogin) {
      isRedirectingToLogin = true;
      const next = encodeURIComponent(
        location.pathname + location.search,
      );
      location.assign(`/login?next=${next}`);
      return Promise.reject(err);
    }
    if (status === 403) {
      toastError("无权限");
    } else if (status === 429) {
      toastError("访问过于频繁，请稍后再试");
    } else if (!err.response) {
      toastError("网络异常，请重试");
    }
    return Promise.reject(err);
  },
);
```

- [ ] **Step 4: `src/api/auth.ts`**

```ts
import { http } from "./http";
import type { User } from "@/types/models";

export async function login(
  username: string,
  password: string,
): Promise<User> {
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
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/api frontend/src/types frontend/src/utils
git commit -m "feat(api): http client, auth endpoints, feedback helpers, types"
```

---

### Task 4: 路由守卫与会话恢复

**Files:** `src/router/guards.ts`、`src/stores/auth.ts`（小改）

- [ ] **Step 1: 扩展 `src/stores/auth.ts`**

```ts
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
```

- [ ] **Step 2: `src/router/guards.ts`**

```ts
import type { Router, RouteLocationNormalized } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const PUBLIC = new Set(["login"]);

function requiredRole(
  to: RouteLocationNormalized,
): "admin" | "creator" | null {
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
    if (
      need === "creator" &&
      !["creator", "admin"].includes(auth.user.role)
    ) {
      return "/contents";
    }
    return true;
  });
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/router frontend/src/stores
git commit -m "feat(router): auth-aware guards with role checks"
```

---

### Task 5: 三栏布局 AppLayout

**Files:** `src/layouts/AppLayout.vue`、`src/layouts/BlankLayout.vue`、`src/components/BrandLogo.vue`

- [ ] **Step 1: `src/components/BrandLogo.vue`**

```vue
<script setup lang="ts">
defineProps<{ small?: boolean }>();
</script>
<template>
  <div class="brand" :class="{ small }">
    <span class="dot" />
    <span class="name">青禾知行</span>
  </div>
</template>
<style scoped>
.brand { display: inline-flex; align-items: center; gap: 8px; }
.brand .dot {
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--color-brand);
}
.brand .name { font-weight: 500; }
.brand.small .name { font-size: 13px; }
</style>
```

- [ ] **Step 2: `src/layouts/BlankLayout.vue`**

```vue
<template>
  <div class="blank">
    <router-view />
  </div>
</template>
<style scoped>
.blank { min-height: 100vh; background: var(--color-bg-soft); }
</style>
```

- [ ] **Step 3: `src/layouts/AppLayout.vue`**

```vue
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
```

- [ ] **Step 4: 启动看效果**

Run: `pnpm dev`，浏览 `/contents`（在登录前会被守卫推到 `/login`，先把 LoginView 在下个任务做出来）。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/layouts frontend/src/components/BrandLogo.vue
git commit -m "feat(layout): topbar + sidebar layout with role-aware menu"
```

---

### Task 6: 登录页

**Files:** `src/views/LoginView.vue`

- [ ] **Step 1: 实现**

```vue
<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { login } from "@/api/auth";
import { useAuthStore } from "@/stores/auth";
import { toastError } from "@/utils/feedback";
import BrandLogo from "@/components/BrandLogo.vue";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const username = ref("");
const password = ref("");
const submitting = ref(false);
const errorBanner = ref("");

async function onSubmit() {
  errorBanner.value = "";
  if (!username.value || !password.value) {
    errorBanner.value = "请输入用户名与密码";
    return;
  }
  submitting.value = true;
  try {
    const u = await login(username.value, password.value);
    auth.setUser(u);
    const next = (route.query.next as string) || "/contents";
    router.push(next);
  } catch (e: any) {
    const status = e?.response?.status;
    if (status === 401) errorBanner.value = "用户名或密码错误";
    else if (status === 403) errorBanner.value = "账号已被禁用，请联系管理员";
    else toastError("登录失败，请稍后重试");
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <BrandLogo />
      <h1>欢迎登录</h1>
      <el-alert
        v-if="errorBanner"
        :title="errorBanner"
        type="error"
        :closable="false"
        show-icon
      />
      <el-form @submit.prevent="onSubmit" label-position="top">
        <el-form-item label="用户名">
          <el-input
            v-model="username"
            autocomplete="username"
            placeholder="请输入用户名"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="password"
            type="password"
            show-password
            autocomplete="current-password"
            placeholder="请输入密码"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-button
          type="primary"
          :loading="submitting"
          @click="onSubmit"
          style="width: 100%; height: var(--control-h-primary)"
        >
          登录
        </el-button>
      </el-form>
      <p class="hint">如需账号，请联系管理员。</p>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: var(--color-bg-soft);
}
.card {
  width: 400px; padding: 32px;
  background: var(--color-bg);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  display: flex; flex-direction: column; gap: 16px;
}
h1 {
  font-size: var(--font-size-h2);
  font-weight: 500; margin: 0;
}
.hint {
  color: var(--color-text-secondary);
  font-size: var(--font-size-secondary);
  margin: 0; text-align: center;
}
</style>
```

- [ ] **Step 2: 跑一次**

启动后端 + 前端，先用 Plan 1 的 `seed_admin` 建账号；登录后应跳到 `/contents`。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/LoginView.vue
git commit -m "feat(login): apple-style login page with auth integration"
```

---

### Task 7: API 模块（contents / tags / shares）

**Files:** `src/api/contents.ts`、`src/api/tags.ts`、`src/api/shares.ts`

- [ ] **Step 1: `src/api/contents.ts`**

```ts
import { http } from "./http";
import type {
  ContentDetail,
  ContentSummary,
  Page,
} from "@/types/models";

export interface ListParams {
  q?: string;
  tag?: string;
  order?: "newest" | "oldest";
  page?: number;
  size?: number;
}

export async function listPublic(
  params: ListParams = {},
): Promise<Page<ContentSummary>> {
  const r = await http.get("/api/contents", { params });
  return r.data;
}

export async function listMine(
  params: ListParams = {},
): Promise<Page<ContentSummary>> {
  const r = await http.get("/api/contents/mine", { params });
  return r.data;
}

export async function detail(id: number): Promise<ContentDetail> {
  const r = await http.get(`/api/contents/${id}`);
  return r.data;
}

export async function patchContent(
  id: number,
  payload: { title?: string; description?: string | null; tags?: string[] },
): Promise<ContentDetail> {
  const r = await http.patch(`/api/contents/${id}`, payload);
  return r.data;
}

export async function removeContent(id: number): Promise<void> {
  await http.delete(`/api/contents/${id}`);
}

export async function uploadContent(
  file: File,
  meta: { title: string; description?: string; tags?: string[] },
  onProgress?: (pct: number) => void,
): Promise<ContentDetail> {
  const fd = new FormData();
  fd.append("title", meta.title);
  if (meta.description) fd.append("description", meta.description);
  for (const t of meta.tags ?? []) fd.append("tags", t);
  fd.append("file", file);
  const r = await http.post("/api/contents", fd, {
    onUploadProgress: (e) => {
      if (!onProgress || !e.total) return;
      onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return r.data;
}
```

- [ ] **Step 2: `src/api/tags.ts`**

```ts
import { http } from "./http";
import type { Tag } from "@/types/models";

export async function listTags(q?: string): Promise<Tag[]> {
  const r = await http.get("/api/tags", { params: { q } });
  return r.data;
}
```

- [ ] **Step 3: `src/api/shares.ts`**

```ts
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
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/api
git commit -m "feat(api): contents, tags, shares modules"
```

---

### Task 8: 通用组件（EmptyState / PageHeader / TagChips）

**Files:** `src/components/EmptyState.vue`、`src/components/PageHeader.vue`、`src/components/TagChips.vue`

- [ ] **Step 1: `EmptyState.vue`**

```vue
<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>
<template>
  <div class="empty">
    <svg width="56" height="56" viewBox="0 0 24 24" fill="none"
      stroke="#a1a1a6" stroke-width="1.5" stroke-linecap="round"
      stroke-linejoin="round">
      <path d="M4 7h16M4 12h16M4 17h10"></path>
    </svg>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
    <div class="action"><slot /></div>
  </div>
</template>
<style scoped>
.empty {
  display: flex; flex-direction: column; align-items: center;
  padding: 64px 24px; gap: 12px;
  color: var(--color-text-secondary);
}
.empty h3 {
  margin: 0; color: var(--color-text);
  font-size: var(--font-size-h3); font-weight: 500;
}
.empty p { margin: 0; }
.action { margin-top: 12px; }
</style>
```

- [ ] **Step 2: `PageHeader.vue`**

```vue
<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>();
</script>
<template>
  <div class="page-header">
    <div class="left">
      <h1>{{ title }}</h1>
      <div v-if="subtitle" class="sub">{{ subtitle }}</div>
    </div>
    <div class="right"><slot name="actions" /></div>
  </div>
</template>
<style scoped>
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-5);
}
h1 { font-size: var(--font-size-h2); margin: 0; font-weight: 500; }
.sub {
  color: var(--color-text-secondary);
  font-size: var(--font-size-secondary);
  margin-top: 4px;
}
</style>
```

- [ ] **Step 3: `TagChips.vue`**

```vue
<script setup lang="ts">
import type { Tag } from "@/types/models";

defineProps<{
  tags: Tag[];
  max?: number;
}>();
const emit = defineEmits<{ (e: "click", t: Tag): void }>();
</script>
<template>
  <span class="chips">
    <template v-for="(t, i) in tags" :key="t.id">
      <button
        v-if="max == null || i < max"
        class="chip"
        @click.prevent="emit('click', t)"
      >
        {{ t.name }}
      </button>
    </template>
    <span
      v-if="max != null && tags.length > max"
      class="chip more"
    >+{{ tags.length - max }}</span>
  </span>
</template>
<style scoped>
.chips { display: inline-flex; flex-wrap: wrap; gap: 6px; }
.chip {
  border: 1px solid var(--color-divider);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  padding: 2px 8px; font-size: 12px;
  border-radius: var(--radius-chip); cursor: pointer;
}
.chip:hover { color: var(--color-brand); border-color: var(--color-brand); }
.chip.more { cursor: default; }
</style>
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components
git commit -m "feat(components): EmptyState / PageHeader / TagChips"
```

---

### Task 9: 时间工具与公开库 ContentsView

**Files:** `src/utils/time.ts`、`src/components/ContentCard.vue`、`src/views/ContentsView.vue`、`src/router/index.ts`（追加 mine 路由）

- [ ] **Step 1: `src/utils/time.ts`**

```ts
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import "dayjs/locale/zh-cn";

dayjs.locale("zh-cn");
dayjs.extend(relativeTime);

export function formatAbs(iso: string): string {
  return dayjs(iso).format("YYYY-MM-DD HH:mm");
}
export function formatRel(iso: string): string {
  const d = dayjs(iso);
  if (d.isAfter(dayjs().subtract(1, "day"))) return d.fromNow();
  return d.format("YYYY-MM-DD");
}
export function remainingText(expIso: string): string {
  const exp = dayjs(expIso);
  const now = dayjs();
  if (!exp.isAfter(now)) return "已过期";
  const mins = exp.diff(now, "minute");
  if (mins < 60) return `剩 ${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) {
    const m = mins % 60;
    return `剩 ${hours}h ${m.toString().padStart(2, "0")}m`;
  }
  return `剩 ${Math.floor(hours / 24)} 天`;
}
export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 ** 2).toFixed(1)} MB`;
}
```

- [ ] **Step 2: `ContentCard.vue`**

```vue
<script setup lang="ts">
import type { ContentSummary } from "@/types/models";
import TagChips from "./TagChips.vue";
import { formatRel } from "@/utils/time";

defineProps<{ item: ContentSummary }>();
const emit = defineEmits<{
  (e: "click"): void;
  (e: "tag", name: string): void;
}>();
</script>
<template>
  <article class="card" @click="emit('click')">
    <div class="thumb">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none"
        stroke="#a1a1a6" stroke-width="1.5" stroke-linecap="round"
        stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <path d="M14 2v6h6"/>
      </svg>
    </div>
    <h3 class="title">{{ item.title }}</h3>
    <div class="meta">
      <span>{{ item.uploader_username }}</span>
      <span>·</span>
      <span>{{ formatRel(item.created_at) }}</span>
    </div>
    <TagChips
      :tags="item.tags"
      :max="3"
      @click="(t) => emit('tag', t.name)"
    />
  </article>
</template>
<style scoped>
.card {
  background: var(--color-bg);
  border: 1px solid var(--color-divider);
  border-radius: var(--radius-card);
  padding: 16px;
  display: flex; flex-direction: column; gap: 10px;
  transition: var(--motion-fast);
  cursor: pointer;
}
.card:hover {
  box-shadow: var(--shadow-card);
  transform: translateY(-1px);
}
.thumb {
  height: 96px; border-radius: 8px;
  background: var(--color-bg-soft);
  display: flex; align-items: center; justify-content: center;
}
.title {
  margin: 0; font-size: 15px; font-weight: 500;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.meta {
  display: flex; gap: 6px;
  color: var(--color-text-secondary);
  font-size: 12px;
}
</style>
```

- [ ] **Step 3: `ContentsView.vue`**

```vue
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import * as contentsApi from "@/api/contents";
import { listTags } from "@/api/tags";
import type { ContentSummary, Tag } from "@/types/models";
import PageHeader from "@/components/PageHeader.vue";
import EmptyState from "@/components/EmptyState.vue";
import ContentCard from "@/components/ContentCard.vue";
import { useAuthStore } from "@/stores/auth";
import { toastError } from "@/utils/feedback";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const q = ref((route.query.q as string) || "");
const tag = ref((route.query.tag as string) || "");
const order = ref(((route.query.order as string) || "newest") as
  "newest" | "oldest");
const page = ref(parseInt((route.query.page as string) || "1", 10));
const size = 24;

const items = ref<ContentSummary[]>([]);
const total = ref(0);
const loading = ref(false);
const tags = ref<Tag[]>([]);

const hasFilter = computed(
  () => Boolean(q.value || tag.value || order.value !== "newest"),
);

const canUpload = computed(
  () => !!auth.user && ["creator", "admin"].includes(auth.user.role),
);

async function reload() {
  loading.value = true;
  try {
    const r = await contentsApi.listPublic({
      q: q.value || undefined,
      tag: tag.value || undefined,
      order: order.value,
      page: page.value,
      size,
    });
    items.value = r.items;
    total.value = r.total;
  } catch {
    toastError("加载失败");
  } finally {
    loading.value = false;
  }
}

function syncQuery() {
  router.replace({
    query: {
      q: q.value || undefined,
      tag: tag.value || undefined,
      order: order.value === "newest" ? undefined : order.value,
      page: page.value === 1 ? undefined : String(page.value),
    },
  });
}

watch([q, tag, order], () => { page.value = 1; syncQuery(); reload(); });
watch(page, () => { syncQuery(); reload(); });

function clearAll() {
  q.value = ""; tag.value = ""; order.value = "newest";
  page.value = 1; syncQuery(); reload();
}

onMounted(async () => {
  tags.value = await listTags().catch(() => []);
  await reload();
});

function go(item: ContentSummary) {
  router.push(`/contents/${item.id}`);
}
</script>

<template>
  <PageHeader title="公开库" :subtitle="`共 ${total} 条`">
    <template #actions>
      <el-button v-if="canUpload" type="primary"
        @click="router.push('/contents/new')">上传</el-button>
    </template>
  </PageHeader>

  <div class="toolbar">
    <el-input
      v-model="q" placeholder="搜索标题"
      style="width: 320px"
      :prefix-icon="undefined"
      clearable
    />
    <el-select
      v-model="tag" placeholder="标签筛选"
      clearable filterable style="width: 200px"
    >
      <el-option
        v-for="t in tags" :key="t.id"
        :label="t.name" :value="t.name"
      />
    </el-select>
    <el-select v-model="order" style="width: 140px">
      <el-option label="最新上传" value="newest" />
      <el-option label="最早上传" value="oldest" />
    </el-select>
    <el-button v-if="hasFilter" link @click="clearAll">清空筛选</el-button>
  </div>

  <div v-loading="loading">
    <EmptyState
      v-if="!loading && items.length === 0 && !hasFilter"
      title="这里还没有互动动画"
      description="联系制作者上传第一份内容吧"
    >
      <el-button v-if="canUpload" type="primary"
        @click="router.push('/contents/new')">上传</el-button>
    </EmptyState>

    <EmptyState
      v-else-if="!loading && items.length === 0"
      :title="`没有匹配 “${q}” 的内容`"
    >
      <el-button @click="clearAll">清空筛选</el-button>
    </EmptyState>

    <div v-else class="grid">
      <ContentCard
        v-for="it in items"
        :key="it.id"
        :item="it"
        @click="go(it)"
        @tag="(name) => { tag = name; }"
      />
    </div>
  </div>

  <div class="pager">
    <el-pagination
      background layout="prev, pager, next"
      :total="total" :page-size="size"
      :current-page="page"
      @current-change="(p) => (page = p)"
    />
  </div>
</template>

<style scoped>
.toolbar {
  display: flex; gap: 12px; align-items: center;
  margin-bottom: var(--space-5);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-4);
}
.pager {
  display: flex; justify-content: center; margin-top: var(--space-5);
}
</style>
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/utils/time.ts frontend/src/components/ContentCard.vue \
        frontend/src/views/ContentsView.vue
git commit -m "feat(contents): public library with grid, filters, paging"
```

---

### Task 10: 详情/观看页

**Files:** `src/components/HtmlSandboxFrame.vue`、`src/views/ContentDetailView.vue`、`src/router/index.ts`（加路由）

- [ ] **Step 1: `HtmlSandboxFrame.vue`**

```vue
<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{
  src: string;
}>();
const loaded = ref(false);
const errored = ref(false);

function reload() {
  loaded.value = false;
  errored.value = false;
  const f = document.querySelector(
    "iframe.sandbox-frame",
  ) as HTMLIFrameElement | null;
  if (f) f.src = props.src;
}
</script>

<template>
  <div class="frame-wrap">
    <div v-if="!loaded && !errored" class="overlay">正在加载互动内容…</div>
    <div v-if="errored" class="overlay error">
      <p>内容加载失败</p>
      <el-button size="small" @click="reload">重试</el-button>
    </div>
    <iframe
      class="sandbox-frame"
      :src="src"
      sandbox="allow-scripts"
      @load="loaded = true"
      @error="errored = true"
    />
    <div class="tools">
      <el-button size="small" link @click="
        ($event.currentTarget as HTMLElement)
          .closest('.frame-wrap')!.requestFullscreen()
      ">全屏</el-button>
      <el-button size="small" link @click="window.open(src, '_blank')">
        在新窗口打开
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.frame-wrap {
  position: relative;
  background: #000; border-radius: var(--radius-card);
  overflow: hidden;
  aspect-ratio: 16 / 9;
}
iframe {
  width: 100%; height: 100%; border: 0; display: block;
}
.overlay {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: #fff; background: rgba(0,0,0,.6);
  flex-direction: column; gap: 12px;
}
.tools {
  position: absolute; top: 8px; right: 8px;
  display: flex; gap: 6px;
  background: rgba(0,0,0,.4); padding: 4px 8px; border-radius: 8px;
}
.tools .el-button { color: #fff; }
</style>
```

- [ ] **Step 2: `ContentDetailView.vue`**

```vue
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import * as contentsApi from "@/api/contents";
import type { ContentDetail } from "@/types/models";
import HtmlSandboxFrame from "@/components/HtmlSandboxFrame.vue";
import TagChips from "@/components/TagChips.vue";
import { formatAbs, formatBytes } from "@/utils/time";
import { useAuthStore } from "@/stores/auth";
import { confirm, toastError, toastSuccess } from "@/utils/feedback";
import ShareCreateDialog from "@/components/ShareCreateDialog.vue";
import ShareLinkList from "@/components/ShareLinkList.vue";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const data = ref<ContentDetail | null>(null);
const showEdit = ref(false);
const showShare = ref(false);
const editForm = ref({ title: "", description: "", tags: [] as string[] });

const id = computed(() => Number(route.params.id));
const canManage = computed(
  () =>
    !!data.value &&
    !!auth.user &&
    (auth.user.id === data.value.uploader_id || auth.user.role === "admin"),
);

async function load() {
  try {
    data.value = await contentsApi.detail(id.value);
    editForm.value = {
      title: data.value.title,
      description: data.value.description ?? "",
      tags: data.value.tags.map((t) => t.name),
    };
  } catch (e: any) {
    if (e?.response?.status === 404) data.value = null;
    else toastError("加载失败");
  }
}

async function onSaveEdit() {
  if (!data.value) return;
  try {
    data.value = await contentsApi.patchContent(data.value.id, {
      title: editForm.value.title,
      description: editForm.value.description || null,
      tags: editForm.value.tags,
    });
    toastSuccess("已保存");
    showEdit.value = false;
  } catch {
    toastError("保存失败");
  }
}

async function onDelete() {
  if (!data.value) return;
  const ok = await confirm(
    "删除内容",
    "删除后内容将不可访问，已生成的分发链接会一并失效。此操作不可撤销。",
    "确认删除",
    "danger",
  );
  if (!ok) return;
  await contentsApi.removeContent(data.value.id);
  toastSuccess("已删除");
  router.push("/contents");
}

onMounted(load);
</script>

<template>
  <div v-if="!data" class="empty-wrap">
    <el-empty description="内容不存在或已被删除">
      <el-button @click="router.push('/contents')">返回公开库</el-button>
    </el-empty>
  </div>

  <div v-else>
    <div class="breadcrumb">
      <router-link to="/contents">公开库</router-link>
      <span> / </span>
      <span>{{ data.title }}</span>
    </div>

    <div class="title-row">
      <h1>{{ data.title }}</h1>
      <div v-if="canManage" class="actions">
        <el-button @click="showEdit = true">编辑</el-button>
        <el-button type="primary" @click="showShare = true">
          生成分发链接
        </el-button>
        <el-button type="danger" plain @click="onDelete">删除</el-button>
      </div>
    </div>

    <div class="meta">
      <span>{{ data.uploader_username }}</span>
      <span>·</span><span>{{ formatAbs(data.created_at) }}</span>
      <span>·</span><span>{{ formatBytes(data.size_bytes) }}</span>
      <span>·</span><span>{{ data.original_filename }}</span>
    </div>
    <TagChips :tags="data.tags" @click="(t) => router.push({
      path: '/contents', query: { tag: t.name }
    })" />

    <HtmlSandboxFrame :src="`/view/${data.id}`" />

    <p v-if="data.description" class="desc">{{ data.description }}</p>

    <ShareLinkList
      v-if="canManage"
      :content-id="data.id"
      :refresh-key="showShare ? 0 : 1"
    />

    <el-drawer
      v-model="showEdit" title="编辑内容" size="440"
      :destroy-on-close="true"
    >
      <el-form label-position="top" @submit.prevent="onSaveEdit">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" maxlength="100" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="editForm.tags"
            multiple filterable allow-create default-first-option
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="简介">
          <el-input
            v-model="editForm.description" type="textarea"
            :rows="4" maxlength="500" show-word-limit
          />
        </el-form-item>
        <el-button type="primary" @click="onSaveEdit">保存</el-button>
      </el-form>
    </el-drawer>

    <ShareCreateDialog
      v-model="showShare"
      :content-id="data.id"
      @created="() => { /* 列表自刷新 */ }"
    />
  </div>
</template>

<style scoped>
.empty-wrap { display: flex; justify-content: center; padding: 64px; }
.breadcrumb {
  margin-bottom: 8px; color: var(--color-text-secondary); font-size: 13px;
}
.breadcrumb a { color: var(--color-text-secondary); }
.title-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
h1 { font-size: var(--font-size-h1); margin: 0; font-weight: 500; }
.actions { display: flex; gap: 8px; }
.meta {
  display: flex; gap: 6px; flex-wrap: wrap;
  color: var(--color-text-secondary); font-size: 13px;
  margin-bottom: 8px;
}
.desc {
  margin: 16px 0; white-space: pre-wrap;
  color: var(--color-text);
}
</style>
```

- [ ] **Step 3: 把详情路由挂上**

`src/router/index.ts` 在 `/contents` 子路由内追加：

```ts
{
  path: ":id(\\d+)",
  name: "content-detail",
  component: () => import("@/views/ContentDetailView.vue"),
},
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/HtmlSandboxFrame.vue \
        frontend/src/views/ContentDetailView.vue \
        frontend/src/router/index.ts
git commit -m "feat(content-detail): viewer with iframe sandbox + edit/delete"
```

---

### Task 11: 分发链接弹窗与列表 + 访问记录抽屉

**Files:** `src/components/ShareCreateDialog.vue`、`src/components/ShareLinkList.vue`、`src/components/ShareAccessDrawer.vue`

- [ ] **Step 1: `ShareCreateDialog.vue`**

```vue
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { createShare } from "@/api/shares";
import type { ShareLink } from "@/types/models";
import { toastError, toastSuccess } from "@/utils/feedback";

const props = defineProps<{
  modelValue: boolean;
  contentId: number;
}>();
const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "created", s: ShareLink): void;
}>();

const PRESETS = [
  { label: "1 小时", seconds: 3600 },
  { label: "24 小时", seconds: 86400 },
  { label: "7 天", seconds: 604800 },
  { label: "自定义", seconds: -1 },
];

const choice = ref(86400);
const customN = ref(30);
const customUnit = ref<"minute" | "hour" | "day">("minute");
const allowDownload = ref(false);
const submitting = ref(false);
const result = ref<ShareLink | null>(null);

const expiresInSeconds = computed(() => {
  if (choice.value !== -1) return choice.value;
  const m = { minute: 60, hour: 3600, day: 86400 }[customUnit.value];
  return Math.max(300, Math.min(2592000, customN.value * m));
});

watch(() => props.modelValue, (v) => {
  if (v) {
    result.value = null;
    choice.value = 86400;
    allowDownload.value = false;
  }
});

async function onSubmit() {
  submitting.value = true;
  try {
    const s = await createShare(props.contentId, {
      expires_in_seconds: expiresInSeconds.value,
      allow_download: allowDownload.value,
    });
    result.value = s;
    emit("created", s);
  } catch {
    toastError("生成失败");
  } finally {
    submitting.value = false;
  }
}

async function copy(text: string) {
  await navigator.clipboard.writeText(text);
  toastSuccess("已复制");
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="(v) => emit('update:modelValue', v)"
    :title="result ? '链接已生成' : '生成分发链接'"
    width="520"
  >
    <div v-if="!result">
      <el-form label-position="top">
        <el-form-item label="有效期">
          <el-radio-group v-model="choice">
            <el-radio
              v-for="p in PRESETS" :key="p.label"
              :value="p.seconds"
            >{{ p.label }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="choice === -1" label="自定义时长">
          <el-input-number v-model="customN" :min="1" :max="30" />
          <el-select v-model="customUnit" style="width: 100px; margin-left: 8px">
            <el-option label="分钟" value="minute" />
            <el-option label="小时" value="hour" />
            <el-option label="天" value="day" />
          </el-select>
        </el-form-item>
        <el-form-item label="允许下载原文件">
          <el-switch v-model="allowDownload" />
          <div class="hint">
            开启后，访客除了在线观看还可下载 HTML 源文件
          </div>
        </el-form-item>
      </el-form>
    </div>

    <div v-else class="result">
      <el-input :model-value="result.url" readonly />
      <div class="row">
        <el-button @click="copy(result.url)">复制链接</el-button>
        <el-button @click="copy(`${result.url}\n有效期至 ${result.expires_at}`)">
          复制链接和有效期
        </el-button>
      </div>
      <p class="hint">链接将在 {{ result.expires_at }} 过期</p>
    </div>

    <template #footer>
      <template v-if="!result">
        <el-button @click="emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">
          生成
        </el-button>
      </template>
      <template v-else>
        <el-button type="primary" @click="emit('update:modelValue', false)">
          完成
        </el-button>
      </template>
    </template>
  </el-dialog>
</template>

<style scoped>
.hint {
  color: var(--color-text-secondary); font-size: 12px; margin-top: 4px;
}
.result { display: flex; flex-direction: column; gap: 12px; }
.row { display: flex; gap: 8px; }
</style>
```

- [ ] **Step 2: `ShareAccessDrawer.vue`**

```vue
<script setup lang="ts">
import { ref, watch } from "vue";
import type { ShareAccessLog } from "@/types/models";
import { listShareLogs } from "@/api/shares";
import { formatAbs } from "@/utils/time";

const props = defineProps<{
  modelValue: boolean;
  token: string | null;
}>();
const emit = defineEmits<{ (e: "update:modelValue", v: boolean): void }>();

const items = ref<ShareAccessLog[]>([]);
const total = ref(0);
const page = ref(1);
const size = 20;
const loading = ref(false);

async function reload() {
  if (!props.token) return;
  loading.value = true;
  try {
    const r = await listShareLogs(props.token, page.value, size);
    items.value = r.items;
    total.value = r.total;
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.modelValue, props.token],
  ([open]) => {
    if (open) {
      page.value = 1;
      reload();
    }
  },
);

const RESULT_LABEL: Record<ShareAccessLog["result"], string> = {
  success: "成功",
  expired: "已过期",
  revoked: "已撤销",
  not_found: "不存在",
};
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="(v) => emit('update:modelValue', v)"
    title="分发链接访问记录"
    size="520"
    :destroy-on-close="true"
  >
    <div v-loading="loading">
      <el-table :data="items" v-if="items.length">
        <el-table-column label="访问时间" width="170">
          <template #default="{ row }">
            {{ formatAbs(row.viewed_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="client_ip_masked" label="IP" width="140" />
        <el-table-column label="UA">
          <template #default="{ row }">
            <span class="ua">{{ row.user_agent }}</span>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="90">
          <template #default="{ row }">
            {{ RESULT_LABEL[row.result] }}
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无访问记录" />

      <div class="pager" v-if="total > size">
        <el-pagination
          background layout="prev, pager, next"
          :total="total" :page-size="size"
          :current-page="page"
          @current-change="(p) => { page = p; reload(); }"
        />
      </div>
    </div>
  </el-drawer>
</template>

<style scoped>
.ua {
  font-size: 12px; color: var(--color-text-secondary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  display: inline-block; max-width: 220px;
}
.pager { display: flex; justify-content: center; margin-top: 16px; }
</style>
```

- [ ] **Step 3: `ShareLinkList.vue`**

```vue
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { listShares, revokeShare } from "@/api/shares";
import type { ShareLink } from "@/types/models";
import { confirm, toastError, toastSuccess } from "@/utils/feedback";
import { formatAbs, remainingText } from "@/utils/time";
import ShareAccessDrawer from "./ShareAccessDrawer.vue";

const props = defineProps<{
  contentId: number;
  refreshKey?: number;
}>();

const items = ref<ShareLink[]>([]);
const expanded = ref(false);
const drawerToken = ref<string | null>(null);
const drawerOpen = ref(false);
const loading = ref(false);

const stats = computed(() => {
  const valid = items.value.filter((s) => s.state === "active").length;
  return { valid, total: items.value.length };
});

async function reload() {
  loading.value = true;
  try {
    items.value = await listShares(props.contentId);
  } catch {
    toastError("加载失败");
  } finally {
    loading.value = false;
  }
}

async function copy(url: string) {
  await navigator.clipboard.writeText(url);
  toastSuccess("已复制");
}

async function revoke(s: ShareLink) {
  const ok = await confirm(
    "撤销分发链接",
    "撤销后此链接立即失效，已通过它打开页面的访客刷新后将看到失效提示。确定撤销？",
    "撤销",
    "danger",
  );
  if (!ok) return;
  await revokeShare(s.token);
  toastSuccess("已撤销");
  reload();
}

function openLogs(s: ShareLink) {
  drawerToken.value = s.token;
  drawerOpen.value = true;
}

function shortToken(t: string) {
  if (t.length <= 14) return t;
  return `${t.slice(0, 8)}…${t.slice(-4)}`;
}

const STATE_TYPE: Record<ShareLink["state"], string> = {
  active: "success",
  expired: "info",
  revoked: "danger",
};
const STATE_LABEL: Record<ShareLink["state"], string> = {
  active: "有效", expired: "已过期", revoked: "已撤销",
};

onMounted(reload);
watch(() => props.refreshKey, reload);
</script>

<template>
  <section class="block">
    <header @click="expanded = !expanded">
      <h3>分发链接（{{ stats.total }}）</h3>
      <span class="stat">
        有效 {{ stats.valid }} / 总 {{ stats.total }}
      </span>
      <el-button link @click.stop="expanded = !expanded">
        {{ expanded ? "收起" : "展开" }}
      </el-button>
    </header>

    <div v-if="expanded" v-loading="loading" class="body">
      <el-table :data="items" v-if="items.length">
        <el-table-column label="链接" width="200">
          <template #default="{ row }">
            <el-tooltip :content="row.url">
              <span class="link" @click="copy(row.url)">
                /s/{{ shortToken(row.token) }}
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="STATE_TYPE[row.state] as any" size="small">
              {{ STATE_LABEL[row.state] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="倒计时" width="120">
          <template #default="{ row }">
            <span v-if="row.state === 'active'">
              {{ remainingText(row.expires_at) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="允许下载" width="90">
          <template #default="{ row }">
            {{ row.allow_download ? "是" : "否" }}
          </template>
        </el-table-column>
        <el-table-column label="生成时间" width="170">
          <template #default="{ row }">{{ formatAbs(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button link @click="copy(row.url)">复制</el-button>
            <el-button link @click="openLogs(row)">访问记录</el-button>
            <el-button
              link type="danger"
              :disabled="row.state !== 'active'"
              @click="revoke(row)"
            >撤销</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="还没有生成分发链接" />
    </div>

    <ShareAccessDrawer
      v-model="drawerOpen"
      :token="drawerToken"
    />
  </section>
</template>

<style scoped>
.block {
  margin-top: var(--space-5);
  background: var(--color-bg);
  border: 1px solid var(--color-divider);
  border-radius: var(--radius-card);
  padding: 16px 20px;
}
header {
  display: flex; align-items: center; gap: 12px; cursor: pointer;
}
header h3 {
  margin: 0; font-size: 15px; font-weight: 500;
}
.stat {
  margin-left: auto; color: var(--color-text-secondary); font-size: 12px;
}
.body { margin-top: 12px; }
.link { color: var(--color-brand); cursor: pointer; }
</style>
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/ShareCreateDialog.vue \
        frontend/src/components/ShareAccessDrawer.vue \
        frontend/src/components/ShareLinkList.vue
git commit -m "feat(shares): create dialog, list with revoke, access drawer"
```

---

### Task 12: 我的上传页

**Files:** `src/views/MyContentsView.vue`、`src/router/index.ts`

- [ ] **Step 1: `MyContentsView.vue`**

```vue
<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import * as contentsApi from "@/api/contents";
import { listTags } from "@/api/tags";
import type { ContentSummary, Tag } from "@/types/models";
import PageHeader from "@/components/PageHeader.vue";
import EmptyState from "@/components/EmptyState.vue";
import TagChips from "@/components/TagChips.vue";
import { confirm, toastError, toastSuccess } from "@/utils/feedback";
import { formatAbs, formatBytes } from "@/utils/time";

const router = useRouter();
const items = ref<ContentSummary[]>([]);
const total = ref(0);
const page = ref(1);
const size = 20;
const q = ref("");
const tag = ref("");
const tags = ref<Tag[]>([]);
const loading = ref(false);

async function reload() {
  loading.value = true;
  try {
    const r = await contentsApi.listMine({
      q: q.value || undefined,
      tag: tag.value || undefined,
      page: page.value,
      size,
    });
    items.value = r.items;
    total.value = r.total;
  } catch {
    toastError("加载失败");
  } finally {
    loading.value = false;
  }
}

async function onDelete(it: ContentSummary) {
  const ok = await confirm(
    "删除内容",
    `“${it.title}” 删除后将不可访问，已生成的分发链接会一并失效。`,
    "确认删除",
    "danger",
  );
  if (!ok) return;
  await contentsApi.removeContent(it.id);
  toastSuccess("已删除");
  reload();
}

watch([q, tag], () => { page.value = 1; reload(); });
watch(page, reload);
onMounted(async () => {
  tags.value = await listTags().catch(() => []);
  reload();
});
</script>

<template>
  <PageHeader title="我的上传" :subtitle="`共 ${total} 条`">
    <template #actions>
      <el-button type="primary" @click="router.push('/contents/new')">
        上传
      </el-button>
    </template>
  </PageHeader>

  <div class="toolbar">
    <el-input v-model="q" placeholder="搜索标题" style="width: 320px" clearable />
    <el-select v-model="tag" placeholder="标签筛选" clearable filterable
      style="width: 200px">
      <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.name"/>
    </el-select>
  </div>

  <div v-loading="loading">
    <EmptyState
      v-if="!loading && items.length === 0"
      title="还没有上传过互动动画"
    >
      <el-button type="primary" @click="router.push('/contents/new')">上传</el-button>
    </EmptyState>

    <el-table v-else :data="items" stripe>
      <el-table-column label="标题">
        <template #default="{ row }">
          <a class="link" @click="router.push(`/contents/${row.id}`)">
            {{ row.title }}
          </a>
        </template>
      </el-table-column>
      <el-table-column label="标签">
        <template #default="{ row }">
          <TagChips :tags="row.tags" :max="3" />
        </template>
      </el-table-column>
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatAbs(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button link @click="router.push(`/contents/${row.id}`)">观看</el-button>
          <el-button link @click="router.push(`/contents/${row.id}?edit=1`)">编辑</el-button>
          <el-button link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager" v-if="total > size">
      <el-pagination
        background layout="prev, pager, next"
        :total="total" :page-size="size"
        :current-page="page"
        @current-change="(p) => (page = p)"
      />
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: var(--space-5); }
.link { color: var(--color-brand); cursor: pointer; }
.pager { display: flex; justify-content: center; margin-top: 16px; }
</style>
```

- [ ] **Step 2: 路由追加**

`src/router/index.ts` 在 `/contents` 子路由（在详情之前）：

```ts
{
  path: "mine",
  name: "my-contents",
  component: () => import("@/views/MyContentsView.vue"),
  meta: { requiresRole: "creator" },
},
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/MyContentsView.vue frontend/src/router/index.ts
git commit -m "feat(my-contents): table view with filters and actions"
```

---

### Task 13: 上传页

**Files:** `src/views/ContentUploadView.vue`、`src/router/index.ts`

- [ ] **Step 1: `ContentUploadView.vue`**

```vue
<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { uploadContent } from "@/api/contents";
import { listTags } from "@/api/tags";
import type { Tag } from "@/types/models";
import PageHeader from "@/components/PageHeader.vue";
import { toastError, toastSuccess } from "@/utils/feedback";

const router = useRouter();
const title = ref("");
const description = ref("");
const tags = ref<string[]>([]);
const tagOptions = ref<Tag[]>([]);
const file = ref<File | null>(null);
const errorFile = ref("");
const submitting = ref(false);
const progress = ref(0);

(async () => { tagOptions.value = await listTags().catch(() => []); })();

const MAX = 10 * 1024 * 1024;

function onFileChange(f: File | null) {
  errorFile.value = "";
  if (!f) { file.value = null; return; }
  if (!f.name.toLowerCase().endsWith(".html")) {
    errorFile.value = "仅支持 .html 文件"; return;
  }
  if (f.size > MAX) {
    errorFile.value = `文件大小不能超过 10MB（当前 ${
      (f.size / 1024 / 1024).toFixed(1)
    } MB）`;
    return;
  }
  file.value = f;
}

async function onSubmit() {
  if (!title.value) { toastError("请输入标题"); return; }
  if (!file.value) { toastError("请选择文件"); return; }
  if (tags.value.length > 10) { toastError("最多 10 个标签"); return; }
  submitting.value = true;
  progress.value = 0;
  try {
    const detail = await uploadContent(
      file.value,
      {
        title: title.value,
        description: description.value || undefined,
        tags: tags.value,
      },
      (p) => (progress.value = p),
    );
    toastSuccess("上传成功");
    router.push(`/contents/${detail.id}`);
  } catch (e: any) {
    const msg = e?.response?.data?.detail || "上传失败，请稍后重试";
    toastError(typeof msg === "string" ? msg : JSON.stringify(msg));
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <PageHeader title="上传互动动画" />

  <el-form label-position="top" class="form" @submit.prevent="onSubmit">
    <el-form-item label="标题" required>
      <el-input v-model="title" maxlength="100" show-word-limit />
    </el-form-item>
    <el-form-item label="标签">
      <el-select
        v-model="tags" multiple filterable allow-create
        default-first-option style="width: 100%"
      >
        <el-option v-for="t in tagOptions" :key="t.id"
          :label="t.name" :value="t.name" />
      </el-select>
    </el-form-item>
    <el-form-item label="简介">
      <el-input
        v-model="description" type="textarea" :rows="4"
        maxlength="500" show-word-limit
      />
    </el-form-item>
    <el-form-item label="HTML 文件" required :error="errorFile">
      <el-upload
        drag :auto-upload="false" :show-file-list="false"
        accept=".html"
        @change="(f) => onFileChange(f.raw as File)"
      >
        <div v-if="!file" class="drop">
          <p>将 HTML 文件拖到此处，或点击选择</p>
          <p class="muted">仅支持 .html，≤ 10MB</p>
        </div>
        <div v-else class="picked">
          <div>{{ file.name }} · {{ (file.size / 1024).toFixed(1) }} KB</div>
          <el-button link @click.stop="file = null">移除</el-button>
        </div>
      </el-upload>
    </el-form-item>

    <el-progress
      v-if="submitting"
      :percentage="progress" :stroke-width="6"
    />

    <div class="footer">
      <el-button @click="router.back()">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="onSubmit">
        上传
      </el-button>
    </div>
  </el-form>
</template>

<style scoped>
.form { max-width: 720px; }
.drop {
  text-align: center; padding: 24px;
}
.muted { color: var(--color-text-secondary); font-size: 12px; }
.picked {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
}
.footer {
  display: flex; gap: 12px; justify-content: flex-end; margin-top: 24px;
}
</style>
```

- [ ] **Step 2: 路由追加**

```ts
{
  path: "new",
  name: "content-new",
  component: () => import("@/views/ContentUploadView.vue"),
  meta: { requiresRole: "creator" },
},
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/ContentUploadView.vue frontend/src/router/index.ts
git commit -m "feat(upload): drag-and-drop upload with progress"
```

---

### Task 14: ESLint / Prettier、构建检查

**Files:** `.eslintrc.cjs`、`.prettierrc`

- [ ] **Step 1: `.eslintrc.cjs`**

```cjs
module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  parser: "vue-eslint-parser",
  parserOptions: {
    parser: "@typescript-eslint/parser",
    sourceType: "module",
    ecmaVersion: "latest",
  },
  extends: [
    "eslint:recommended",
    "plugin:vue/vue3-recommended",
  ],
  rules: {
    "vue/multi-word-component-names": "off",
  },
};
```

- [ ] **Step 2: `.prettierrc`**

```json
{
  "semi": true,
  "singleQuote": false,
  "trailingComma": "all",
  "printWidth": 88
}
```

- [ ] **Step 3: 构建验证**

Run: `pnpm build`
Expected: `dist/` 生成，无类型错误。

- [ ] **Step 4: 提交**

```bash
git add frontend/.eslintrc.cjs frontend/.prettierrc
git commit -m "chore(frontend): eslint and prettier config"
```

---

### Task 15: README

**Files:** `frontend/README.md`

- [ ] **Step 1: 写**

```markdown
# 青禾知行 · 前端

Vue 3 + Vite + TS + Element Plus，苹果式简洁风。

## 开发

确保后端已起在 :8000。

```bash
pnpm install
pnpm dev
```

打开 `http://localhost:5173`，登录后可用。

## 构建

```bash
pnpm build
```

产物在 `dist/`，由 Plan 5 中的 Nginx 提供静态服务。

## 已实现页面

- /login
- /contents 公开库
- /contents/mine 我的上传（creator/admin）
- /contents/new 上传（creator/admin）
- /contents/:id 详情/观看 + 分发链接弹窗 / 列表 / 访问记录抽屉

管理后台与外部观看页见 Plan 5（外部观看页由后端直接渲染）。
```

- [ ] **Step 2: 提交**

```bash
git add frontend/README.md
git commit -m "docs(frontend): runbook and route map"
```

---

## Self-Review 结果

- 覆盖范围：PRD §0（视觉/控件/字号/状态/时间格式映射到 tokens 与 utils）；§1 登录；§2 公开库（搜索/标签/排序/分页/空态/无权限）；§3 详情/观看/编辑/删除；§4 上传（拖拽/进度/校验文案）；§5 分发链接全部（弹窗/结果态/列表/状态/倒计时/复制/撤销/访问记录抽屉）；§6 我的上传（表格 + 操作）；§9 错误空态在各页对应；§10 角色矩阵在路由守卫与组件 v-if 双层把守。
- 不含：管理后台 + 外部观看页（Plan 5），但已在 AppLayout 菜单留出条目。
- 命名一致：`ContentSummary`/`ContentDetail`/`ShareLink`/`ShareAccessLog` 在 types、api、组件三处一致；`useAuthStore` 的 `user/ready/setUser/reset/ensureLoaded` 在 guards/login/layout 三处使用一致；`http` 实例只此一份。
- 无占位符；每个步骤都给出完整可粘代码或命令。
- 风险：Element Plus iframe 全屏 API 在 Safari 老版本兼容性需关注；属于 v1 之外的 polish。

---

## 交付清单

- 工程可 `pnpm dev` 起、`pnpm build` 通过、`pnpm lint` 0 警告。
- 登录 → 公开库 → 详情观看 → 上传 → 我的上传 → 生成分发链接 → 复制 → 撤销 → 访问记录，闭环可用。
- 视觉与 PRD §0.1 描述一致：青绿色主色克制、苹果系字体、统一圆角、无渐变与重阴影。
