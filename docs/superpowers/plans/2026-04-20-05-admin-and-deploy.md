# 青禾知行 v1 — Plan 5：管理后台与部署 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成管理后台前端三页（全部内容 / 用户管理 / 标签管理），并交付生产可用的部署配置（Dockerfile、docker-compose、Nginx、阿里云 ECS/RDS/OSS runbook）。

**Architecture:** 管理后台复用 Plan 4 的 AppLayout 与 Apple-style tokens，三页均为表格 + 抽屉/弹窗。部署侧后端打包为单一镜像，前端静态产物由 Nginx 直出，反代 `/api`、`/view`、`/view-share`、`/s`、`/d`、`/health` 至 FastAPI。生产数据走阿里云 RDS PostgreSQL 与 OSS。

**Tech Stack:** Vue 3 / Element Plus / Pinia（前端）、FastAPI（后端）、Nginx 1.25、Docker / docker-compose v2、阿里云 ECS / RDS for PostgreSQL / OSS。

**前置依赖：** Plan 1（鉴权 + admin user CRUD API）、Plan 2（admin contents + tags API）、Plan 3（分发链接 + 限流）、Plan 4（前端骨架与公共组件）。

---

## File Structure

**新增前端文件：**
- `frontend/src/api/admin.ts` — 管理后台 API 封装（用户、标签、全部内容）
- `frontend/src/views/admin/AdminContentsView.vue`
- `frontend/src/views/admin/AdminUsersView.vue`
- `frontend/src/views/admin/AdminTagsView.vue`
- `frontend/src/components/admin/UserFormDrawer.vue`
- `frontend/src/components/admin/ResetPasswordDialog.vue`
- `frontend/src/components/admin/TagMergeDialog.vue`

**修改：**
- `frontend/src/router/index.ts` — 注册三个 `/admin/*` 路由（meta.requiresRole: ['admin']）
- `frontend/src/layouts/AppLayout.vue` — 左侧菜单展开「管理后台」子项

**新增部署文件（仓库根目录）：**
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `deploy/docker-compose.prod.yml`
- `deploy/nginx/qinghe.conf`
- `deploy/.env.prod.example`
- `deploy/runbook.md` — 阿里云部署 runbook（含 RDS / OSS / RAM / 安全组步骤）

---

## Task 1：admin API 封装

**Files:**
- Create: `frontend/src/api/admin.ts`
- Modify: `frontend/src/types/index.ts`（追加管理后台相关类型）

- [ ] **Step 1: 追加类型定义**

在 `frontend/src/types/index.ts` 末尾追加：

```ts
export interface AdminUser {
  id: number;
  username: string;
  role: 'admin' | 'creator' | 'viewer';
  is_active: boolean;
  remark: string | null;
  created_at: string;
  last_login_at: string | null;
}

export interface AdminUserListResp {
  items: AdminUser[];
  total: number;
}

export interface AdminUserCreatePayload {
  username: string;
  password: string;
  role: AdminUser['role'];
  remark?: string;
}

export interface AdminUserPatchPayload {
  role?: AdminUser['role'];
  is_active?: boolean;
  remark?: string;
}

export interface AdminTag {
  id: number;
  name: string;
  content_count: number;
  created_at: string;
}

export interface AdminTagListResp {
  items: AdminTag[];
  total: number;
}

export interface AdminContentRow {
  id: number;
  title: string;
  uploader: { id: number; username: string };
  size_bytes: number;
  share_active_count: number;
  share_total_count: number;
  is_deleted: boolean;
  created_at: string;
  tags: { id: number; name: string }[];
}

export interface AdminContentListResp {
  items: AdminContentRow[];
  total: number;
}
```

- [ ] **Step 2: 写 admin API 模块**

```ts
// frontend/src/api/admin.ts
import { http } from './http';
import type {
  AdminUser, AdminUserListResp, AdminUserCreatePayload, AdminUserPatchPayload,
  AdminTag, AdminTagListResp,
  AdminContentListResp,
} from '@/types';

export const adminUsersApi = {
  list: (params: { q?: string; role?: string; is_active?: boolean; page?: number; page_size?: number }) =>
    http.get<AdminUserListResp>('/admin/users', { params }),
  create: (payload: AdminUserCreatePayload) =>
    http.post<AdminUser>('/admin/users', payload),
  patch: (id: number, payload: AdminUserPatchPayload) =>
    http.patch<AdminUser>(`/admin/users/${id}`, payload),
  resetPassword: (id: number) =>
    http.post<{ password: string }>(`/admin/users/${id}/reset-password`, {}),
};

export const adminTagsApi = {
  list: (params: { q?: string; page?: number; page_size?: number }) =>
    http.get<AdminTagListResp>('/admin/tags', { params }),
  create: (name: string) => http.post<AdminTag>('/admin/tags', { name }),
  rename: (id: number, name: string) => http.patch<AdminTag>(`/admin/tags/${id}`, { name }),
  remove: (id: number) => http.delete<void>(`/admin/tags/${id}`),
  merge: (sourceId: number, targetId: number) =>
    http.post<{ moved: number }>(`/admin/tags/${sourceId}/merge`, { target_id: targetId }),
};

export const adminContentsApi = {
  list: (params: { q?: string; uploader_id?: number; is_deleted?: boolean; page?: number; page_size?: number }) =>
    http.get<AdminContentListResp>('/admin/contents', { params }),
  softDelete: (id: number) => http.delete<void>(`/admin/contents/${id}`),
  restore: (id: number) => http.post<void>(`/admin/contents/${id}/restore`, {}),
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/admin.ts frontend/src/types/index.ts
git commit -m "feat(frontend): add admin api modules and types"
```

---

## Task 2：路由与菜单接入

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/layouts/AppLayout.vue`

- [ ] **Step 1: 注册三个路由**

在 `router/index.ts` 的 children 数组中追加（与公开库等并列）：

```ts
{
  path: '/admin/contents',
  name: 'AdminContents',
  component: () => import('@/views/admin/AdminContentsView.vue'),
  meta: { requiresAuth: true, requiresRole: ['admin'], title: '全部内容' },
},
{
  path: '/admin/users',
  name: 'AdminUsers',
  component: () => import('@/views/admin/AdminUsersView.vue'),
  meta: { requiresAuth: true, requiresRole: ['admin'], title: '用户管理' },
},
{
  path: '/admin/tags',
  name: 'AdminTags',
  component: () => import('@/views/admin/AdminTagsView.vue'),
  meta: { requiresAuth: true, requiresRole: ['admin'], title: '标签管理' },
},
```

- [ ] **Step 2: AppLayout 菜单展开**

在 `AppLayout.vue` 的菜单数据结构中，根据 `auth.user?.role === 'admin'` 显示子菜单组：

```vue
<el-sub-menu v-if="auth.user?.role === 'admin'" index="admin">
  <template #title>
    <span>管理后台</span>
  </template>
  <el-menu-item index="/admin/contents" @click="go('/admin/contents')">全部内容</el-menu-item>
  <el-menu-item index="/admin/users" @click="go('/admin/users')">用户管理</el-menu-item>
  <el-menu-item index="/admin/tags" @click="go('/admin/tags')">标签管理</el-menu-item>
</el-sub-menu>
```

- [ ] **Step 3: 启动 dev，验证菜单仅在 admin 登录时出现**

```bash
cd frontend && pnpm dev
```

预期：viewer/creator 登录看不到「管理后台」；admin 看到三个子项；非 admin 直接访问 `/admin/users` 触发 router guard 跳回首页 + Toast `无权限`。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/router/index.ts frontend/src/layouts/AppLayout.vue
git commit -m "feat(frontend): wire admin routes and sidebar entries"
```

---

## Task 3：用户管理页 — 列表与筛选

**Files:**
- Create: `frontend/src/views/admin/AdminUsersView.vue`

- [ ] **Step 1: 写列表骨架（搜索 / 筛选 / 表格 / 分页）**

```vue
<!-- frontend/src/views/admin/AdminUsersView.vue -->
<template>
  <div class="page-wrap">
    <PageHeader title="用户管理">
      <template #actions>
        <el-button type="primary" @click="openCreate">新建用户</el-button>
      </template>
    </PageHeader>

    <div class="filter-bar">
      <el-input v-model="q" placeholder="搜索用户名" clearable style="width: 240px" @change="reload" />
      <el-select v-model="role" placeholder="角色" clearable style="width: 140px" @change="reload">
        <el-option label="admin" value="admin" />
        <el-option label="creator" value="creator" />
        <el-option label="viewer" value="viewer" />
      </el-select>
      <el-select v-model="active" placeholder="状态" clearable style="width: 140px" @change="reload">
        <el-option label="启用" :value="true" />
        <el-option label="禁用" :value="false" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="username" label="用户名" min-width="160" />
      <el-table-column prop="role" label="角色" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatAbs(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="最近登录" width="170">
        <template #default="{ row }">{{ row.last_login_at ? formatAbs(row.last_login_at) : '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="primary" @click="openReset(row)">重置密码</el-button>
          <el-button link :type="row.is_active ? 'danger' : 'primary'" @click="toggleActive(row)">
            {{ row.is_active ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pager"
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next, total"
      @current-change="reload"
    />

    <UserFormDrawer v-model:visible="formVisible" :user="editing" @saved="onSaved" />
    <ResetPasswordDialog v-model:visible="resetVisible" :user="resetting" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ElMessageBox } from 'element-plus';
import PageHeader from '@/components/PageHeader.vue';
import UserFormDrawer from '@/components/admin/UserFormDrawer.vue';
import ResetPasswordDialog from '@/components/admin/ResetPasswordDialog.vue';
import { adminUsersApi } from '@/api/admin';
import { toast } from '@/utils/feedback';
import { formatAbs } from '@/utils/time';
import type { AdminUser } from '@/types';

const rows = ref<AdminUser[]>([]);
const total = ref(0);
const loading = ref(false);
const page = ref(1);
const pageSize = 20;
const q = ref('');
const role = ref<string | undefined>();
const active = ref<boolean | undefined>();

const formVisible = ref(false);
const editing = ref<AdminUser | null>(null);
const resetVisible = ref(false);
const resetting = ref<AdminUser | null>(null);

async function reload() {
  loading.value = true;
  try {
    const data = await adminUsersApi.list({
      q: q.value || undefined,
      role: role.value,
      is_active: active.value,
      page: page.value,
      page_size: pageSize,
    });
    rows.value = data.items;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  formVisible.value = true;
}

function openEdit(row: AdminUser) {
  editing.value = row;
  formVisible.value = true;
}

function openReset(row: AdminUser) {
  resetting.value = row;
  resetVisible.value = true;
}

async function toggleActive(row: AdminUser) {
  const next = !row.is_active;
  if (!next) {
    await ElMessageBox.confirm(
      '禁用后该用户无法登录，已有会话将在下次请求时失效。',
      '禁用用户',
      { type: 'warning', confirmButtonText: '确认禁用', cancelButtonText: '取消' },
    );
  }
  await adminUsersApi.patch(row.id, { is_active: next });
  toast.success(next ? '已启用' : '已禁用');
  reload();
}

function onSaved() {
  formVisible.value = false;
  reload();
}

onMounted(reload);
</script>

<style scoped>
.page-wrap { padding: 24px 32px; }
.filter-bar { display: flex; gap: 12px; margin: 16px 0; }
.pager { margin-top: 16px; display: flex; justify-content: center; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/admin/AdminUsersView.vue
git commit -m "feat(frontend): admin users list view"
```

---

## Task 4：新建/编辑用户抽屉

**Files:**
- Create: `frontend/src/components/admin/UserFormDrawer.vue`

- [ ] **Step 1: 写抽屉组件**

```vue
<!-- frontend/src/components/admin/UserFormDrawer.vue -->
<template>
  <el-drawer :model-value="visible" :title="user ? '编辑用户' : '新建用户'" size="440px"
             @update:model-value="emit('update:visible', $event)">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" :disabled="!!user" placeholder="2–32 字，英数下划线" />
      </el-form-item>
      <el-form-item v-if="!user" label="初始密码" prop="password">
        <el-input v-model="form.password" type="password" show-password placeholder="8–64 字，至少含字母与数字" />
      </el-form-item>
      <el-form-item label="角色" prop="role">
        <el-radio-group v-model="form.role">
          <el-radio value="viewer">viewer</el-radio>
          <el-radio value="creator">creator</el-radio>
          <el-radio value="admin">admin</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="备注" prop="remark">
        <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="200" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSubmit">保存</el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';
import { adminUsersApi } from '@/api/admin';
import { toast } from '@/utils/feedback';
import type { AdminUser } from '@/types';

const props = defineProps<{ visible: boolean; user: AdminUser | null }>();
const emit = defineEmits<{ (e: 'update:visible', v: boolean): void; (e: 'saved'): void }>();

const formRef = ref<FormInstance>();
const saving = ref(false);
const form = reactive({
  username: '',
  password: '',
  role: 'viewer' as AdminUser['role'],
  remark: '',
});

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]{2,32}$/, message: '2–32 字，英数下划线', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { pattern: /^(?=.*[A-Za-z])(?=.*\d).{8,64}$/, message: '8–64 字，至少含字母与数字', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色' }],
};

watch(() => props.visible, (v) => {
  if (!v) return;
  if (props.user) {
    form.username = props.user.username;
    form.password = '';
    form.role = props.user.role;
    form.remark = props.user.remark ?? '';
  } else {
    form.username = '';
    form.password = '';
    form.role = 'viewer';
    form.remark = '';
  }
});

async function onSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate();
  saving.value = true;
  try {
    if (props.user) {
      await adminUsersApi.patch(props.user.id, { role: form.role, remark: form.remark });
      toast.success('已保存');
    } else {
      await adminUsersApi.create({
        username: form.username,
        password: form.password,
        role: form.role,
        remark: form.remark || undefined,
      });
      toast.success('用户已创建');
    }
    emit('saved');
  } finally {
    saving.value = false;
  }
}
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/admin/UserFormDrawer.vue
git commit -m "feat(frontend): user form drawer for admin"
```

---

## Task 5：重置密码弹窗

**Files:**
- Create: `frontend/src/components/admin/ResetPasswordDialog.vue`

- [ ] **Step 1: 写弹窗**

```vue
<!-- frontend/src/components/admin/ResetPasswordDialog.vue -->
<template>
  <el-dialog :model-value="visible" title="重置密码" width="440px" :close-on-click-modal="false"
             @update:model-value="emit('update:visible', $event)" @open="onOpen" @close="onClose">
    <div v-if="loading" class="loading">生成中…</div>
    <div v-else-if="password" class="result">
      <p class="hint">已为 <b>{{ user?.username }}</b> 生成新密码：</p>
      <div class="pw-box">
        <code>{{ password }}</code>
        <el-button type="primary" link @click="copy">复制</el-button>
      </div>
      <p class="warn">请线下转交用户，关闭后无法再次查看。</p>
    </div>
    <template #footer>
      <el-button type="primary" @click="emit('update:visible', false)">完成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { adminUsersApi } from '@/api/admin';
import { toast } from '@/utils/feedback';
import type { AdminUser } from '@/types';

const props = defineProps<{ visible: boolean; user: AdminUser | null }>();
const emit = defineEmits<{ (e: 'update:visible', v: boolean): void }>();

const loading = ref(false);
const password = ref<string | null>(null);

async function onOpen() {
  if (!props.user) return;
  loading.value = true;
  password.value = null;
  try {
    const data = await adminUsersApi.resetPassword(props.user.id);
    password.value = data.password;
  } finally {
    loading.value = false;
  }
}

function onClose() {
  password.value = null;
}

async function copy() {
  if (!password.value) return;
  await navigator.clipboard.writeText(password.value);
  toast.success('已复制');
}
</script>

<style scoped>
.loading { text-align: center; padding: 24px; color: var(--color-text-secondary); }
.result .hint { margin: 0 0 12px; }
.pw-box {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; background: var(--color-bg-subtle); border-radius: 8px;
  font-family: ui-monospace, Menlo, monospace; font-size: 16px;
}
.warn { margin-top: 12px; color: var(--color-warning); font-size: 13px; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/admin/ResetPasswordDialog.vue
git commit -m "feat(frontend): reset password dialog"
```

---

## Task 6：标签管理页 + 合并弹窗

**Files:**
- Create: `frontend/src/views/admin/AdminTagsView.vue`
- Create: `frontend/src/components/admin/TagMergeDialog.vue`

- [ ] **Step 1: 写标签页**

```vue
<!-- frontend/src/views/admin/AdminTagsView.vue -->
<template>
  <div class="page-wrap">
    <PageHeader title="标签管理">
      <template #actions>
        <el-button type="primary" @click="onCreate">新建标签</el-button>
      </template>
    </PageHeader>

    <div class="filter-bar">
      <el-input v-model="q" placeholder="搜索标签" clearable style="width: 240px" @change="reload" />
    </div>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column label="标签名" min-width="200">
        <template #default="{ row }">
          <span v-if="editingId !== row.id">{{ row.name }}</span>
          <el-input v-else v-model="editingName" size="small" @keyup.enter="commitRename(row)" />
        </template>
      </el-table-column>
      <el-table-column prop="content_count" label="关联内容数" width="140" />
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatAbs(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <template v-if="editingId === row.id">
            <el-button link type="primary" @click="commitRename(row)">保存</el-button>
            <el-button link @click="editingId = null">取消</el-button>
          </template>
          <template v-else>
            <el-button link type="primary" @click="startRename(row)">重命名</el-button>
            <el-button link type="primary" @click="openMerge(row)">合并到…</el-button>
            <el-button link type="danger" :disabled="row.content_count > 0" @click="onDelete(row)">删除</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination class="pager" v-model:current-page="page" :page-size="pageSize" :total="total"
                   layout="prev, pager, next, total" @current-change="reload" />

    <TagMergeDialog v-model:visible="mergeVisible" :source="mergingSource" :all-tags="allTags" @merged="reload" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ElMessageBox, ElMessageBox as MB } from 'element-plus';
import PageHeader from '@/components/PageHeader.vue';
import TagMergeDialog from '@/components/admin/TagMergeDialog.vue';
import { adminTagsApi } from '@/api/admin';
import { toast } from '@/utils/feedback';
import { formatAbs } from '@/utils/time';
import type { AdminTag } from '@/types';

const rows = ref<AdminTag[]>([]);
const total = ref(0);
const loading = ref(false);
const page = ref(1);
const pageSize = 50;
const q = ref('');

const editingId = ref<number | null>(null);
const editingName = ref('');

const mergeVisible = ref(false);
const mergingSource = ref<AdminTag | null>(null);
const allTags = ref<AdminTag[]>([]);

async function reload() {
  loading.value = true;
  try {
    const data = await adminTagsApi.list({ q: q.value || undefined, page: page.value, page_size: pageSize });
    rows.value = data.items;
    total.value = data.total;
    allTags.value = data.items;
  } finally {
    loading.value = false;
  }
}

async function onCreate() {
  const { value } = await MB.prompt('请输入标签名（1–20 字）', '新建标签', {
    inputPattern: /^.{1,20}$/, inputErrorMessage: '1–20 字',
  });
  await adminTagsApi.create(value);
  toast.success('已创建');
  reload();
}

function startRename(row: AdminTag) {
  editingId.value = row.id;
  editingName.value = row.name;
}

async function commitRename(row: AdminTag) {
  if (!editingName.value || editingName.value === row.name) {
    editingId.value = null;
    return;
  }
  await adminTagsApi.rename(row.id, editingName.value);
  toast.success('已重命名');
  editingId.value = null;
  reload();
}

function openMerge(row: AdminTag) {
  mergingSource.value = row;
  mergeVisible.value = true;
}

async function onDelete(row: AdminTag) {
  await ElMessageBox.confirm(`确认删除标签 "${row.name}"？`, '删除标签', {
    type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消',
  });
  await adminTagsApi.remove(row.id);
  toast.success('已删除');
  reload();
}

onMounted(reload);
</script>

<style scoped>
.page-wrap { padding: 24px 32px; }
.filter-bar { display: flex; gap: 12px; margin: 16px 0; }
.pager { margin-top: 16px; display: flex; justify-content: center; }
</style>
```

- [ ] **Step 2: 写合并弹窗**

```vue
<!-- frontend/src/components/admin/TagMergeDialog.vue -->
<template>
  <el-dialog :model-value="visible" title="合并标签" width="440px"
             @update:model-value="emit('update:visible', $event)">
    <el-form label-width="80px">
      <el-form-item label="源标签">
        <el-tag>{{ source?.name }}</el-tag>
      </el-form-item>
      <el-form-item label="合并到">
        <el-select v-model="targetId" placeholder="选择目标标签" filterable style="width: 100%">
          <el-option v-for="t in candidates" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :disabled="!targetId" :loading="saving" @click="onConfirm">合并</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { ElMessageBox } from 'element-plus';
import { adminTagsApi } from '@/api/admin';
import { toast } from '@/utils/feedback';
import type { AdminTag } from '@/types';

const props = defineProps<{ visible: boolean; source: AdminTag | null; allTags: AdminTag[] }>();
const emit = defineEmits<{ (e: 'update:visible', v: boolean): void; (e: 'merged'): void }>();

const targetId = ref<number | undefined>();
const saving = ref(false);

const candidates = computed(() => props.allTags.filter(t => t.id !== props.source?.id));

async function onConfirm() {
  if (!props.source || !targetId.value) return;
  const target = props.allTags.find(t => t.id === targetId.value)!;
  await ElMessageBox.confirm(
    `将 "${props.source.name}" 合并到 "${target.name}" 后，"${props.source.name}" 会被删除，` +
    `${props.source.content_count} 条内容的标签会被改为 "${target.name}"。`,
    '确认合并',
    { type: 'warning', confirmButtonText: '确认合并', cancelButtonText: '取消' },
  );
  saving.value = true;
  try {
    await adminTagsApi.merge(props.source.id, targetId.value);
    toast.success('已合并');
    emit('merged');
    emit('update:visible', false);
  } finally {
    saving.value = false;
  }
}
</script>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/admin/AdminTagsView.vue frontend/src/components/admin/TagMergeDialog.vue
git commit -m "feat(frontend): admin tags view with merge dialog"
```

---

## Task 7：全部内容页

**Files:**
- Create: `frontend/src/views/admin/AdminContentsView.vue`

- [ ] **Step 1: 写表格 + 软删/恢复操作**

```vue
<!-- frontend/src/views/admin/AdminContentsView.vue -->
<template>
  <div class="page-wrap">
    <PageHeader title="全部内容" />

    <div class="filter-bar">
      <el-input v-model="q" placeholder="搜索标题" clearable style="width: 240px" @change="reload" />
      <el-select v-model="status" placeholder="状态" clearable style="width: 140px" @change="reload">
        <el-option label="正常" :value="false" />
        <el-option label="已删除" :value="true" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column label="标题" min-width="240">
        <template #default="{ row }">
          <router-link :to="`/contents/${row.id}`" class="title-link">{{ row.title }}</router-link>
        </template>
      </el-table-column>
      <el-table-column label="上传者" width="140">
        <template #default="{ row }">{{ row.uploader.username }}</template>
      </el-table-column>
      <el-table-column label="标签" min-width="180">
        <template #default="{ row }">
          <TagChips :tags="row.tags" />
        </template>
      </el-table-column>
      <el-table-column label="文件大小" width="120">
        <template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template>
      </el-table-column>
      <el-table-column label="分发链接" width="120">
        <template #default="{ row }">
          有效 {{ row.share_active_count }} / 总 {{ row.share_total_count }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_deleted ? 'info' : 'success'">
            {{ row.is_deleted ? '已删除' : '正常' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatAbs(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button v-if="!row.is_deleted" link type="danger" @click="onDelete(row)">下架</el-button>
          <el-button v-else link type="primary" @click="onRestore(row)">恢复</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination class="pager" v-model:current-page="page" :page-size="pageSize" :total="total"
                   layout="prev, pager, next, total" @current-change="reload" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ElMessageBox } from 'element-plus';
import PageHeader from '@/components/PageHeader.vue';
import TagChips from '@/components/TagChips.vue';
import { adminContentsApi } from '@/api/admin';
import { toast } from '@/utils/feedback';
import { formatAbs } from '@/utils/time';
import type { AdminContentRow } from '@/types';

const rows = ref<AdminContentRow[]>([]);
const total = ref(0);
const loading = ref(false);
const page = ref(1);
const pageSize = 20;
const q = ref('');
const status = ref<boolean | undefined>();

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

async function reload() {
  loading.value = true;
  try {
    const data = await adminContentsApi.list({
      q: q.value || undefined,
      is_deleted: status.value,
      page: page.value,
      page_size: pageSize,
    });
    rows.value = data.items;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}

async function onDelete(row: AdminContentRow) {
  await ElMessageBox.confirm(
    '删除后内容将不可访问，已生成的分发链接会一并失效。此操作不可撤销。',
    '下架内容',
    { type: 'warning', confirmButtonText: '确认下架', cancelButtonText: '取消' },
  );
  await adminContentsApi.softDelete(row.id);
  toast.success('已下架');
  reload();
}

async function onRestore(row: AdminContentRow) {
  await adminContentsApi.restore(row.id);
  toast.success('已恢复');
  reload();
}

onMounted(reload);
</script>

<style scoped>
.page-wrap { padding: 24px 32px; }
.filter-bar { display: flex; gap: 12px; margin: 16px 0; }
.pager { margin-top: 16px; display: flex; justify-content: center; }
.title-link { color: var(--color-brand); text-decoration: none; }
.title-link:hover { text-decoration: underline; }
</style>
```

- [ ] **Step 2: dev 自测三页**

```bash
cd frontend && pnpm dev
```

预期：admin 登录后三页可访问；用户增/改、密码重置一次性显示并复制；标签重命名/合并/删除生效；全部内容下架后状态变更、可恢复。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/admin/AdminContentsView.vue
git commit -m "feat(frontend): admin all-contents view"
```

---

## Task 8：后端 Dockerfile

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

- [ ] **Step 1: 写 .dockerignore**

```
__pycache__
*.pyc
.venv
.pytest_cache
.mypy_cache
tests/
*.md
.env*
```

- [ ] **Step 2: 写多阶段 Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install --prefix=/install .

FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY . .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://127.0.0.1:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips=*"]
```

- [ ] **Step 3: 本地构建验证**

```bash
docker build -t qinghe-backend:dev backend/
```

预期：构建成功；`docker run --rm -p 8000:8000 --env-file backend/.env qinghe-backend:dev` 可启动并响应 `/health`。

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "build(backend): multi-stage dockerfile"
```

---

## Task 9：前端 Dockerfile（构建产物 + Nginx 直出）

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/.dockerignore`
- Create: `frontend/nginx.conf`

- [ ] **Step 1: .dockerignore**

```
node_modules
dist
.vite
*.log
```

- [ ] **Step 2: nginx 站点配置（容器内）**

```nginx
# frontend/nginx.conf
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  client_max_body_size 12m;

  # SPA fallback
  location / {
    try_files $uri $uri/ /index.html;
  }

  location ~* \.(?:js|css|woff2?|ttf|svg|png|jpg|webp|ico)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
  }
}
```

- [ ] **Step 3: 多阶段 Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM nginx:1.25-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
```

- [ ] **Step 4: 构建验证**

```bash
docker build -t qinghe-frontend:dev frontend/
docker run --rm -p 8080:80 qinghe-frontend:dev
```

预期：浏览器访问 `http://localhost:8080` 可看到登录页（API 调用此时 404 是预期的，因前端仅做静态资源）。

- [ ] **Step 5: Commit**

```bash
git add frontend/Dockerfile frontend/.dockerignore frontend/nginx.conf
git commit -m "build(frontend): dockerfile with nginx static serving"
```

---

## Task 10：生产 docker-compose 与边缘 Nginx

**Files:**
- Create: `deploy/docker-compose.prod.yml`
- Create: `deploy/nginx/qinghe.conf`
- Create: `deploy/.env.prod.example`

说明：生产架构为「边缘 Nginx（宿主机或独立容器）→ 前端容器（静态）+ 后端容器（FastAPI）」。本任务把边缘 Nginx 作为额外容器一并编排，统一暴露 80/443。

- [ ] **Step 1: .env.prod.example**

```bash
# deploy/.env.prod.example
# 复制为 deploy/.env.prod 并填实际值，勿入 git。
APP_ENV=prod
APP_SECRET=请用 `python -c "import secrets;print(secrets.token_urlsafe(48))"` 生成

POSTGRES_DSN=postgresql+asyncpg://qinghe:STRONG_PWD@rds-host.rds.aliyuncs.com:5432/qinghe
REDIS_URL=redis://redis:6379/0

OSS_ENDPOINT=oss-cn-hangzhou-internal.aliyuncs.com
OSS_BUCKET=qinghe-prod
OSS_ACCESS_KEY_ID=
OSS_ACCESS_KEY_SECRET=
OSS_PREFIX=contents/

SHARE_RATE_LIMIT_PER_MIN=30
SHARE_DEFAULT_TTL_SECONDS=86400
SHARE_MIN_TTL_SECONDS=300
SHARE_MAX_TTL_SECONDS=2592000

SESSION_TTL_SECONDS=604800
COOKIE_SECURE=true
COOKIE_DOMAIN=qinghe.example.com
```

- [ ] **Step 2: 边缘 Nginx 配置**

```nginx
# deploy/nginx/qinghe.conf
upstream qinghe_backend { server backend:8000; }
upstream qinghe_frontend { server frontend:80; }

server {
  listen 80;
  server_name qinghe.example.com;
  return 301 https://$host$request_uri;
}

server {
  listen 443 ssl http2;
  server_name qinghe.example.com;

  ssl_certificate     /etc/nginx/certs/fullchain.pem;
  ssl_certificate_key /etc/nginx/certs/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers HIGH:!aNULL:!MD5;

  client_max_body_size 12m;
  proxy_http_version 1.1;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;

  # 后端路由
  location /api/         { proxy_pass http://qinghe_backend; }
  location /view/        { proxy_pass http://qinghe_backend; }
  location /view-share/  { proxy_pass http://qinghe_backend; }
  location /s/           { proxy_pass http://qinghe_backend; }
  location /d/           { proxy_pass http://qinghe_backend; }
  location /health       { proxy_pass http://qinghe_backend; access_log off; }

  # SPA
  location / { proxy_pass http://qinghe_frontend; }
}
```

- [ ] **Step 3: docker-compose.prod.yml**

```yaml
# deploy/docker-compose.prod.yml
version: "3.9"
services:
  redis:
    image: redis:7-alpine
    restart: always
    command: ["redis-server", "--appendonly", "yes"]
    volumes: ["redis-data:/data"]

  backend:
    image: qinghe-backend:latest
    restart: always
    env_file: .env.prod
    depends_on: [redis]
    expose: ["8000"]

  frontend:
    image: qinghe-frontend:latest
    restart: always
    expose: ["80"]

  nginx:
    image: nginx:1.25-alpine
    restart: always
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx/qinghe.conf:/etc/nginx/conf.d/default.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on: [backend, frontend]

volumes:
  redis-data:
```

- [ ] **Step 4: Commit**

```bash
git add deploy/docker-compose.prod.yml deploy/nginx/qinghe.conf deploy/.env.prod.example
git commit -m "deploy: production compose, edge nginx, env template"
```

---

## Task 11：阿里云部署 Runbook

**Files:**
- Create: `deploy/runbook.md`

- [ ] **Step 1: 写 runbook（含 RDS / OSS / RAM / 安全组步骤）**

```markdown
# 青禾知行 v1 — 阿里云部署 Runbook

## 资源清单

| 资源 | 规格建议 | 备注 |
|---|---|---|
| ECS | 2c4g（ecs.t6-c2m2.large 或同档），CentOS / AlmaLinux 8 | 安装 Docker 24+ |
| RDS PostgreSQL | 15.x，1c2g 起步 | 开内网访问 |
| OSS Bucket | 标准存储，私有读写 | 与 ECS 同地域，使用内网 endpoint |
| 域名 + ICP | qinghe.example.com | 备案完成后绑定 ECS 公网 IP |
| SSL 证书 | 阿里云免费证书或 Let's Encrypt | 放置 `deploy/certs/` |

## 一次性配置

### 1. RDS PostgreSQL
1. 控制台创建实例，选「PostgreSQL 15」，专有网络与 ECS 同 VPC。
2. 创建数据库 `qinghe`、账号 `qinghe`（强密码）。
3. 白名单加入 ECS 内网网段。
4. 记录内网连接串：`postgresql+asyncpg://qinghe:PWD@HOST:5432/qinghe`。

### 2. OSS Bucket
1. 创建 Bucket `qinghe-prod`，地域与 ECS 同；读写权限选「私有」。
2. 跨域规则：v1 不需要直传，留空。
3. 服务端加密：开启「OSS 完全托管 (SSE-OSS)」。
4. 生命周期：可选——为 `contents/` 前缀设置 365 天后转低频，降低成本。

### 3. RAM 子账号
1. 创建子账号 `qinghe-app`，仅程序访问。
2. 自定义策略 `qinghe-oss-rw`：

   ```json
   {
     "Version": "1",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["oss:PutObject", "oss:GetObject", "oss:DeleteObject", "oss:HeadObject"],
         "Resource": ["acs:oss:*:*:qinghe-prod/contents/*"]
       },
       {
         "Effect": "Allow",
         "Action": ["oss:ListObjects"],
         "Resource": ["acs:oss:*:*:qinghe-prod"],
         "Condition": { "StringLike": { "oss:Prefix": ["contents/*"] } }
       }
     ]
   }
   ```

3. 附加策略后生成 AK/SK，写入 `.env.prod`。

### 4. 安全组
- 入方向：80/443 对 0.0.0.0/0；22 仅运维 IP。
- 出方向：默认放行（需访问 RDS 内网与 OSS 内网 endpoint）。

## 部署步骤

```bash
# 0. ECS 安装 Docker
curl -fsSL https://get.docker.com | bash
systemctl enable --now docker

# 1. 拉取/上传镜像（CI 推到 ACR；或本地构建后 docker save / load）
# 推荐 ACR：在本地构建后 push 到 cr.cn-hangzhou.aliyuncs.com/qinghe/{backend,frontend}:vX.Y.Z
docker pull cr.cn-hangzhou.aliyuncs.com/qinghe/backend:v1.0.0
docker pull cr.cn-hangzhou.aliyuncs.com/qinghe/frontend:v1.0.0
docker tag cr.cn-hangzhou.aliyuncs.com/qinghe/backend:v1.0.0 qinghe-backend:latest
docker tag cr.cn-hangzhou.aliyuncs.com/qinghe/frontend:v1.0.0 qinghe-frontend:latest

# 2. 准备配置
cd /opt/qinghe
git clone <repo> .
cp deploy/.env.prod.example deploy/.env.prod
vim deploy/.env.prod   # 填实际值
mkdir -p deploy/certs && cp /path/to/{fullchain,privkey}.pem deploy/certs/

# 3. 数据库初始化
docker run --rm --env-file deploy/.env.prod qinghe-backend:latest \
  alembic upgrade head

# 4. 创建初始 admin
docker run --rm -it --env-file deploy/.env.prod qinghe-backend:latest \
  python -m app.cli.seed_admin --username admin --password 'INIT_PWD'

# 5. 启动
cd deploy && docker compose -f docker-compose.prod.yml up -d
docker compose ps
curl -fsS https://qinghe.example.com/health
```

## 升级流程

```bash
# 1. 更新镜像 tag
sed -i 's|qinghe-backend:latest|qinghe-backend:v1.x.y|' deploy/docker-compose.prod.yml
sed -i 's|qinghe-frontend:latest|qinghe-frontend:v1.x.y|' deploy/docker-compose.prod.yml

# 2. 拉取并重启
docker compose -f deploy/docker-compose.prod.yml pull
docker run --rm --env-file deploy/.env.prod qinghe-backend:v1.x.y alembic upgrade head
docker compose -f deploy/docker-compose.prod.yml up -d
```

## 备份

- **RDS**：开启自动备份，保留 7 天；每月手动快照一次留存 3 个月。
- **OSS**：开启版本控制 + 跨地域复制（可选）。
- **应用配置**：`deploy/.env.prod` 与证书加密备份至 OSS 私有 Bucket（独立的运维 Bucket）。

## 监控与日志

- 容器日志：`docker compose logs -f backend`；建议接入阿里云 SLS。
- 应用 `/health` 由 SLB 或云监控探活。
- Redis：可选接入云数据库 Redis 替代自建容器。

## 故障排查

| 现象 | 排查 |
|---|---|
| 502 | `docker compose logs nginx backend`，看 upstream 是否健康 |
| OSS 上传 403 | RAM 策略权限、AK/SK、bucket region 是否一致 |
| 分发链接 429 | Redis 限流计数；调整 `SHARE_RATE_LIMIT_PER_MIN` |
| 会话失效频繁 | 检查 Redis 持久化与 `SESSION_TTL_SECONDS` |
| HTML 加载白屏 | 浏览器 DevTools → Console，看 CSP/sandbox 报错 |
```

- [ ] **Step 2: Commit**

```bash
git add deploy/runbook.md
git commit -m "docs(deploy): aliyun ecs/rds/oss runbook"
```

---

## Task 12：CI 草案与端到端冒烟（可选但推荐）

**Files:**
- Create: `.github/workflows/build.yml`
- Create: `deploy/smoke.sh`

- [ ] **Step 1: GitHub Actions 构建（如使用 GH；自建 CI 类似）**

```yaml
# .github/workflows/build.yml
name: build
on:
  push: { branches: [main] }
  pull_request: {}

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: install
        run: |
          cd backend && pip install -e .[dev]
      - name: pytest
        run: cd backend && pytest -q

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "pnpm", cache-dependency-path: frontend/pnpm-lock.yaml }
      - run: cd frontend && pnpm install --frozen-lockfile
      - run: cd frontend && pnpm lint && pnpm build

  images:
    needs: [backend, frontend]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - run: docker build -t qinghe-backend:ci backend/
      - run: docker build -t qinghe-frontend:ci frontend/
```

- [ ] **Step 2: 端到端冒烟脚本**

```bash
# deploy/smoke.sh
#!/usr/bin/env bash
set -euo pipefail
HOST="${1:?usage: smoke.sh https://qinghe.example.com}"

echo "[1/4] /health"
curl -fsS "$HOST/health" | grep -q '"status":"ok"'

echo "[2/4] login admin"
COOKIE=$(mktemp)
curl -fsS -c "$COOKIE" -H 'content-type: application/json' \
  -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PWD\"}" \
  "$HOST/api/auth/login" >/dev/null
curl -fsS -b "$COOKIE" "$HOST/api/auth/me" | grep -q '"role":"admin"'

echo "[3/4] list contents"
curl -fsS -b "$COOKIE" "$HOST/api/contents?page=1&page_size=1" >/dev/null

echo "[4/4] invalid share token returns generic page"
curl -fsS "$HOST/s/zzzzzzzzzzzz" | grep -q '链接已失效'

echo "smoke OK"
```

- [ ] **Step 3: 远程跑一次冒烟**

```bash
chmod +x deploy/smoke.sh
ADMIN_PWD='INIT_PWD' deploy/smoke.sh https://qinghe.example.com
```

预期：四步全部 OK；失败定位至对应组件。

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build.yml deploy/smoke.sh
git commit -m "ci: build workflow and smoke script"
```

---

## 完成校验清单

- [ ] 三个管理后台页面（用户 / 标签 / 全部内容）均可在 admin 账号下完整使用，非 admin 不可访问。
- [ ] `docker build` 两个镜像均通过；`docker compose -f deploy/docker-compose.prod.yml up -d` 在演练环境可启动。
- [ ] `alembic upgrade head` 与 `seed_admin` 在容器内可执行。
- [ ] HTTPS 入口 `/health` 200；登录后能正常上传（≤10MB）、生成分发链接、外部 `/s/{token}` 路径有效与失效页符合预期。
- [ ] runbook 包含 RDS / OSS / RAM / 安全组的完整步骤；新人按 runbook 可在 1 小时内完成首次部署。

---

## 自检（plan 作者已完成）

- 覆盖 PRD §8（管理后台三页）与设计文档「部署拓扑」「OSS 鉴权」段落。
- 路由 `meta.requiresRole` 与 Plan 4 的 router guard 字段一致；admin API 名称（`adminUsersApi.resetPassword` 等）在本 plan 内自洽。
- Dockerfile / compose / nginx 三者端口与 upstream 名一致（`backend:8000`、`frontend:80`）。
- 部署步骤区分「一次性配置」与「升级流程」，并列出回滚思路（修改 tag 后 `compose up -d`，迁移幂等）。
